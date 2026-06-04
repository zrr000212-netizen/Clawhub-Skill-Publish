import os
import io
import zipfile
import json
import tempfile
import requests
import hashlib
from models.models import PublishPayload, PublishResponse
from client.clawhub_client import ClawHubClient, CLIError
from client.github_client import GitHubClient
from utils.logger import get_logger
from utils.retry import retry_with_backoff


class PublishError(Exception):
    """发布错误"""

    def __init__(self, skill_name: str, version: str, reason: str):
        self.skill_name = skill_name
        self.version = version
        self.reason = reason
        super().__init__(f"Failed to publish {skill_name} {version}: {reason}")


class SkillPublisher:
    """技能发布器"""

    def __init__(self, clawhub_client: ClawHubClient, github_client: GitHubClient):
        self.clawhub_client = clawhub_client
        self.github_client = github_client
        self.logger = get_logger(__name__)
        self.temp_dir = None

    def download_skill(self, skill_path: str) -> str:
        """从 GitHub 下载技能到本地临时目录"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="skill_")
        self.logger.info(f"创建临时目录: {self.temp_dir}")

        # 递归下载文件
        self._download_files(skill_path, self.temp_dir)

        return self.temp_dir

    def _download_files(self, path: str, local_dir: str):
        """递归下载文件"""
        try:
            items = self.github_client.get_files(path)
            for item in items:
                if item["type"] == "file":
                    # 下载文件内容
                    content = self._download_file_content(item["download_url"])
                    local_path = os.path.join(local_dir, item["name"])
                    with open(local_path, "wb") as f:
                        f.write(content)
                    self.logger.debug(f"下载文件: {item['path']} -> {local_path}")
                elif item["type"] == "dir":
                    # 创建子目录并递归下载
                    sub_dir = os.path.join(local_dir, item["name"])
                    os.makedirs(sub_dir, exist_ok=True)
                    self._download_files(item["path"], sub_dir)
        except Exception as e:
            self.logger.warning(f"下载目录 {path} 失败: {str(e)}")

    def _download_file_content(self, url: str) -> bytes:
        """下载文件内容"""
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content

    def extract_display_name(self, skill_path: str) -> str:
        """从 skill.md 提取显示名称"""
        try:
            items = self.github_client.get_files(skill_path)
            for item in items:
                if item["type"] == "file" and item["name"] == "skill.md":
                    content = self._download_file_content(item["download_url"])
                    text = content.decode("utf-8")
                    # 提取 displayName
                    for line in text.split("\n"):
                        if line.startswith("displayName:"):
                            return line.split(":", 1)[1].strip().strip("\"'")
        except Exception as e:
            self.logger.warning(f"提取显示名称失败: {str(e)}")
        # 如果没有找到，使用 skill_name
        return skill_path.split("/")[-1]

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def publish(self, skill_name: str, version: str, skill_path: str) -> PublishResponse:
        """发布技能"""
        try:
            # 下载技能到本地
            local_path = self.download_skill(skill_path)

            # 提取显示名称
            display_name = self.extract_display_name(skill_path)
            self.logger.info(f"显示名称: {display_name}")

            # 使用 CLI 发布
            response = self.clawhub_client.publish_skill(
                skill_path=local_path,
                slug=skill_name,
                display_name=display_name,
                version=version,
                changelog=f"Release {version}"
            )

            self.logger.info(f"技能发布成功: {skill_name} {version}")
            return response
        except CLIError as e:
            self.logger.error(f"技能发布失败: {skill_name} {version} - {e.message}")
            raise PublishError(skill_name, version, e.message)
        except Exception as e:
            self.logger.error(f"技能发布失败: {skill_name} {version} - {str(e)}")
            raise PublishError(skill_name, version, str(e))
        finally:
            # 清理临时目录
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"清理临时目录: {self.temp_dir}")
