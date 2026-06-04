import re
import time
from typing import Optional
from datetime import datetime
from models.models import CommitInfo
from client.github_client import GitHubClient
from publisher.skill_publisher import SkillPublisher
from utils.logger import get_logger


class MonitorPublisher:
    """监控发布器"""

    COMMIT_MESSAGE_PATTERN = re.compile(r"update skill: solution/sac/(\S+) (v\d+\.\d+\.\d+)")

    def __init__(self, github_client: GitHubClient, clawhub_client: ClawHubClient):
        self.github_client = github_client
        self.clawhub_client = clawhub_client
        self.skill_publisher = SkillPublisher(clawhub_client, github_client)
        self.logger = get_logger(__name__)
        self.last_commit_sha: Optional[str] = None

    def monitor_commits(self, interval: int = 60):
        """监控提交记录"""
        self.logger.info(f"开始监控提交记录，间隔 {interval} 秒")
        while True:
            try:
                commits = self.github_client.get_commits()
                for commit in commits:
                    if commit["sha"] == self.last_commit_sha:
                        break
                    self.process_commit(commit)
                if commits:
                    self.last_commit_sha = commits[0]["sha"]
            except Exception as e:
                self.logger.error(f"监控提交记录失败: {str(e)}")
            time.sleep(interval)

    def process_commit(self, commit: dict):
        """处理提交"""
        commit_info = CommitInfo(
            sha=commit["sha"],
            message=commit["message"],
            author=commit["author"],
            timestamp=datetime.fromisoformat(commit["commit"]["author"]["date"])
        )
        self.logger.info(f"检测到新提交: {commit_info.sha} - {commit_info.message}")

        try:
            skill_info = self.extract_skill_info(commit_info.message)
            self.publish_skill(skill_info["skill_name"], skill_info["version"])
        except ValueError as e:
            self.logger.warning(f"提交消息格式错误: {str(e)}")

    def extract_skill_info(self, commit_message: str) -> dict:
        """从 commit message 中提取技能信息"""
        match = self.COMMIT_MESSAGE_PATTERN.search(commit_message)
        if not match:
            raise ValueError(f"提交消息格式错误: {commit_message}")
        skill_name = match.group(1)
        # 转换受保护的 slug
        skill_name = self.convert_protected_slug(skill_name)
        return {
            "skill_name": skill_name,
            "version": match.group(2)
        }

    def convert_protected_slug(self, slug: str) -> str:
        """转换受保护的 slug 为可用格式"""
        # 检查是否以 "clawhub-" 开头或以 "-clawhub" 结尾
        if slug.startswith("clawhub-"):
            # 使用缩写 "clh-"
            return "clh-" + slug[8:]
        elif slug.endswith("-clawhub"):
            # 添加后缀 "-mai"
            return slug[:-8] + "-mai"
        return slug

    def publish_skill(self, skill_name: str, version: str):
        """发布技能"""
        self.logger.info(f"发布技能: {skill_name} {version}")
        try:
            self.skill_publisher.publish(skill_name, version, skill_name)
        except Exception as e:
            self.logger.error(f"发布技能失败: {skill_name} {version} - {str(e)}")
