import json
import os
import subprocess
from pathlib import Path
from utils.logger import get_logger


class PublishedVersionsStore:
    """已发布版本持久化存储（含 commit SHA 去重 + Git 同步）"""

    def __init__(self, store_file: str = ".published_versions.json", repo_dir: str = ""):
        self.store_file = store_file
        self.repo_dir = repo_dir or os.path.dirname(os.path.abspath(store_file))
        self.logger = get_logger(__name__)
        self.skills = {}
        self._load()

    def _load(self):
        """从文件加载已发布的版本记录（兼容旧格式）"""
        if os.path.exists(self.store_file):
            try:
                with open(self.store_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if 'skills' in data:
                    self.skills = data['skills']
                elif 'versions' in data:
                    self._migrate_old_format(data['versions'])
                else:
                    self.skills = {}
                self.logger.info(f"加载已发布版本记录: {len(self.skills)} 个 skill")
            except Exception as e:
                self.logger.warning(f"加载已发布版本记录失败: {str(e)}")
                self.skills = {}

    def _migrate_old_format(self, versions: list):
        """从旧格式 {'versions': ['skill@0.0.1']} 迁移到新格式"""
        self.skills = {}
        for v in versions:
            if '@' in v:
                name, ver = v.rsplit('@', 1)
                self.skills[name] = {"version": ver, "commit_sha": ""}
        self.logger.info(f"迁移旧格式记录: {len(self.skills)} 个 skill")
        self._save(sync=False)

    def _save(self, sync: bool = True):
        """保存已发布的版本到文件"""
        try:
            data = {'skills': self.skills}
            with open(self.store_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"保存已发布版本记录: {len(self.skills)} 个 skill")
            if sync:
                self._git_sync()
        except Exception as e:
            self.logger.error(f"保存已发布版本记录失败: {str(e)}")

    def get_commit_sha(self, skill_name: str) -> str:
        """获取已存储的 commit SHA"""
        info = self.skills.get(skill_name)
        if info:
            return info.get("commit_sha", "")
        return ""

    def get_version(self, skill_name: str) -> str:
        """获取已存储的版本号"""
        info = self.skills.get(skill_name)
        if info:
            return info.get("version", "")
        return ""

    def is_published(self, skill_name: str, version: str) -> bool:
        """检查版本是否已发布"""
        info = self.skills.get(skill_name)
        if info:
            return info.get("version") == version
        return False

    def is_content_unchanged(self, skill_name: str, commit_sha: str) -> bool:
        """检查 skill 内容是否未变更（commit SHA 比对）"""
        if not commit_sha:
            return False
        stored_sha = self.get_commit_sha(skill_name)
        if not stored_sha:
            return False
        return stored_sha == commit_sha

    def mark_published(self, skill_name: str, version: str, commit_sha: str = "", sync: bool = True):
        """标记版本为已发布"""
        self.skills[skill_name] = {
            "version": version,
            "commit_sha": commit_sha
        }
        self._save(sync=sync)

    def clear(self):
        """清空已发布版本记录"""
        self.skills.clear()
        self._save()

    def git_pull(self):
        """从远程仓库拉取最新存储文件"""
        try:
            result = subprocess.run(
                ["git", "pull", "--rebase"],
                capture_output=True, text=True,
                cwd=self.repo_dir, timeout=30
            )
            if result.returncode == 0:
                self.logger.info(f"git pull 成功: {result.stdout.strip()}")
                self._load()
            else:
                self.logger.warning(f"git pull 失败: {result.stderr.strip()}")
        except Exception as e:
            self.logger.warning(f"git pull 异常: {str(e)}")

    def _git_sync(self):
        """将存储文件 commit + push 到远程仓库"""
        try:
            store_path = os.path.abspath(self.store_file)
            store_basename = os.path.basename(store_path)

            subprocess.run(
                ["git", "add", store_basename],
                capture_output=True, text=True,
                cwd=self.repo_dir, timeout=10
            )

            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                capture_output=True, text=True,
                cwd=self.repo_dir, timeout=10
            )
            if result.returncode == 0:
                return

            skill_summary = f"{len(self.skills)} skills"
            commit_msg = f"chore: update published_versions store [{skill_summary}]"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                capture_output=True, text=True,
                cwd=self.repo_dir, timeout=10
            )
            if result.returncode != 0:
                self.logger.warning(f"git commit 失败: {result.stderr.strip()}")
                return

            self._git_push()
        except Exception as e:
            self.logger.warning(f"git sync 异常: {str(e)}")

    def _git_push(self):
        """推送到远程仓库，失败时先 pull 再重试"""
        for attempt in range(2):
            result = subprocess.run(
                ["git", "push"],
                capture_output=True, text=True,
                cwd=self.repo_dir, timeout=30
            )
            if result.returncode == 0:
                self.logger.info("git push 成功")
                return
            if attempt == 0:
                self.logger.warning(f"git push 失败，尝试 pull --rebase 后重试: {result.stderr.strip()}")
                subprocess.run(
                    ["git", "pull", "--rebase"],
                    capture_output=True, text=True,
                    cwd=self.repo_dir, timeout=30
                )
            else:
                self.logger.error(f"git push 重试仍失败: {result.stderr.strip()}")
