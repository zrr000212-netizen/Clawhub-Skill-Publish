import re
from models.models import SkillInfo, PublishResult
from client.github_client import GitHubClient
from publisher.skill_publisher import SkillPublisher
from utils.logger import get_logger


class BatchPublisher:
    """批量发布器"""

    def __init__(self, github_client: GitHubClient, clawhub_client: ClawHubClient):
        self.github_client = github_client
        self.clawhub_client = clawhub_client
        self.skill_publisher = SkillPublisher(clawhub_client, github_client)
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
                if file["type"] == "file" and file["name"] == "skill.md":
                    skill_path = file["path"].replace("/skill.md", "")
                    skill_name = self.extract_skill_name(skill_path)
                    skills.append(SkillInfo(
                        skill_name=skill_name,
                        skill_path=skill_path,
                        version="0.0.1"
                    ))
                elif file["type"] == "dir":
                    self._find_skill_files(file["path"], skills)
        except Exception as e:
            self.logger.warning(f"扫描目录 {path} 失败: {str(e)}")

    def extract_skill_name(self, skill_path: str) -> str:
        """从技能路径中提取技能名称"""
        parts = skill_path.split("/")
        skill_name = parts[-1]
        # 转换受保护的 slug
        return self.convert_protected_slug(skill_name)

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

    def publish_skills(self, skills: list[SkillInfo]) -> PublishResult:
        """批量发布技能"""
        total = len(skills)
        success = 0
        failed = 0
        failed_skills = []

        self.logger.info(f"开始批量发布，共 {total} 个技能")

        for i, skill in enumerate(skills):
            self.display_progress(total, i)
            try:
                self.skill_publisher.publish(skill.skill_name, skill.version, skill.skill_path)
                success += 1
            except Exception as e:
                failed += 1
                failed_skills.append({
                    "skill_name": skill.skill_name,
                    "version": skill.version,
                    "reason": str(e)
                })

        self.display_progress(total, total)
        self.logger.info(f"批量发布完成，成功 {success} 个，失败 {failed} 个")

        return PublishResult(
            total=total,
            success=success,
            failed=failed,
            failed_skills=failed_skills
        )

    def display_progress(self, total: int, current: int):
        """显示发布进度"""
        percent = int(current / total * 100) if total > 0 else 0
        print(f"\r进度: [{'=' * percent}{' ' * (100 - percent)}] {current}/{total} ({percent}%)", end="", flush=True)
