import json
import os
from pathlib import Path
from utils.logger import get_logger


class PublishedVersionsStore:
    """已发布版本持久化存储"""

    def __init__(self, store_file: str = ".published_versions.json"):
        self.store_file = store_file
        self.logger = get_logger(__name__)
        self.published_versions = set()
        self._load()

    def _load(self):
        """从文件加载已发布的版本"""
        if os.path.exists(self.store_file):
            try:
                with open(self.store_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.published_versions = set(data.get('versions', []))
                self.logger.info(f"加载已发布版本记录: {len(self.published_versions)} 个")
            except Exception as e:
                self.logger.warning(f"加载已发布版本记录失败: {str(e)}")
                self.published_versions = set()

    def _save(self):
        """保存已发布的版本到文件"""
        try:
            data = {
                'versions': list(self.published_versions)
            }
            with open(self.store_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"保存已发布版本记录: {len(self.published_versions)} 个")
        except Exception as e:
            self.logger.error(f"保存已发布版本记录失败: {str(e)}")

    def is_published(self, skill_name: str, version: str) -> bool:
        """检查版本是否已发布"""
        version_key = f"{skill_name}@{version}"
        return version_key in self.published_versions

    def mark_published(self, skill_name: str, version: str):
        """标记版本为已发布"""
        version_key = f"{skill_name}@{version}"
        if version_key not in self.published_versions:
            self.published_versions.add(version_key)
            self._save()

    def clear(self):
        """清空已发布版本记录"""
        self.published_versions.clear()
        self._save()