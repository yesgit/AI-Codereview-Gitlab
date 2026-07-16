import os
import traceback
from datetime import datetime
from typing import Any

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.utils.queue import retry_task
from biz.event.event_manager import event_manager
from biz.gitlab.webhook_handler import filter_changes, MergeRequestHandler, PushHandler, NoteHandler, _normalize_base_url
from biz.gitlab.ai_trigger_utils import contains_ai_trigger, should_skip_ai_note, format_ai_review_result
from biz.github.webhook_handler import filter_changes as filter_github_changes, PullRequestHandler as GithubPullRequestHandler, PushHandler as GithubPushHandler
from biz.gitea.webhook_handler import filter_changes as filter_gitea_changes, PullRequestHandler as GiteaPullRequestHandler, \
    PushHandler as GiteaPushHandler
from biz.service.review_service import ReviewService
from biz.utils.code_reviewer import CodeReviewer
from biz.utils.im import notifier
from biz.utils.log import logger




# 可重试的异常类型
RETRYABLE_EXCEPTIONS = (
    'openai.APITimeoutError',
    'openai.APIConnectionError',
    'openai.RateLimitError',
    'httpx.TimeoutException',
    'httpx.ConnectTimeout',
    'httpx.ReadTimeout',
    'ConnectionError',
    'TimeoutError',
)


def _resolve_repo_for_event(webhook_data: dict, gitlab_url: str = "") -> tuple[str | None, str | None, str | None]:
    """Infer (repo_url, repo_key, ref) for agentic mode from a webhook payload.

    Returns (None, None, None) if it can't be determined (caller should degrade).
    """
    # GitLab MR
    if webhook_data.get("object_kind") == "merge_request":
        repo = webhook_data.get("project", {})
        path = repo.get("path_with_namespace") or repo.get("name")
        url = repo.get("git_http_url") or repo.get("url") or (gitlab_url.rstrip("/") + "/" + path if path and gitlab_url else None)
        attrs = webhook_data.get("object_attributes", {})
        ref = attrs.get("source_branch") or attrs.get("ref")
        sha = (attrs.get("last_commit") or {}).get("id")
        if path and url and (ref or sha):
            return url, path, sha or ref
        return None, None, None
    # GitLab push
    if webhook_data.get("object_kind") == "push":
        repo = webhook_data.get("project", {})
        path = repo.get("path_with_namespace") or repo.get("name")
        url = repo.get("git_http_url") or repo.get("url") or (gitlab_url.rstrip("/") + "/" + path if path and gitlab_url else None)
        ref = webhook_data.get("after") or webhook_data.get("ref")
        if path and url and ref:
            return url, path, ref
        return None, None, None
    # GitHub
    if "repository" in webhook_data and "pull_request" in webhook_data:
        repo = webhook_data["repository"]
        url = repo.get("clone_url") or repo.get("html_url")
        path = repo.get("full_name")
        pr = webhook_data["pull_request"]
        ref = pr.get("head", {}).get("sha") or pr.get("head", {}).get("ref")
        if path and url and ref:
            return url, path, ref
        return None, None, None
    if "repository" in webhook_data and "ref" in webhook_data:
        repo = webhook_data["repository"]
        url = repo.get("clone_url") or repo.get("html_url")
        path = repo.get("full_name")
        ref = webhook_data.get("after") or webhook_data.get("head_commit", {}).get("id")
        if path and url and ref:
            return url, path, ref
        return None, None, None
    # Gitea (similar shape to GitHub but `pusher` may be present).
    return None, None, None


def _estimate_complexity(changes: list) -> int:
    """估算 diff 复杂度：统计总新增行数"""
    total = 0
    for c in (changes or []):
        diff_text = c.get('diff', '') if isinstance(c, dict) else str(c)
        total += len([l for l in diff_text.split('\n') if l.startswith('+') and not l.startswith('+++')])
    return total


def _review_with_strategy(changes: list, commits_text: str, webhook_data: dict, gitlab_url: str,
                         review_strategy: str = 'diff_only') -> str:
    """Pick review strategy based on review_strategy parameter (project > env > default).

    review_strategy 可选值:
      - 'diff_only': 仅审查 diff
      - 'agentic':   始终使用 agent 深度审查
      - 'auto':      自适应：简单变更用 diff_only，复杂变更（>200 行新增）用 agentic
    """
    strategy = review_strategy or 'diff_only'

    if strategy == 'auto':
        complexity = _estimate_complexity(changes)
        threshold = int(os.getenv('AGENTIC_AUTO_THRESHOLD', '200'))
        strategy = 'agentic' if complexity > threshold else 'diff_only'
        logger.info(f"auto strategy: complexity={complexity} threshold={threshold} → {strategy}")

    if strategy != "agentic":
        return CodeReviewer().review_and_strip_code(str(changes), commits_text)

    # Agentic mode.
    from biz.agent.agentic_reviewer import AgenticReviewer
    repo_url, repo_key, ref = _resolve_repo_for_event(webhook_data, gitlab_url)
    if not (repo_url and repo_key and ref):
        logger.warning("could not resolve repo info for agentic mode, falling back to diff_only")
        return CodeReviewer().review_and_strip_code(str(changes), commits_text)
    cache_root = os.getenv("REPO_CACHE_DIR", "data/repo_cache")
    try:
        reviewer = AgenticReviewer(
            repo_url=repo_url,
            repo_key=repo_key,
            ref=ref,
            cache_root=cache_root,
        )
        return reviewer.review(diffs_text=str(changes), commits_text=commits_text)
    except Exception as e:
        logger.error("agentic reviewer raised unexpectedly, falling back: %s", e)
        return CodeReviewer().review_and_strip_code(str(changes), commits_text)




def is_retryable_error(error: Exception) -> bool:
    """判断异常是否可重试"""
    error_name = type(error).__name__
    error_module = type(error).__module__
    
    # 检查异常类型名称
    for retryable in RETRYABLE_EXCEPTIONS:
        if error_name == retryable.split('.')[-1] or \
           f"{error_module}.{error_name}" == retryable:
            return True
    
    # 检查异常消息
    error_msg = str(error).lower()
    retryable_keywords = ['timeout', 'connection', 'rate limit', 'temporarily unavailable']
    if any(keyword in error_msg for keyword in retryable_keywords):
        return True
    
    return False


def increment_retry_count(webhook_data: dict) -> int:
    """增加重试计数并返回当前重试次数"""
    retry_count = webhook_data.get('_retry_count', 0)
    webhook_data['_retry_count'] = retry_count + 1
    return retry_count + 1


def should_retry(webhook_data: dict) -> bool:
    """判断是否应该重试"""
    max_retries = int(os.getenv('MAX_RETRIES', '3'))
    current_retries = webhook_data.get('_retry_count', 0)
    return current_retries < max_retries


def handle_retry(webhook_data: dict, exception: Exception, handler_function, *args):
    """处理重试逻辑"""
    retry_count = increment_retry_count(webhook_data)
    max_retries = int(os.getenv('MAX_RETRIES', '3'))
    delay = int(os.getenv('RETRY_DELAY_SECONDS', '60'))
    
    logger.warning(f"任务失败 (第 {retry_count}/{max_retries} 次重试): {type(exception).__name__}: {str(exception)}")
    
    if retry_count < max_retries:
        logger.info(f"将在 {delay} 秒后重试...")
        retry_task(handler_function, webhook_data, *args, delay=delay)
    else:
        logger.error(f"已达到最大重试次数 {max_retries}，放弃重试")
        error_message = f'任务重试 {max_retries} 次后仍然失败: {str(exception)}\n{traceback.format_exc()}'
        notifier.send_notification(content=error_message)



def handle_push_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str,
                      comment_url: str = None, comment_token: str = None,
                      review_strategy: str = 'diff_only'):
    push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'
    try:
        handler = PushHandler(webhook_data, gitlab_token, gitlab_url, comment_url=comment_url, comment_token=comment_token)
        logger.info('Push Hook event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        # 提取 gitlab_base_url 和 project_slug
        gitlab_base_url = _normalize_base_url(gitlab_url)
        project_slug = webhook_data.get('project', {}).get('path_with_namespace')

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
                    gitlab_base_url=gitlab_base_url,
                    project_slug=project_slug,
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
                    review_result = code_reviewer.review_changes_in_batches(
                        all_changes, commits_text, project_name, gitlab_base_url, project_slug,
                        webhook_data.get('ref', '').replace('refs/heads/', '')
                    )
                    score = CodeReviewer.parse_review_score(review_text=review_result)
                    
                    # 发送该 author 的审查结果到 GitLab（在最后一次提交上添加评论）
                    if author_commit_list:
                        last_commit_id = None
                        for original_commit in webhook_data.get('commits', [])[::-1]:
                            if original_commit.get('author', {}).get('name') == author_name:
                                last_commit_id = original_commit.get('id')
                                break
                        
                        if last_commit_id:
                            # 直接调用 API 添加评论（使用评论目标地址）
                            from urllib.parse import urljoin, quote
                            _effective_url = comment_url or gitlab_url
                            _effective_token = comment_token or gitlab_token
                            base = _normalize_base_url(_effective_url)
                            if base:
                                # 使用 URL-encoded project_path 确保跨实例兼容
                                _project_ref = quote(handler.project_path, safe='') if handler.project_path else str(handler.project_id)
                                url = urljoin(base, f"api/v4/projects/{_project_ref}/repository/commits/{last_commit_id}/comments")
                                headers = {
                                    'Private-Token': _effective_token,
                                    'Content-Type': 'application/json'
                                }
                                data = {
                                    'note': f'🤖 AI Code Review Result (by {author_name})\n\n{review_result}'
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
                    gitlab_base_url=gitlab_base_url,
                    project_slug=project_slug,
                ))
            except Exception as e:
                logger.error(f"Error processing author {author_name}: {str(e)}")
                # 继续处理下一个 author，不中断整个流程
                continue

    except Exception as e:
        # 判断是否为可重试的异常
        if is_retryable_error(e):
            handle_retry(webhook_data, e, handle_push_event, gitlab_token, gitlab_url, gitlab_url_slug, comment_url, comment_token, review_strategy)
        else:
            error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
            notifier.send_notification(content=error_message)
def handle_note_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str,
                     comment_url: str = None, comment_token: str = None,
                     review_strategy: str = 'diff_only'):
    """
    处理 GitLab note 事件（@AI 触发评审）
    
    支持两种场景：
    1. 在 commit 上评论 @AI → 触发单个 commit 的代码评审
    2. 在 MR 上评论 @AI → 触发整个 MR 的代码评审
    """
    try:
        # 解析 note 事件
        handler = NoteHandler(webhook_data, gitlab_token, gitlab_url, comment_url=comment_url, comment_token=comment_token)
        logger.info(f'Note Hook event received, note_type={handler.note_type}')
        
        # 检查是否为有效的 note 事件
        if handler.note_type not in ['Commit', 'MergeRequest']:
            logger.info(f"Unsupported note_type: {handler.note_type}, only Commit and MergeRequest are supported.")
            return
        
        # 获取评论内容
        note_body = handler.note_body
        
        # 检查是否为 AI 系统添加的评论（避免死循环）
        if should_skip_ai_note(note_body):
            logger.info("Skipping AI system added comment to avoid infinite loop.")
            return
        
        # 检查是否包含 @AI 触发词
        if not contains_ai_trigger(note_body):
            logger.info("Note does not contain @AI trigger, skipping.")
            return
        
        # 提取 gitlab_base_url 和 project_slug
        gitlab_base_url = _normalize_base_url(gitlab_url)
        project_slug = webhook_data.get('project', {}).get('path_with_namespace')
        project_name = webhook_data.get('project', {}).get('name')
        
        # 根据 note_type 处理不同的评审场景
        if handler.note_type == 'Commit':
            _handle_commit_note_review(handler, gitlab_token, gitlab_url, gitlab_url_slug,
                                   gitlab_base_url, project_slug, project_name, note_body,
                                   comment_url, comment_token)
        elif handler.note_type == 'MergeRequest':
            _handle_mr_note_review(handler, gitlab_token, gitlab_url, gitlab_url_slug,
                                gitlab_base_url, project_slug, project_name, note_body, webhook_data,
                                comment_url, comment_token)
        
    except Exception as e:
        # 判断是否为可重试的异常
        if is_retryable_error(e):
            handle_retry(webhook_data, e, handle_note_event, gitlab_token, gitlab_url, gitlab_url_slug, comment_url, comment_token, review_strategy)
        else:
            error_message = f'AI Code Review 服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
            notifier.send_notification(content=error_message)
            logger.error('出现未知错误: %s', error_message)


def _handle_commit_note_review(handler, gitlab_token, gitlab_url, gitlab_url_slug,
                             gitlab_base_url, project_slug, project_name, note_body,
                             comment_url=None, comment_token=None):
    """处理 commit 上的 @AI 评审"""
    try:
        logger.info(f"Handling @AI review for commit {handler.commit_id}")
        
        # 获取 commit diff
        changes = handler.get_commit_diff()
        if not changes:
            logger.info(f"Commit {handler.commit_id} has no changes or failed to fetch diff.")
            handler.add_commit_comment("⚠️ 未获取到代码变更或变更不支持的文件类型。")
            return
        
        # 过滤变更
        changes = filter_changes(changes)
        if not changes:
            logger.info(f"Commit {handler.commit_id} has no supported file changes.")
            handler.add_commit_comment("⚠️ 关注的文件没有修改。")
            return
        
        # 统计变更
        additions = 0
        deletions = 0
        for item in changes:
            additions += item.get('additions', 0)
            deletions += item.get('deletions', 0)
        
        # 获取 commit 信息（使用真正的 commit 作者，而不是评论者）
        commit_message = "Review triggered by @AI comment"
        commit_author = getattr(handler, 'commit_author', handler.author)
        
        # 执行代码评审（commit 评审没有分支信息，无法使用分支级配置）
        code_reviewer = CodeReviewer()
        review_result = code_reviewer.review_changes_in_batches(
            changes, commit_message, project_name, gitlab_base_url, project_slug, branch_name=""
        )
        score = CodeReviewer.parse_review_score(review_text=review_result)
        
        # 格式化评审结果（添加触发源标识）
        formatted_result = format_ai_review_result(
            review_result,
            trigger_type=f"@AI comment by {handler.author} on commit {handler.commit_id[:8]}"
        )
        
        # 添加评论到 commit
        handler.add_commit_comment(formatted_result)
        
        # 发送 push_reviewed 事件（复用现有表记录）
        event_manager['push_reviewed'].send(PushReviewEntity(
            project_name=project_name,
            author=commit_author,  # 使用真正的 commit 作者
            branch="N/A",  # commit 评审没有分支信息
            updated_at=int(datetime.now().timestamp()),
            commits=[{
                'message': commit_message,
                'author': commit_author,
                'timestamp': str(datetime.now()),
            }],
            score=score,
            review_result=formatted_result,
            url_slug=gitlab_url_slug,
            webhook_data={'object_kind': 'note'},  # 标识来源
            # 添加评论者信息用于追踪
            comment_author=handler.author,
            additions=additions,
            deletions=deletions,
            gitlab_base_url=gitlab_base_url,
            project_slug=project_slug,
        ))
        
        logger.info(f"Successfully completed @AI review for commit {handler.commit_id}")
        
    except Exception as e:
        logger.error(f"Error handling commit note review: {str(e)}")
        # 向用户反馈错误
        handler.add_commit_comment(f"❌ AI 评审失败: {str(e)}")


def _handle_mr_note_review(handler, gitlab_token, gitlab_url, gitlab_url_slug,
                         gitlab_base_url, project_slug, project_name, note_body, webhook_data,
                         comment_url=None, comment_token=None):
    """处理 MR 上的 @AI 评审"""
    try:
        logger.info(f"Handling @AI review for MR {handler.mr_iid}")
        
        # 获取 MR changes
        changes = handler.get_merge_request_changes()
        if not changes:
            logger.info(f"MR {handler.mr_iid} has no changes or failed to fetch diff.")
            handler.add_merge_request_comment("⚠️ 未获取到代码变更或变更不支持的文件类型。")
            return
        
        # 过滤变更
        changes = filter_changes(changes)
        if not changes:
            logger.info(f"MR {handler.mr_iid} has no supported file changes.")
            handler.add_merge_request_comment("⚠️ 关注的文件没有修改。")
            return
        
        # 统计变更
        additions = 0
        deletions = 0
        for item in changes:
            additions += item.get('additions', 0)
            deletions += item.get('deletions', 0)
        
        # 获取 MR commits
        # 从 webhook_data 中获取 MR 信息
        merge_request = webhook_data.get('merge_request', {})
        
        # 如果 webhook_data 中没有 merge_request，需要通过 API 获取
        if not merge_request:
            import requests
            from urllib.parse import urljoin
            base = _normalize_base_url(gitlab_url)
            if base:
                url = urljoin(base, f"api/v4/projects/{handler.project_id}/merge_requests/{handler.mr_iid}")
                headers = {'Private-Token': gitlab_token}
                response = requests.get(url, headers=headers, verify=False)
                if response.status_code == 200:
                    merge_request = response.json()
        
        commits = merge_request.get('commits', []) or []
        
        # 获取 MR 作者（如果存在）
        mr_author = getattr(handler, 'mr_author', None)
        if not mr_author and merge_request:
            mr_author = merge_request.get('author', {}).get('username', handler.author)
        
        if not commits:
            logger.warn(f"MR {handler.mr_iid} has no commits.")
            commits = [{'title': 'Review triggered by @AI comment'}]
        
        # 执行代码评审
        commits_text = ';'.join(commit.get('title', '') for commit in commits)
        code_reviewer = CodeReviewer()
        review_result = code_reviewer.review_changes_in_batches(
            changes, commits_text, project_name, gitlab_base_url, project_slug,
            merge_request.get('source_branch', '')
        )
        score = CodeReviewer.parse_review_score(review_text=review_result)
        
        # 格式化评审结果（添加触发源标识）
        formatted_result = format_ai_review_result(
            review_result,
            trigger_type=f"@AI comment by {handler.author} on MR #{handler.mr_iid}"
        )
        
        # 添加评论到 MR
        handler.add_merge_request_comment(formatted_result)
        
        # 发送 merge_request_reviewed 事件（复用现有表记录）
        object_attributes = webhook_data.get('object_attributes', {})
        last_commit_id = object_attributes.get('last_commit', {}).get('id', '')
        
        # 使用 MR 作者而不是评论者
        author = mr_author or handler.author
        
        event_manager['merge_request_reviewed'].send(
            MergeRequestReviewEntity(
                project_name=project_name,
                author=author,  # 使用 MR 作者
                source_branch=merge_request.get('source_branch', ''),
                target_branch=merge_request.get('target_branch', ''),
                updated_at=int(datetime.now().timestamp()),
                commits=commits,
                score=score,
                url=merge_request.get('web_url', ''),
                review_result=formatted_result,
                url_slug=gitlab_url_slug,
                webhook_data={'object_kind': 'note'},  # 标识来源
                # 添加评论者信息用于追踪
                comment_author=handler.author,
                additions=additions,
                deletions=deletions,
                last_commit_id=last_commit_id,
                gitlab_base_url=gitlab_base_url,
                project_slug=project_slug,
            )
        )
        
        logger.info(f"Successfully completed @AI review for MR {handler.mr_iid}")
        
    except Exception as e:
        logger.error(f"Error handling MR note review: {str(e)}")
        # 向用户反馈错误
        handler.add_merge_request_comment(f"❌ AI 评审失败: {str(e)}")


def handle_merge_request_event(webhook_data: dict, gitlab_token: str, gitlab_url: str, gitlab_url_slug: str,
                               comment_url: str = None, comment_token: str = None,
                               review_strategy: str = 'diff_only'):
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
        handler = MergeRequestHandler(webhook_data, gitlab_token, gitlab_url, comment_url=comment_url, comment_token=comment_token)
        logger.info('Merge Request Hook event received')

        # 提取 gitlab_base_url 和 project_slug
        gitlab_base_url = _normalize_base_url(gitlab_url)
        project_slug = webhook_data.get('project', {}).get('path_with_namespace')

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
        review_result = code_reviewer.review_changes_in_batches(
            changes, commits_text, project_name, gitlab_base_url, project_slug,
            webhook_data['object_attributes']['source_branch']
        )

        # 将review结果提交到Gitlab的 notes，使用新格式避免包含@AI触发词
        handler.add_merge_request_notes(f'🤖 AI Code Review Result\n\n{review_result}')

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
                gitlab_base_url=gitlab_base_url,
                project_slug=project_slug,
            )
        )

    except Exception as e:
        # 判断是否为可重试的异常
        if is_retryable_error(e):
            handle_retry(webhook_data, e, handle_merge_request_event, gitlab_token, gitlab_url, gitlab_url_slug, comment_url, comment_token, review_strategy)
        else:
            error_message = f'AI Code Review 服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
            notifier.send_notification(content=error_message)
            logger.error('出现未知错误: %s', error_message)

def handle_github_push_event(webhook_data: dict, github_token: str, github_url: str, github_url_slug: str,
                             comment_url: str = None, comment_token: str = None,
                             review_strategy: str = 'diff_only'):
    push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'
    try:
        handler = GithubPushHandler(webhook_data, github_token, github_url)
        logger.info('GitHub Push event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        # 提取 github_base_url 和 project_slug
        from biz.utils.token_util import _normalize_base_url as normalize_url
        github_base_url = normalize_url(github_url)
        project_slug = webhook_data.get('repository', {}).get('full_name')

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
                review_result = code_reviewer.review_changes_in_batches(
                    changes, commits_text, project_name, github_base_url, project_slug,
                    webhook_data.get('ref', '').replace('refs/heads/', '')
                )
                score = CodeReviewer.parse_review_score(review_text=review_result)
                for item in changes:
                    additions += item.get('additions', 0)
                    deletions += item.get('deletions', 0)
            # 将review结果提交到GitHub的 notes，使用新格式避免包含@AI触发词
            handler.add_push_notes(f'🤖 AI Code Review Result\n\n{review_result}')

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
            gitlab_base_url=github_base_url,
            project_slug=project_slug,
        ))

    except Exception as e:
        # 判断是否为可重试的异常
        if is_retryable_error(e):
            handle_retry(webhook_data, e, handle_github_push_event, github_token, github_url, github_url_slug)
        else:
            error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
            notifier.send_notification(content=error_message)
            logger.error('出现未知错误: %s', error_message)


def handle_github_pull_request_event(webhook_data: dict, github_token: str, github_url: str, github_url_slug: str,
                                     comment_url: str = None, comment_token: str = None,
                                     review_strategy: str = 'diff_only'):
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

        # 提取 github_base_url 和 project_slug
        from biz.utils.token_util import _normalize_base_url as normalize_url
        github_base_url = normalize_url(github_url)
        project_slug = webhook_data.get('repository', {}).get('full_name')
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
        review_result = code_reviewer.review_changes_in_batches(
            changes, commits_text, project_name, github_base_url, project_slug,
            webhook_data['pull_request']['head']['ref']
        )

        # 将review结果提交到GitHub的 notes，使用新格式避免包含@AI触发词
        handler.add_pull_request_notes(f'🤖 AI Code Review Result\n\n{review_result}')

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
                gitlab_base_url=github_base_url,
                project_slug=project_slug,
            ))

    except Exception as e:
        # 判断是否为可重试的异常
        if is_retryable_error(e):
            handle_retry(webhook_data, e, handle_github_pull_request_event, github_token, github_url, github_url_slug)
        else:
            error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
            notifier.send_notification(content=error_message)
            logger.error('出现未知错误: %s', error_message)


def handle_gitea_push_event(webhook_data: dict, gitea_token: str, gitea_url: str, gitea_url_slug: str,
                            comment_url: str = None, comment_token: str = None,
                            review_strategy: str = 'diff_only'):
    push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'
    try:
        handler = GiteaPushHandler(webhook_data, gitea_token, gitea_url)
        logger.info('Gitea Push event received')
        commits = handler.get_push_commits()
        if not commits:
            logger.error('Failed to get commits')
            return

        # 提取 gitea_base_url 和 project_slug
        from biz.gitea.webhook_handler import _normalize_base_url as normalize_gitea_url
        gitea_base_url = normalize_gitea_url(gitea_url)
        project_slug = webhook_data.get('repository', {}).get('full_name')

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
                review_result = code_reviewer.review_changes_in_batches(
                    changes, commits_text, project_name, gitea_base_url, project_slug,
                    handler.branch_name
                )
                score = CodeReviewer.parse_review_score(review_text=review_result)
                for item in changes:
                    additions += item.get('additions', 0)
                    deletions += item.get('deletions', 0)
            handler.add_push_notes(f'🤖 AI Code Review Result\n\n{review_result}')

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
            gitlab_base_url=gitea_base_url,
            project_slug=project_slug,
        ))

    except Exception as e:
        # 判断是否为可重试的异常
        if is_retryable_error(e):
            handle_retry(webhook_data, e, handle_gitea_push_event, gitea_token, gitea_url, gitea_url_slug)
        else:
            error_message = f'服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
            notifier.send_notification(content=error_message)
            logger.error('出现未知错误: %s', error_message)


def handle_gitea_pull_request_event(webhook_data: dict, gitea_token: str, gitea_url: str, gitea_url_slug: str,
                                    comment_url: str = None, comment_token: str = None,
                                    review_strategy: str = 'diff_only'):
    merge_review_only_protected_branches = os.environ.get('MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED', '0') == '1'
    try:
        handler = GiteaPullRequestHandler(webhook_data, gitea_token, gitea_url)
        logger.info('Gitea Pull Request event received')

        # 提取 gitea_base_url 和 project_slug
        from biz.gitea.webhook_handler import _normalize_base_url as normalize_gitea_url
        gitea_base_url = normalize_gitea_url(gitea_url)
        project_slug = webhook_data.get('repository', {}).get('full_name')

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
        review_result = code_reviewer.review_changes_in_batches(
            changes, commits_text, project_name, gitea_base_url, project_slug,
            head_info.get('ref') or pull_request.get('head_branch', '')
        )

        handler.add_pull_request_notes(f'🤖 AI Code Review Result\n\n{review_result}')

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
                gitlab_base_url=gitea_base_url,
                project_slug=project_slug,
            ))

    except Exception as e:
        # 判断是否为可重试的异常
        if is_retryable_error(e):
            handle_retry(webhook_data, e, handle_gitea_pull_request_event, gitea_token, gitea_url, gitea_url_slug)
        else:
            error_message = f'AI Code Review 服务出现未知错误: {str(e)}\n{traceback.format_exc()}'
            notifier.send_notification(content=error_message)
            logger.error('出现未知错误: %s', error_message)
