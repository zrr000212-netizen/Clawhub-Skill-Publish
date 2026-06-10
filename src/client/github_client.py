import time
import requests
from typing import Optional
from datetime import datetime
from models.models import CommitInfo
from utils.logger import get_logger
from utils.retry import retry_with_backoff


class GitHubError(Exception):
    """GitHub API 错误"""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{status_code}] {message}")


class GitHubClient:
    """GitHub API 客户端"""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, owner: str, repo: str, branch: str = "main"):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.logger = get_logger(__name__)

    def _headers(self, accept="application/vnd.github.v3+json") -> dict:
        """构建请求头，token为空时不发Authorization（公开仓库无需认证）"""
        headers = {"Accept": accept}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def get_commits(self, since: Optional[datetime] = None) -> list[dict]:
        """获取提交记录"""
        url = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/commits"
        headers = self._headers()
        params = {
            "sha": self.branch
        }
        if since:
            params["since"] = since.isoformat()

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            self.handle_error(response)
            return response.json()
        except requests.exceptions.Timeout:
            raise GitHubError(0, "请求超时")
        except requests.exceptions.RequestException as e:
            raise GitHubError(0, f"请求失败: {str(e)}")

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def get_files(self, path: str = "") -> list[dict]:
        """获取文件列表"""
        url = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/contents/{path}"
        headers = self._headers()
        params = {
            "ref": self.branch
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            self.handle_error(response)
            return response.json()
        except requests.exceptions.Timeout:
            raise GitHubError(0, "请求超时")
        except requests.exceptions.RequestException as e:
            raise GitHubError(0, f"请求失败: {str(e)}")

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def get_file_content(self, path: str) -> str:
        """获取文件内容"""
        url = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/contents/{path}"
        headers = self._headers(accept="application/vnd.github.v3.raw")
        params = {
            "ref": self.branch
        }
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            self.handle_error(response)
            return response.text
        except requests.exceptions.Timeout:
            raise GitHubError(0, "请求超时")
        except requests.exceptions.RequestException as e:
            raise GitHubError(0, f"请求失败: {str(e)}")

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def get_dir_commit_sha(self, path: str) -> str:
        """获取指定目录下最新 commit SHA"""
        url = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/commits"
        headers = self._headers()
        params = {
            "sha": self.branch,
            "path": path,
            "per_page": 1
        }
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            self.handle_error(response)
            commits = response.json()
            if commits and len(commits) > 0:
                return commits[0]["sha"]
            return ""
        except requests.exceptions.Timeout:
            raise GitHubError(0, "请求超时")
        except requests.exceptions.RequestException as e:
            raise GitHubError(0, f"请求失败: {str(e)}")

    def handle_error(self, response: requests.Response):
        """处理错误"""
        if response.status_code == 200:
            return

        error_messages = {
            401: "GitHub Token 无效或已过期",
            403: "GitHub 权限不足",
            404: "GitHub 仓库不存在"
        }

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "5")
            self.logger.warning(f"限流中，等待 {retry_after} 秒后重试...")
            time.sleep(int(retry_after))
            raise GitHubError(429, "限流")

        message = error_messages.get(response.status_code, f"未知错误: {response.status_code}")
        raise GitHubError(response.status_code, message)
