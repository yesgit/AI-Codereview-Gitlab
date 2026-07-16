import os
import re
import time
from urllib.parse import urljoin, quote
import fnmatch
import requests

from biz.utils.log import logger
from biz.gitlab.ai_trigger_utils import contains_ai_trigger, should_skip_ai_note


def filter_changes(changes: list):
    '''
    过滤数据，只保留支持的文件类型以及必要的字段信息
    '''
    # 从环境变量中获取支持的文件扩展名
    supported_extensions = os.getenv('SUPPORTED_EXTENSIONS', '.java,.py,.php').split(',')

    filter_deleted_files_changes = [change for change in changes if not change.get("deleted_file")]

    # 过滤 `new_path` 以支持的扩展名结尾的元素, 仅保留diff和new_path字段
    filtered_changes = [
        {
            'diff': item.get('diff', ''),
            'new_path': item['new_path'],
            'additions': len(re.findall(r'^\+(?!\+\+)', item.get('diff', ''), re.MULTILINE)),
            'deletions': len(re.findall(r'^-(?!--)', item.get('diff', ''), re.MULTILINE))
        }
        for item in filter_deleted_files_changes
        if any(item.get('new_path', '').endswith(ext) for ext in supported_extensions)
    ]
    return filtered_changes


def slugify_url(original_url: str) -> str:
    """
    将原始URL转换为适合作为文件名的字符串，其中非字母或数字的字符会被替换为下划线，举例：
    slugify_url("http://example.com/path/to/repo/") => example_com_path_to_repo
    slugify_url("https://gitlab.com/user/repo.git") => gitlab_com_user_repo_git
    """
    # Remove URL scheme (http, https, etc.) if present
    original_url = re.sub(r'^https?://', '', original_url)

    # Replace non-alphanumeric characters (except underscore) with underscores
    target = re.sub(r'[^a-zA-Z0-9]', '_', original_url)

    # Remove trailing underscore if present
    target = target.rstrip('_')

    return target


def _normalize_base_url(u: str) -> str:
    """Ensure base URL has a scheme and trailing slash suitable for urljoin.

    If caller provided a URL without scheme (e.g. gitlab.com), default to https://.
    """
    if not u:
        return None
    u = u.strip()
    if not u.startswith(('http://', 'https://')):
        u = 'https://' + u
    if not u.endswith('/'):
        u = u + '/'
    return u


class MergeRequestHandler:
    def __init__(self, webhook_data: dict, gitlab_token: str, gitlab_url: str,
                 comment_url: str = None, comment_token: str = None,
                 comment_project_path: str = None):
        self.merge_request_iid = None
        self.webhook_data = webhook_data
        self.gitlab_token = gitlab_token
        self.gitlab_url = gitlab_url
        self.comment_url = comment_url or gitlab_url
        self.comment_token = comment_token or gitlab_token
        # 评论目标项目路径：优先使用配置的路径，否则用源库路径
        self.comment_project_path = comment_project_path or webhook_data.get('project', {}).get('path_with_namespace', '')
        self.event_type = None
        self.project_id = None
        self.action = None
        self.parse_event_type()

    def parse_event_type(self):
        # 提取 event_type
        self.event_type = self.webhook_data.get('object_kind', None)
        if self.event_type == 'merge_request':
            self.parse_merge_request_event()

    def parse_merge_request_event(self):
        # 提取 Merge Request 的相关参数
        merge_request = self.webhook_data.get('object_attributes', {})
        self.merge_request_iid = merge_request.get('iid')
        self.project_id = merge_request.get('target_project_id')
        self.action = merge_request.get('action')

    def get_merge_request_changes(self) -> list:
        # 检查是否为 Merge Request Hook 事件
        if self.event_type != 'merge_request':
            logger.warn(f"Invalid event type: {self.event_type}. Only 'merge_request' event is supported now.")
            return []

        # Gitlab merge request changes API可能存在延迟，多次尝试
        max_retries = 3  # 最大重试次数
        retry_delay = 10  # 重试间隔时间（秒）
        for attempt in range(max_retries):
            # 调用 GitLab API 获取 Merge Request 的 changes
            base = _normalize_base_url(self.gitlab_url)
            if not base:
                logger.error("gitlab_url not configured; cannot fetch merge request changes")
                return []
            url = urljoin(base, f"api/v4/projects/{self.project_id}/merge_requests/{self.merge_request_iid}/changes?access_raw_diffs=true")
            headers = {
                'Private-Token': self.gitlab_token
            }
            response = requests.get(url, headers=headers, verify=False)
            logger.debug(
                f"Get changes response from GitLab (attempt {attempt + 1}): {response.status_code}, {response.text}, URL: {url}")

            # 检查请求是否成功
            if response.status_code == 200:
                changes = response.json().get('changes', [])
                if changes:
                    return changes
                else:
                    logger.info(
                        f"Changes is empty, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries}), URL: {url}")
                    time.sleep(retry_delay)
            else:
                logger.warn(f"Failed to get changes from GitLab (URL: {url}): {response.status_code}, {response.text}")
                return []

        logger.warning(f"Max retries ({max_retries}) reached. Changes is still empty.")
        return []  # 达到最大重试次数后返回空列表

    def get_merge_request_commits(self) -> list:
        # 检查是否为 Merge Request Hook 事件
        if self.event_type != 'merge_request':
            return []

        # 调用 GitLab API 获取 Merge Request 的 commits
        base = _normalize_base_url(self.gitlab_url)
        if not base:
            logger.error("gitlab_url not configured; cannot fetch merge request commits")
            return []
        url = urljoin(base, f"api/v4/projects/{self.project_id}/merge_requests/{self.merge_request_iid}/commits")
        headers = {
            'Private-Token': self.gitlab_token
        }
        response = requests.get(url, headers=headers, verify=False)
        logger.debug(f"Get commits response from gitlab: {response.status_code}, {response.text}")
        # 检查请求是否成功
        if response.status_code == 200:
            return response.json()
        else:
            logger.warn(f"Failed to get commits: {response.status_code}, {response.text}")
            return []

    def add_merge_request_notes(self, review_result):
        base = _normalize_base_url(self.comment_url)
        if not base:
            logger.error("comment_url not configured; cannot add merge request notes")
            return
        # 使用 URL-encoded project_path 而非数字 project_id，确保跨实例兼容
        project_ref = quote(self.comment_project_path, safe='') if self.comment_project_path else str(self.project_id)
        url = urljoin(base, f"api/v4/projects/{project_ref}/merge_requests/{self.merge_request_iid}/notes")
        headers = {
            'Private-Token': self.comment_token,
            'Content-Type': 'application/json'
        }
        data = {
            'body': review_result
        }
        response = requests.post(url, headers=headers, json=data, verify=False)
        logger.debug(f"Add notes to gitlab {url}: {response.status_code}, {response.text}")
        if response.status_code == 201:
            logger.info("Note successfully added to merge request.")
        else:
            logger.error(f"Failed to add note: {response.status_code}")
            logger.error(response.text)

    def target_branch_protected(self) -> bool:
        base = _normalize_base_url(self.gitlab_url)
        if not base:
            logger.error("gitlab_url not configured; cannot check protected branches")
            return False
        url = urljoin(base, f"api/v4/projects/{self.project_id}/protected_branches")
        headers = {
            'Private-Token': self.gitlab_token,
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers, verify=False)
        logger.debug(f"Get protected branches response from gitlab: {response.status_code}, {response.text}")
        # 检查请求是否成功
        if response.status_code == 200:
            data = response.json()
            target_branch = self.webhook_data['object_attributes']['target_branch']
            return any(fnmatch.fnmatch(target_branch, item['name']) for item in data)
        else:
            logger.warn(f"Failed to get protected branches: {response.status_code}, {response.text}")
            return False


class NoteHandler:
    def __init__(self, webhook_data: dict, gitlab_token: str, gitlab_url: str,
                 comment_url: str = None, comment_token: str = None,
                 comment_project_path: str = None):
        self.webhook_data = webhook_data
        self.gitlab_token = gitlab_token
        self.gitlab_url = gitlab_url
        self.comment_url = comment_url or gitlab_url
        self.comment_token = comment_token or gitlab_token
        self.comment_project_path = comment_project_path or webhook_data.get('project', {}).get('path_with_namespace', '')
        self.event_type = None
        self.note_type = None  # Commit 或 MergeRequest
        self.note_body = None
        self.commit_id = None
        self.mr_iid = None
        self.project_id = None
        self.author = None
        self.parse_event_type()

    def parse_event_type(self):
        """解析 note 事件"""
        self.event_type = self.webhook_data.get('object_kind', None)
        if self.event_type == 'note':
            self.parse_note_event()

    def parse_note_event(self):
        """解析 note 事件参数"""
        object_attributes = self.webhook_data.get('object_attributes', {})
        self.note_type = object_attributes.get('noteable_type')
        self.note_body = object_attributes.get('note', '')
        self.noteable_iid = object_attributes.get('noteable_iid')
        
        # 获取评论作者
        user_info = self.webhook_data.get('user', {})
        self.author = user_info.get('username', 'Unknown')
        
        # 获取项目 ID
        self.project_id = self.webhook_data.get('project', {}).get('id')
        
        # 根据 note_type 设置具体的 ID
        if self.note_type == 'Commit':
            # 对于 commit，优先使用 commit_id 字段，如果不存在则使用 noteable_iid
            self.commit_id = object_attributes.get('commit_id') or self.noteable_iid
            
            # 获取真正的 commit 作者（从 webhook payload 中的 commit 字段）
            commit_info = self.webhook_data.get('commit', {})
            if commit_info and commit_info.get('author'):
                self.commit_author = commit_info.get('author', {}).get('name', 'Unknown')
            else:
                # 如果 payload 中没有 commit 作者信息，回退到评论者
                self.commit_author = self.author
        elif self.note_type == 'MergeRequest':
            self.mr_iid = self.noteable_iid

    def get_commit_diff(self) -> list:
        """获取单个 commit 的 diff"""
        if not self.commit_id:
            logger.error("Commit ID not found in note event")
            return []
        
        base = _normalize_base_url(self.gitlab_url)
        if not base:
            logger.error("gitlab_url not configured; cannot fetch commit diff")
            return []
        
        url = urljoin(base, f"api/v4/projects/{self.project_id}/repository/commits/{self.commit_id}/diff")
        headers = {
            'Private-Token': self.gitlab_token
        }
        
        response = requests.get(url, headers=headers, verify=False)
        logger.debug(f"Get commit diff response: {response.status_code}, URL: {url}")
        
        if response.status_code == 200:
            diffs = response.json()
            # 转换格式以兼容 filter_changes
            changes = []
            for diff in diffs:
                changes.append({
                    'diff': diff.get('diff', ''),
                    'new_path': diff.get('new_path', diff.get('old_path', '')),
                    'deleted_file': diff.get('deleted_file', False)
                })
            return changes
        else:
            logger.warn(f"Failed to get commit diff for {self.commit_id}: {response.status_code}")
            return []

    def get_merge_request_changes(self) -> list:
        """获取 MR 的 changes"""
        if not self.mr_iid or not self.project_id:
            logger.error("MR IID or project ID not found in note event")
            return []
        
        base = _normalize_base_url(self.gitlab_url)
        if not base:
            logger.error("gitlab_url not configured; cannot fetch MR changes")
            return []
        
        url = urljoin(base, f"api/v4/projects/{self.project_id}/merge_requests/{self.mr_iid}/changes?access_raw_diffs=true")
        headers = {
            'Private-Token': self.gitlab_token
        }
        
        response = requests.get(url, headers=headers, verify=False)
        logger.debug(f"Get MR changes response: {response.status_code}, URL: {url}")
        
        if response.status_code == 200:
            return response.json().get('changes', [])
        else:
            logger.warn(f"Failed to get MR changes: {response.status_code}")
            return []

    def add_commit_comment(self, message: str):
        """在 commit 上添加评论"""
        if not self.commit_id:
            logger.error("Commit ID not found, cannot add comment")
            return

        project_ref = quote(self.comment_project_path, safe='') if self.comment_project_path else str(self.project_id)
        base = _normalize_base_url(self.comment_url)
        if not base:
            logger.error("comment_url not configured; cannot add commit comment")
            return

        url = urljoin(base, f"api/v4/projects/{project_ref}/repository/commits/{self.commit_id}/comments")
        headers = {
            'Private-Token': self.comment_token,
            'Content-Type': 'application/json'
        }
        data = {
            'note': message
        }

        response = requests.post(url, headers=headers, json=data, verify=False)
        logger.debug(f"Add comment to commit {self.commit_id}: {response.status_code}")
        if response.status_code == 201:
            logger.info("Comment successfully added to commit.")
        else:
            logger.error(f"Failed to add comment: {response.status_code}")
            logger.error(response.text)

    def add_merge_request_comment(self, message: str):
        """在 MR 上添加评论"""
        if not self.mr_iid or not self.project_id:
            logger.error("MR IID or project ID not found, cannot add comment")
            return

        project_ref = quote(self.comment_project_path, safe='') if self.comment_project_path else str(self.project_id)
        base = _normalize_base_url(self.comment_url)
        if not base:
            logger.error("comment_url not configured; cannot add MR comment")
            return

        url = urljoin(base, f"api/v4/projects/{project_ref}/merge_requests/{self.mr_iid}/notes")
        headers = {
            'Private-Token': self.comment_token,
            'Content-Type': 'application/json'
        }
        data = {
            'body': message
        }

        response = requests.post(url, headers=headers, json=data, verify=False)
        logger.debug(f"Add comment to MR {self.mr_iid}: {response.status_code}")
        if response.status_code == 201:
            logger.info("Comment successfully added to merge request.")
        else:
            logger.error(f"Failed to add comment: {response.status_code}")
            logger.error(response.text)


class PushHandler:
    def __init__(self, webhook_data: dict, gitlab_token: str, gitlab_url: str,
                 comment_url: str = None, comment_token: str = None,
                 comment_project_path: str = None):
        self.webhook_data = webhook_data
        self.gitlab_token = gitlab_token
        self.gitlab_url = gitlab_url
        self.comment_url = comment_url or gitlab_url
        self.comment_token = comment_token or gitlab_token
        self.comment_project_path = comment_project_path or webhook_data.get('project', {}).get('path_with_namespace', '')
        self.event_type = None
        self.project_id = None
        self.branch_name = None
        self.commit_list = []
        self.parse_event_type()

    def parse_event_type(self):
        # 提取 event_type
        self.event_type = self.webhook_data.get('event_name', None)
        if self.event_type == 'push':
            self.parse_push_event()

    def parse_push_event(self):
        # 提取 Push 事件的相关参数
        self.project_id = self.webhook_data.get('project_id', None)
        if self.project_id is None:
            self.project_id = self.webhook_data.get('project', {}).get('id')
        self.branch_name = self.webhook_data.get('ref', '').replace('refs/heads/', '')
        self.commit_list = self.webhook_data.get('commits', [])

    def get_push_commits(self) -> list:
        # 检查是否为 Push 事件
        if self.event_type != 'push':
            logger.warn(f"Invalid event type: {self.event_type}. Only 'push' event is supported now.")
            return []

        # 提取提交信息
        commit_details = []
        for commit in self.commit_list:
            commit_info = {
                'message': commit.get('message'),
                'author': commit.get('author', {}).get('name'),
                'timestamp': commit.get('timestamp'),
                'url': commit.get('url'),
            }
            commit_details.append(commit_info)

        logger.info(f"Collected {len(commit_details)} commits from push event.")
        return commit_details

    def add_push_notes(self, message: str):
        # 添加评论到 GitLab Push 请求的提交中（此处假设是在最后一次提交上添加注释）
        if not self.commit_list:
            logger.warn("No commits found to add notes to.")
            return

        # 获取最后一个提交的ID
        last_commit_id = self.commit_list[-1].get('id')
        if not last_commit_id:
            logger.error("Last commit ID not found.")
            return

        project_ref = quote(self.comment_project_path, safe='') if self.comment_project_path else str(self.project_id)
        base = _normalize_base_url(self.comment_url)
        if not base:
            logger.error("comment_url not configured; cannot add push notes")
            return
        url = urljoin(base, f"api/v4/projects/{project_ref}/repository/commits/{last_commit_id}/comments")
        headers = {
            'Private-Token': self.comment_token,
            'Content-Type': 'application/json'
        }
        data = {
            'note': message
        }
        response = requests.post(url, headers=headers, json=data, verify=False)
        logger.debug(f"Add comment to commit {last_commit_id}: {response.status_code}, {response.text}")
        if response.status_code == 201:
            logger.info("Comment successfully added to push commit.")
        else:
            logger.error(f"Failed to add comment: {response.status_code}")
            logger.error(response.text)

    def __repository_commits(self, ref_name: str = "", since: str = "", until: str = "", pre_page: int = 100,
                             page: int = 1):
        # 获取仓库提交信息
        base = _normalize_base_url(self.gitlab_url)
        if not base:
            logger.error("gitlab_url not configured; cannot fetch repository commits")
            return []
        url = urljoin(base, f"api/v4/projects/{self.project_id}/repository/commits")
        url = f"{url}?ref_name={ref_name}&since={since}&until={until}&per_page={pre_page}&page={page}"
        headers = {
            'Private-Token': self.gitlab_token
        }
        response = requests.get(url, headers=headers, verify=False)
        logger.debug(
            f"Get commits response from GitLab for repository_commits: {response.status_code}, {response.text}, URL: {url}")

        if response.status_code == 200:
            return response.json()
        else:
            logger.warn(
                f"Failed to get commits for ref {ref_name}: {response.status_code}, {response.text}")
            return []

    def repository_compare(self, before: str, after: str):
        # 比较两个提交之间的差异
        base = _normalize_base_url(self.gitlab_url)
        if not base:
            logger.error("gitlab_url not configured; cannot compare repository commits")
            return []
        url = urljoin(base, f"api/v4/projects/{self.project_id}/repository/compare")
        url = f"{url}?from={before}&to={after}"
        headers = {
            'Private-Token': self.gitlab_token
        }
        response = requests.get(url, headers=headers, verify=False)
        logger.debug(
            f"Get changes response from GitLab for repository_compare: {response.status_code}, {response.text}, URL: {url}")

        if response.status_code == 200:
            return response.json().get('diffs', [])
        else:
            logger.warn(
                f"Failed to get changes for repository_compare: {response.status_code}, {response.text}")
            return []

    def get_commit_diff(self, commit_id: str) -> list:
        """获取单个 commit 的 diff"""
        base = _normalize_base_url(self.gitlab_url)
        if not base:
            logger.error("gitlab_url not configured; cannot fetch commit diff")
            return []
        url = urljoin(base, f"api/v4/projects/{self.project_id}/repository/commits/{commit_id}/diff")
        headers = {
            'Private-Token': self.gitlab_token
        }
        response = requests.get(url, headers=headers, verify=False)
        logger.debug(f"Get commit diff response: {response.status_code}, URL: {url}")
        
        if response.status_code == 200:
            diffs = response.json()
            # 转换格式以兼容 filter_changes
            changes = []
            for diff in diffs:
                changes.append({
                    'diff': diff.get('diff', ''),
                    'new_path': diff.get('new_path', diff.get('old_path', '')),
                    'deleted_file': diff.get('deleted_file', False)
                })
            return changes
        else:
            logger.warn(f"Failed to get commit diff for {commit_id}: {response.status_code}")
            return []

    def get_push_changes(self) -> list:
        # 检查是否为 Push 事件
        if self.event_type != 'push':
            logger.warn(f"Invalid event type: {self.event_type}. Only 'push' event is supported now.")
            return []

        # 如果没有提交，返回空列表
        if not self.commit_list:
            logger.info("No commits found in push event.")
            return []

        before = self.webhook_data.get('before', '')
        after = self.webhook_data.get('after', '')

        if not before or not after:
            logger.warn("Missing before or after commit SHA in webhook data.")
            return []

        if after.startswith('0000000'):
            # 删除分支处理
            logger.info("Branch deletion detected, no changes to review.")
            return []

        if before.startswith('0000000'):
            # 创建分支处理 - 使用单个提交的 diff API
            logger.info("New branch creation detected, using commit diff API.")
            if self.commit_list:
                latest_commit_id = after
                return self.get_commit_diff(latest_commit_id)
            else:
                return []
        else:
            # 正常的提交范围比较 - 使用 compare API
            logger.info(f"Comparing commits from {before} to {after}")
            return self.repository_compare(before, after)
