import re
from models.models import SkillInfo, PublishResult
from client.github_client import GitHubClient
from client.clawhub_client import ClawHubClient
from publisher.skill_publisher import SkillPublisher
from utils.published_versions_store import PublishedVersionsStore
from utils.logger import get_logger


class BatchPublisher:
    """批量发布器（含 commit SHA 去重）"""

    def __init__(self, github_client: GitHubClient, clawhub_client: ClawHubClient, clawhub_config=None, store: PublishedVersionsStore = None):
        self.github_client = github_client
        self.clawhub_client = clawhub_client
        self.clawhub_config = clawhub_config
        self.skill_publisher = SkillPublisher(clawhub_client, github_client, clawhub_config)
        self.store = store or PublishedVersionsStore()
        self.logger = get_logger(__name__)

    def scan_skills(self) -> list[SkillInfo]:
        """扫描仓库中的所有技能"""
        skills = []
        self._find_skill_files("", skills)
        return skills

    def _find_skill_files(self, path: str, skills: list[SkillInfo]):
        """递归查找 skill.md 文件"""
        try:
            files = self.github_client.get_files(path)
            for file in files:
                if file["type"] == "file" and file["name"].lower() == "skill.md":
                    skill_path = file["path"].replace("/" + file["name"], "")
                    skill_name = self.extract_skill_name(skill_path)
                    version = self._resolve_version(skill_name)
                    commit_sha = self._get_commit_sha(skill_path)
                    skills.append(SkillInfo(
                        skill_name=skill_name,
                        skill_path=skill_path,
                        version=version,
                        commit_sha=commit_sha
                    ))
                elif file["type"] == "dir":
                    self._find_skill_files(file["path"], skills)
        except Exception as e:
            self.logger.warning(f"扫描目录 {path} 失败: {str(e)}")

    def _get_commit_sha(self, skill_path: str) -> str:
        """获取 skill 目录的最新 commit SHA"""
        try:
            sha = self.github_client.get_dir_commit_sha(skill_path)
            if sha:
                self.logger.debug(f"{skill_path} 最新 commit SHA: {sha[:8]}")
            return sha
        except Exception as e:
            self.logger.warning(f"获取 {skill_path} commit SHA 失败: {str(e)}")
            return ""

    def extract_skill_name(self, skill_path: str) -> str:
        """从技能路径中提取技能名称"""
        parts = skill_path.split("/")
        skill_name = parts[-1]
        return self.convert_protected_slug(skill_name)

    def convert_protected_slug(self, slug: str) -> str:
        """转换受保护的 slug 为可用格式"""
        if slug.startswith("clawhub-"):
            return "clh-" + slug[8:]
        elif slug.endswith("-clawhub"):
            return slug[:-8] + "-mai"
        return slug

    def _resolve_version(self, skill_name: str) -> str:
        """版本号智能解析：ClawHub无此skill→0.0.1，有则Z+1"""
        owner = self.clawhub_config.owner if self.clawhub_config else ""
        latest = self.clawhub_client.get_latest_version(skill_name, owner=owner)
        if latest is None:
            version = "0.0.1"
            self.logger.info(f"ClawHub 无 {skill_name}，默认版本: {version}")
        else:
            parts = latest.split(".")
            if len(parts) == 3 and parts[2].isdigit():
                parts[2] = str(int(parts[2]) + 1)
                version = ".".join(parts)
            else:
                version = latest + ".1"
            self.logger.info(f"ClawHub 已有 {skill_name} v{latest}，自动递增: {version}")
        return version

    def publish_skills(self, skills: list[SkillInfo]) -> PublishResult:
        """批量发布技能（commit SHA 去重）"""
        total = len(skills)
        success = 0
        failed = 0
        skipped = 0
        failed_skills = []

        self.logger.info(f"开始批量发布，共 {total} 个技能")

        for i, skill in enumerate(skills):
            self.display_progress(total, i, skipped)
            if self.store.is_content_unchanged(skill.skill_name, skill.commit_sha):
                self.logger.info(f"跳过 {skill.skill_name}，内容未变 (commit SHA: {skill.commit_sha[:8]})")
                skipped += 1
                continue
            try:
                self.skill_publisher.publish(skill.skill_name, skill.version, skill.skill_path)
                self.store.mark_published(skill.skill_name, skill.version, skill.commit_sha)
                success += 1
            except Exception as e:
                failed += 1
                failed_skills.append({
                    "skill_name": skill.skill_name,
                    "version": skill.version,
                    "reason": str(e)
                })

        self.display_progress(total, total, skipped)
        self.logger.info(f"批量发布完成，成功 {success} 个，跳过 {skipped} 个，失败 {failed} 个")

        return PublishResult(
            total=total,
            success=success,
            failed=failed,
            failed_skills=failed_skills
        )

    def display_progress(self, total: int, current: int, skipped: int = 0):
        """显示发布进度"""
        percent = int(current / total * 100) if total > 0 else 0
        skip_info = f", 跳过 {skipped}" if skipped > 0 else ""
        print(f"\r进度: [{'=' * percent}{' ' * (100 - percent)}] {current}/{total} ({percent}%){skip_info}", end="", flush=True)
