import re
import time
from typing import Optional
from datetime import datetime
from models.models import CommitInfo
from client.github_client import GitHubClient
from publisher.skill_publisher import SkillPublisher
from utils.logger import get_logger
from utils.published_versions_store import PublishedVersionsStore


class MonitorPublisher:
    """监控发布器"""

    COMMIT_MESSAGE_PATTERN = re.compile(r"update skill: (?:skills/)?(?:\w+/)*(\S+) (v\d+\.\d+\.\d+)")

    def __init__(self, github_client: GitHubClient, clawhub_client, clawhub_config=None, ai_changelog_generator=None):
        self.github_client = github_client
        self.clawhub_client = clawhub_client
        self.skill_publisher = SkillPublisher(clawhub_client, github_client, clawhub_config)
        self.ai_changelog_generator = ai_changelog_generator
        self.logger = get_logger(__name__)
        self.last_commit_sha: Optional[str] = None
        self.published_versions_store = PublishedVersionsStore()
        if self.ai_changelog_generator:
            self.logger.info("AI Changelog 生成器已启用")
        else:
            self.logger.info("AI Changelog 生成器未启用，使用传统 changelog 生成方式")

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
            message=commit["commit"]["message"],
            author=commit["commit"]["author"]["name"],
            timestamp=datetime.fromisoformat(commit["commit"]["author"]["date"])
        )
        self.logger.info(f"检测到新提交: {commit_info.sha} - {commit_info.message}")

        try:
            skill_info = self.extract_skill_info(commit_info.message)
            changelog = self.generate_changelog(commit_info.sha, commit_info.message, skill_info["version"])
            self.publish_skill(skill_info["skill_name"], skill_info["version"], skill_info["skill_path"], changelog)
        except ValueError as e:
            self.logger.warning(f"提交消息格式不满足版本发布条件: {str(e)}")

    def extract_skill_info(self, commit_message: str) -> dict:
        """从 commit message 中提取技能信息"""
        match = self.COMMIT_MESSAGE_PATTERN.search(commit_message)
        if not match:
            raise ValueError(f"提交消息格式错误: {commit_message}")
        skill_name = match.group(1)
        # 转换受保护的 slug
        skill_name = self.convert_protected_slug(skill_name)
        # 在仓库中搜索技能的实际路径
        skill_path = self.find_skill_path(skill_name)
        if not skill_path:
            raise ValueError(f"在仓库中未找到技能: {skill_name}")
        version = match.group(2)
        self.logger.info(f"从 commit message 提取的原始版本号: {version}")
        # 去掉版本号中的所有 v 前缀（ClawHub CLI 会自动添加 v 前缀）
        while version.startswith('v'):
            version = version[1:]
        self.logger.info(f"处理后的版本号: {version}")
        return {
            "skill_name": skill_name,
            "skill_path": skill_path,
            "version": version
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

    def find_skill_path(self, skill_name: str) -> str:
        """在仓库中搜索技能路径"""
        self.logger.info(f"在仓库中搜索技能: {skill_name}")
        # 递归搜索仓库中的所有目录
        found_path = self._search_skill_recursive("", skill_name)
        if found_path:
            self.logger.info(f"找到技能路径: {found_path}")
        else:
            self.logger.warning(f"未找到技能: {skill_name}")
        return found_path

    def _search_skill_recursive(self, path: str, skill_name: str) -> str:
        """递归搜索技能目录"""
        try:
            items = self.github_client.get_files(path)
            for item in items:
                if item["type"] == "dir":
                    # 检查目录名是否匹配
                    if item["name"] == skill_name:
                        # 检查是否包含 skill.md
                        if self._has_skill_file(item["path"]):
                            return item["path"]
                    # 递归搜索子目录
                    result = self._search_skill_recursive(item["path"], skill_name)
                    if result:
                        return result
        except Exception as e:
            self.logger.debug(f"搜索目录 {path} 失败: {str(e)}")
        return None

    def _has_skill_file(self, path: str) -> bool:
        """检查目录是否包含 skill.md 文件"""
        try:
            items = self.github_client.get_files(path)
            for item in items:
                if item["type"] == "file" and item["name"] == "skill.md":
                    return True
        except Exception as e:
            self.logger.debug(f"检查目录 {path} 失败: {str(e)}")
        return False

    def generate_changelog(self, commit_sha: str, commit_message: str, version: str) -> str:
        """生成 changelog（AI 优先，回退到 commit message）"""
        if self.ai_changelog_generator:
            try:
                structured = self.ai_changelog_generator.generate_changelog(
                    commit_sha, commit_message, version
                )
                self.logger.info(f"changelog 来源: {structured.source} | {structured.raw_text}")
                return structured.raw_text
            except Exception as e:
                self.logger.error(f"AI changelog 生成异常，回退到默认方式: {str(e)}")

        default_changelog = f"Release {version}"
        self.logger.info(f"changelog 来源: default_template | {default_changelog}")
        return default_changelog

    def publish_skill(self, skill_name: str, version: str, skill_path: str, changelog: str = ""):
        """发布技能"""
        if self.published_versions_store.is_published(skill_name, version):
            self.logger.info(f"技能 {skill_name} {version} 已发布，跳过")
            return
        self.logger.info(f"发布技能: {skill_name} {version} (路径: {skill_path})")
        try:
            self.skill_publisher.publish(skill_name, version, skill_path, changelog=changelog)
            self.published_versions_store.mark_published(skill_name, version)
        except Exception as e:
            self.logger.error(f"发布技能失败: {skill_name} {version} - {str(e)}")
