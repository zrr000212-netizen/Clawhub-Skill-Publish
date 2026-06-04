from git import Repo
from typing import Optional
from datetime import datetime
from utils.logger import get_logger


class GitClient:
    """Git 客户端"""

    def __init__(self, repo_url: str, local_path: str):
        self.repo_url = repo_url
        self.local_path = local_path
        self.logger = get_logger(__name__)
        self.repo: Optional[Repo] = None

    def clone(self, branch: str = "main"):
        """克隆仓库"""
        self.logger.info(f"克隆仓库: {self.repo_url} -> {self.local_path}")
        self.repo = Repo.clone_from(self.repo_url, self.local_path, branch=branch)

    def pull(self):
        """拉取最新代码"""
        self.logger.info("拉取最新代码")
        self.repo.remotes.origin.pull()

    def get_commits(self, since: Optional[datetime] = None) -> list[dict]:
        """获取提交记录"""
        commits = []
        for commit in self.repo.iter_commits():
            commit_date = datetime.fromtimestamp(commit.committed_date)
            if since and commit_date < since:
                break
            commits.append({
                "sha": commit.hexsha,
                "message": commit.message,
                "author": commit.author.name,
                "timestamp": commit_date
            })
        return commits
