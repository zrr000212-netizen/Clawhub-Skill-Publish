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

    # 支持 add/update，版本号可选（缺省默认 1.0.0）
    COMMIT_MESSAGE_PATTERN = re.compile(r"(?:add|update) skill: (?:skills/)?(?:\w+/)*(\S+)(?:\s+(v\d+\.\d+\.\d+))?")

    def __init__(self, github_client: GitHubClient, clawhub_client, clawhub_config=None, ai_changelog_generator=None, store: PublishedVersionsStore = None):
        self.github_client = github_client
        self.clawhub_client = clawhub_client
        self.clawhub_config = clawhub_config
        self.skill_publisher = SkillPublisher(clawhub_client, github_client, clawhub_config)
        self.ai_changelog_generator = ai_changelog_generator
        self.logger = get_logger(__name__)
        self.last_commit_sha: Optional[str] = None
        self.published_versions_store = store or PublishedVersionsStore()
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
            changelog = self.generate_changelog(commit_info.sha, commit_info.message, skill_info["version"],
                                                skill_name=skill_info["skill_name"], skill_path=skill_info["skill_path"])
            self.publish_skill(skill_info["skill_name"], skill_info["version"], skill_info["skill_path"], changelog, commit_sha=commit_info.sha)
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
        if version:
            self.logger.info(f"从 commit message 提取的原始版本号: {version}")
            # 去掉版本号中的所有 v 前缀（ClawHub CLI 会自动添加 v 前缀）
            while version.startswith('v'):
                version = version[1:]
        else:
            # 版本号缺省：查 ClawHub 已有版本，有则 Z+1，无则 0.0.1
            version = self._resolve_default_version(skill_name)
        self.logger.info(f"处理后的版本号: {version}")
        return {
            "skill_name": skill_name,
            "skill_path": skill_path,
            "version": version
        }

    def _resolve_default_version(self, skill_name: str) -> str:
        """版本号缺省时自动决定：ClawHub 无此 skill → 0.0.1，有则 Z+1"""
        owner = self.clawhub_config.owner if self.clawhub_config else ""
        latest = self.clawhub_client.get_latest_version(skill_name, owner=owner)
        if latest is None:
            version = "0.0.1"
            self.logger.info(f"ClawHub 无 {skill_name}，默认版本: {version}")
        else:
            # latest 格式如 "1.0.6"，Z+1
            parts = latest.split(".")
            if len(parts) == 3 and parts[2].isdigit():
                parts[2] = str(int(parts[2]) + 1)
                version = ".".join(parts)
            else:
                version = latest + ".1"
            self.logger.info(f"ClawHub 已有 {skill_name} v{latest}，自动递增: {version}")
        return version

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
                if item["type"] == "file" and item["name"].lower() == "skill.md":
                    return True
        except Exception as e:
            self.logger.debug(f"检查目录 {path} 失败: {str(e)}")
        return False

    def generate_changelog(self, commit_sha: str, commit_message: str, version: str, skill_name: str = "", skill_path: str = "") -> str:
        """生成条目式 changelog（始终使用 '- ' 格式，与 ClawHub auto 风格一致）

        优先级：
        1. AI 生成摘要 → 注入 extract_auto_changelog 做条目格式化
        2. 纯 extract_auto_changelog 从 SKILL.md 提取
        3. 兜底模板
        """
        ai_summary = ""
        if self.ai_changelog_generator:
            try:
                structured = self.ai_changelog_generator.generate_changelog(
                    commit_sha, commit_message, version
                )
                ai_summary = structured.raw_text
                self.logger.info(f"AI changelog 摘要: {structured.source} | {ai_summary}")
            except Exception as e:
                self.logger.error(f"AI changelog 生成异常: {str(e)}")

        # 从 SKILL.md 自动提取功能概括，生成条目式 changelog
        if skill_name and skill_path:
            auto_changelog = self.skill_publisher.extract_auto_changelog(
                skill_name, version, skill_path, ai_summary=ai_summary
            )
            source = "ai+auto" if ai_summary else "auto"
            self.logger.info(f"changelog 来源: {source} | {auto_changelog[:120]}...")
            return auto_changelog

        default_changelog = f"- Release {version} of {skill_name}." if skill_name else f"- Release {version}."
        self.logger.info(f"changelog 来源: default_template | {default_changelog}")
        return default_changelog

    def publish_skill(self, skill_name: str, version: str, skill_path: str, changelog: str = "", commit_sha: str = ""):
        """发布技能"""
        if self.published_versions_store.is_published(skill_name, version):
            self.logger.info(f"技能 {skill_name} {version} 已发布，跳过")
            return
        self.logger.info(f"发布技能: {skill_name} {version} (路径: {skill_path})")
        try:
            self.skill_publisher.publish(skill_name, version, skill_path, changelog=changelog)
            self.published_versions_store.mark_published(skill_name, version, commit_sha)
        except Exception as e:
            self.logger.error(f"发布技能失败: {skill_name} {version} - {str(e)}")
