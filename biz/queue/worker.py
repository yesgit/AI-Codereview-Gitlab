import os
import traceback
from datetime import datetime

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.event.event_manager import event_manager
from biz.gitlab.webhook_handler import filter_changes, MergeRequestHandler, PushHandler, _normalize_base_url
from biz.github.webhook_handler import filter_changes as filter_github_changes, PullRequestHandler as GithubPullRequestHandler, PushHandler as GithubPushHandler
from biz.gitea.webhook_handler import filter_changes as filter_gitea_changes, PullRequestHandler as GiteaPullRequestHandler, \
    PushHandler as GiteaPushHandler
from biz.service.review_service import ReviewService
from biz.utils.code_reviewer import CodeReviewer
from biz.utils.im import notifier
from biz.utils.log import logger



def handle_push_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str):
    push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'
    try:
        handler = PushHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info('Push Hook event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        # 按 author 分组 commits
        from collections import defaultdict
        author_commits = defaultdict(list)
        for commit in commits:
            author_name = commit.get('author', 'Unknown')
            author_commits[author_name].append(commit)

        logger.info(f"Total {len(commits)} commits, grouped by {len(author_commits)} authors")

        # 如果没有启用 push review，仍然发送通知但不进行审查
        if not push_review_enabled:
            for author_name, author_commit_list in author_commits.items():
                event_manager['push_reviewed'].send(PushReviewEntity(
                    project_name=webhook_data['project']['name'],
                    author=author_name,
                    branch=webhook_data.get('ref', '').replace('refs/heads/', ''),
                    updated_at=int(datetime.now().timestamp()),
                    commits=author_commit_list,
                    score=0,
                    review_result="Push review 未启用",
                    url_slug=gitlab_url_slug,
                    webhook_data=webhook_data,
                    additions=0,
                    deletions=0,
                ))
            return

        # 为每个 author 获取其所有 commits 的 diff，合并后审查
        for author_name, author_commit_list in author_commits.items():
            try:
                all_changes = []
                additions = 0
                deletions = 0
                commit_messages = []
                failed_commits = []

                # 获取该 author 所有 commits 的 diff
                for commit in author_commit_list:
                    # 需要从原始 webhook_data 中获取 commit ID
                    commit_id = None
                    for original_commit in webhook_data.get('commits', []):
                        if original_commit.get('message') == commit.get('message'):
                            commit_id = original_commit.get('id')
                            break
                    
                    if commit_id:
                        try:
                            # 获取 commit diff，支持重试
                            commit_changes = handler.get_commit_diff(commit_id)
                            logger.debug(f"Author {author_name}, commit {commit_id[:8]}: got {len(commit_changes)} changes")
                            commit_changes = filter_changes(commit_changes)
                            all_changes.extend(commit_changes)
                            commit_messages.append(commit.get('message', '').strip())
                            
                            # 统计
                            for item in commit_changes:
                                additions += item['additions']
                                deletions += item['deletions']
                        except Exception as e:
                            logger.error(f"Failed to get diff for commit {commit_id[:8]} (author: {author_name}): {str(e)}")
                            failed_commits.append(commit_id)
                            continue
                    else:
                        logger.warning(f"Commit ID not found for message: {commit.get('message', '')}")
                        failed_commits.append(commit_id)
                        continue

                # 记录失败的 commits
                if failed_commits:
                    logger.warning(f"Author {author_name}: Failed to process {len(failed_commits)} commits: {[c[:8] if c else 'N/A' for c in failed_commits]}")

                # 如果有有效的 changes，进行审查
                review_result = None
                score = 0
                
                if all_changes:
                    project_name = webhook_data['project']['name']
                    commits_text = ';'.join(commit_messages)
                    code_reviewer = CodeReviewer()
                    review_result = code_reviewer.review_changes_in_batches(all_changes, commits_text, project_name)
                    score = CodeReviewer.parse_review_score(review_text=review_result)
                    
                    # 发送该 author 的审查结果到 GitLab（在最后一次提交上添加评论）
                    if author_commit_list:
                        last_commit_id = None
                        for original_commit in webhook_data.get('commits', [])[::-1]:
                            if original_commit.get('author', {}).get('name') == author_name:
                                last_commit_id = original_commit.get('id')
                                break
                        
                        if last_commit_id:
                            # 直接调用 API 添加评论
                            from urllib.parse import urljoin
                            base = _normalize_base_url(gitlab_url)
                            if base:
                                url = urljoin(base, f"api/v4/projects/{handler.project_id}/repository/commits/{last_commit_id}/comments")
                                headers = {
                                    'Private-Token': gitlab_token,
                                    'Content-Type': 'application/json'
                                }
                                data = {
                                    'note': f'[{author_name}] Auto Review Result: \n{review_result}'
                                }
                                import requests
                                response = requests.post(url, headers=headers, json=data, verify=False)
                                logger.debug(f"Add comment to commit {last_commit_id[:8]}: {response.status_code}")
                else:
                    review_result = "关注的文件没有修改"
                    logger.info(f"Author {author_name}: {review_result}")

                # 发送该 author 的 PushReviewEntity 事件
                event_manager['push_reviewed'].send(PushReviewEntity(
                    project_name=webhook_data['project']['name'],
                    author=author_name,
                    branch=webhook_data.get('ref', '').replace('refs/heads/', ''),
                    updated_at=int(datetime.now().timestamp()),
                    commits=author_commit_list,
                    score=score,
                    review_result=review_result,
                    url_slug=gitlab_url_slug,
                    webhook_data=webhook_data,
                    additions=additions,
                    deletions=deletions,
                ))
            except Exception as e:
                logger.error(f"Error processing author {author_name}: {str(e)}")
                # 继续处理下一个 author，不中断整个流程
                continue

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_merge_request_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str):
    '''
    处理Merge Request Hook事件
    :param webhook_data:
    :param gitlab_token:
    :param gitlab_url:
    :param gitlab_url_slug:
    :return:
    '''
    merge_review_only_protected_branches = os.environ.get('MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED', '0') == '1'
    try:
        # 解析Webhook数据
        handler = MergeRequestHandler(webhook_data, gitlab_token, gitlab_url)
        logger.info('Merge Request Hook event received')

        # 新增：判断是否为draft（草稿）MR
        object_attributes = webhook_data.get('object_attributes', {})
        is_draft = object_attributes.get('draft') or object_attributes.get('work_in_progress')
        if is_draft:
            msg = f"[通知] MR为草稿（draft），未触发AI审查。\n项目: {webhook_data['project']['name']}\n作者: {webhook_data['user']['username']}\n源分支: {object_attributes.get('source_branch')}\n目标分支: {object_attributes.get('target_branch')}\n链接: {object_attributes.get('url')}"
            notifier.send_notification(content=msg)
            logger.info("MR为draft，仅发送通知，不触发AI review。")
            return

        # 如果开启了仅review projected branches的，判断当前目标分支是否为projected branches
        if merge_review_only_protected_branches and not handler.target_branch_protected():
            logger.info("Merge Request target branch not match protected branches, ignored.")
            return

        if handler.action not in ['open', 'update']:
            logger.info(f"Merge Request Hook event, action={handler.action}, ignored.")
            return

        # 检查last_commit_id是否已经存在，如果存在则跳过处理
        last_commit_id = object_attributes.get('last_commit', {}).get('id', '')
        if last_commit_id:
            project_name = webhook_data['project']['name']
            source_branch = object_attributes.get('source_branch', '')
            target_branch = object_attributes.get('target_branch', '')
            
            if ReviewService.check_mr_last_commit_id_exists(project_name, source_branch, target_branch, last_commit_id):
                logger.info(f"Merge Request with last_commit_id {last_commit_id} already exists, skipping review for {project_name}.")
                return

        # 仅仅在MR创建或更新时进行Code Review
        # 获取Merge Request的changes
        changes = handler.get_merge_request_changes()
        logger.info('changes: %s', changes)
        changes = filter_changes(changes)
        if not changes:
            logger.info('未检测到有关代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            return
        # 统计本次新增、删除的代码总数
        additions = 0
        deletions = 0
        for item in changes:
            additions += item.get('additions', 0)
            deletions += item.get('deletions', 0)

        # 获取Merge Request的commits
        commits = handler.get_merge_request_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        # review 代码 - 使用批量审查方法
        project_name = webhook_data['project']['name']
        commits_text = ';'.join(commit['title'] for commit in commits)
        code_reviewer = CodeReviewer()
        review_result = code_reviewer.review_changes_in_batches(changes, commits_text, project_name)

        # 将review结果提交到Gitlab的 notes
        handler.add_merge_request_notes(f'Auto Review Result: \n{review_result}')

        # dispatch merge_request_reviewed event
        event_manager['merge_request_reviewed'].send(
            MergeRequestReviewEntity(
                project_name=webhook_data['project']['name'],
                author=webhook_data['user']['username'],
                source_branch=webhook_data['object_attributes']['source_branch'],
                target_branch=webhook_data['object_attributes']['target_branch'],
                updated_at=int(datetime.now().timestamp()),
                commits=commits,
                score=CodeReviewer.parse_review_score(review_text=review_result),
                url=webhook_data['object_attributes']['url'],
                review_result=review_result,
                url_slug=gitlab_url_slug,
                webhook_data=webhook_data,
                additions=additions,
                deletions=deletions,
                last_commit_id=last_commit_id,
            )
        )

    except Exception as e:
        error_message = f'AI Code Review 服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)

def handle_github_push_event(webhook_data: dict, github_token: str, github_url: str, github_url_slug: str):
    push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'
    try:
        handler = GithubPushHandler(webhook_data, github_token, github_url)
        logger.info('GitHub Push event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        review_result = None
        score = 0
        additions = 0
        deletions = 0
        if push_review_enabled:
            # 获取PUSH的changes
            changes = handler.get_push_changes()
            logger.info('changes: %s', changes)
            changes = filter_github_changes(changes)
            if not changes:
                logger.info('未检测到PUSH代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            review_result = "关注的文件没有修改"

            if len(changes) > 0:
                project_name = webhook_data['repository']['name']
                commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
                code_reviewer = CodeReviewer()
                review_result = code_reviewer.review_changes_in_batches(changes, commits_text, project_name)
                score = CodeReviewer.parse_review_score(review_text=review_result)
                for item in changes:
                    additions += item.get('additions', 0)
                    deletions += item.get('deletions', 0)
            # 将review结果提交到GitHub的 notes
            handler.add_push_notes(f'Auto Review Result: \n{review_result}')

        event_manager['push_reviewed'].send(PushReviewEntity(
            project_name=webhook_data['repository']['name'],
            author=webhook_data['sender']['login'],
            branch=webhook_data['ref'].replace('refs/heads/', ''),
            updated_at=int(datetime.now().timestamp()),  # 当前时间
            commits=commits,
            score=score,
            review_result=review_result,
            url_slug=github_url_slug,
            webhook_data=webhook_data,
            additions=additions,
            deletions=deletions,
        ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_github_pull_request_event(webhook_data: dict, github_token: str, github_url: str, github_url_slug: str):
    '''
    处理GitHub Pull Request 事件
    :param webhook_data:
    :param github_token:
    :param github_url:
    :param github_url_slug:
    :return:
    '''
    merge_review_only_protected_branches = os.environ.get('MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED', '0') == '1'
    try:
        # 解析Webhook数据
        handler = GithubPullRequestHandler(webhook_data, github_token, github_url)
        logger.info('GitHub Pull Request event received')
        # 如果开启了仅review projected branches的，判断当前目标分支是否为projected branches
        if merge_review_only_protected_branches and not handler.target_branch_protected():
            logger.info("Merge Request target branch not match protected branches, ignored.")
            return

        if handler.action not in ['opened', 'synchronize']:
            logger.info(f"Pull Request Hook event, action={handler.action}, ignored.")
            return

        # 检查GitHub Pull Request的last_commit_id是否已经存在，如果存在则跳过处理
        github_last_commit_id = webhook_data['pull_request']['head']['sha']
        if github_last_commit_id:
            project_name = webhook_data['repository']['name']
            source_branch = webhook_data['pull_request']['head']['ref']
            target_branch = webhook_data['pull_request']['base']['ref']
            
            if ReviewService.check_mr_last_commit_id_exists(project_name, source_branch, target_branch, github_last_commit_id):
                logger.info(f"Pull Request with last_commit_id {github_last_commit_id} already exists, skipping review for {project_name}.")
                return

        # 仅仅在PR创建或更新时进行Code Review
        # 获取Pull Request的changes
        changes = handler.get_pull_request_changes()
        logger.info('changes: %s', changes)
        changes = filter_github_changes(changes)
        if not changes:
            logger.info('未检测到有关代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            return
        # 统计本次新增、删除的代码总数
        additions = 0
        deletions = 0
        for item in changes:
            additions += item.get('additions', 0)
            deletions += item.get('deletions', 0)

        # 获取Pull Request的commits
        commits = handler.get_pull_request_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        # review 代码 - 使用批量审查方法
        project_name = webhook_data['repository']['name']
        commits_text = ';'.join(commit['title'] for commit in commits)
        code_reviewer = CodeReviewer()
        review_result = code_reviewer.review_changes_in_batches(changes, commits_text, project_name)

        # 将review结果提交到GitHub的 notes
        handler.add_pull_request_notes(f'Auto Review Result: \n{review_result}')

        # dispatch pull_request_reviewed event
        event_manager['merge_request_reviewed'].send(
            MergeRequestReviewEntity(
                project_name=webhook_data['repository']['name'],
                author=webhook_data['pull_request']['user']['login'],
                source_branch=webhook_data['pull_request']['head']['ref'],
                target_branch=webhook_data['pull_request']['base']['ref'],
                updated_at=int(datetime.now().timestamp()),
                commits=commits,
                score=CodeReviewer.parse_review_score(review_text=review_result),
                url=webhook_data['pull_request']['html_url'],
                review_result=review_result,
                url_slug=github_url_slug,
                webhook_data=webhook_data,
                additions=additions,
                deletions=deletions,
                last_commit_id=github_last_commit_id,
            ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_gitea_push_event(webhook_data: dict, gitea_token: str, gitea_url: str, gitea_url_slug: str):
    push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'
    try:
        handler = GiteaPushHandler(webhook_data, gitea_token, gitea_url)
        logger.info('Gitea Push event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        review_result = None
        score = 0
        additions = 0
        deletions = 0
        if push_review_enabled:
            changes = handler.get_push_changes()
            logger.info('changes: %s', changes)
            changes = filter_gitea_changes(changes)
            if not changes:
                logger.info('未检测到PUSH代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            review_result = "关注的文件没有修改"

            if len(changes) > 0:
                project_name = webhook_data.get('repository', {}).get('name')
                commits_text = ';'.join(commit.get('message', '').strip() for commit in commits)
                code_reviewer = CodeReviewer()
                review_result = code_reviewer.review_changes_in_batches(changes, commits_text, project_name)
                score = CodeReviewer.parse_review_score(review_text=review_result)
                for item in changes:
                    additions += item.get('additions', 0)
                    deletions += item.get('deletions', 0)
            handler.add_push_notes(f'Auto Review Result: \n{review_result}')

        repository = webhook_data.get('repository', {})
        sender = webhook_data.get('sender', {}) or webhook_data.get('pusher', {}) or {}

        event_manager['push_reviewed'].send(PushReviewEntity(
            project_name=repository.get('name'),
            author=sender.get('login') or sender.get('username'),
            branch=handler.branch_name,
            updated_at=int(datetime.now().timestamp()),
            commits=commits,
            score=score,
            review_result=review_result,
            url_slug=gitea_url_slug,
            webhook_data=webhook_data,
            additions=additions,
            deletions=deletions,
        ))

    except Exception as e:
        error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)


def handle_gitea_pull_request_event(webhook_data: dict, gitea_token: str, gitea_url: str, gitea_url_slug: str):
    merge_review_only_protected_branches = os.environ.get('MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED', '0') == '1'
    try:
        handler = GiteaPullRequestHandler(webhook_data, gitea_token, gitea_url)
        logger.info('Gitea Pull Request event received')

        pull_request = webhook_data.get('pull_request', {})

        if merge_review_only_protected_branches and not handler.target_branch_protected():
            logger.info("Pull Request target branch not match protected branches, ignored.")
            return

        if handler.action not in ['opened', 'open', 'reopened', 'synchronize', 'synchronized']:
            logger.info(f"Pull Request Hook event, action={handler.action}, ignored.")
            return

        head_info = pull_request.get('head') or {}
        base_info = pull_request.get('base') or {}

        last_commit_id = head_info.get('sha') or pull_request.get('merge_commit_sha') or pull_request.get('last_commit_id')
        if last_commit_id:
            project_name = webhook_data.get('repository', {}).get('name')
            source_branch = head_info.get('ref') or pull_request.get('head_branch', '')
            target_branch = base_info.get('ref') or pull_request.get('base_branch', '')

            if ReviewService.check_mr_last_commit_id_exists(project_name, source_branch, target_branch, last_commit_id):
                logger.info(f"Pull Request with last_commit_id {last_commit_id} already exists, skipping review for {project_name}.")
                return

        changes = handler.get_pull_request_changes()
        logger.info('changes: %s', changes)
        changes = filter_gitea_changes(changes)
        if not changes:
            logger.info('未检测到有关代码的修改,修改文件可能不满足SUPPORTED_EXTENSIONS。')
            return

        additions = 0
        deletions = 0
        for item in changes:
            additions += item.get('additions', 0)
            deletions += item.get('deletions', 0)

        commits = handler.get_pull_request_commits()
        if not commits:
            logger.error('Failed to get commits for Gitea pull request')
            return

        project_name = webhook_data.get('repository', {}).get('name')
        commits_text = ';'.join(commit.get('title', '') for commit in commits)
        code_reviewer = CodeReviewer()
        review_result = code_reviewer.review_changes_in_batches(changes, commits_text, project_name)

        handler.add_pull_request_notes(f'Auto Review Result: \n{review_result}')

        repository = webhook_data.get('repository', {})
        author_info = pull_request.get('user', {}) or webhook_data.get('sender', {}) or {}

        event_manager['merge_request_reviewed'].send(
            MergeRequestReviewEntity(
                project_name=repository.get('name'),
                author=author_info.get('login') or author_info.get('username'),
                source_branch=head_info.get('ref') or pull_request.get('head_branch', ''),
                target_branch=base_info.get('ref') or pull_request.get('base_branch', ''),
                updated_at=int(datetime.now().timestamp()),
                commits=commits,
                score=CodeReviewer.parse_review_score(review_text=review_result),
                url=pull_request.get('html_url') or pull_request.get('url'),
                review_result=review_result,
                url_slug=gitea_url_slug,
                webhook_data=webhook_data,
                additions=additions,
                deletions=deletions,
                last_commit_id=last_commit_id,
            ))

    except Exception as e:
        error_message = f'AI Code Review 服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)
        logger.error('出现未知错误: %s', error_message)
