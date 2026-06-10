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



class PublishError(Exception):
    """发布错误"""

    def __init__(self, skill_name: str, version: str, reason: str):
        self.skill_name = skill_name
        self.version = version
        self.reason = reason
        super().__init__(f"Failed to publish {skill_name} {version}: {reason}")


class SkillPublisher:
    """技能发布器"""

    def __init__(self, clawhub_client: ClawHubClient, github_client: GitHubClient, clawhub_config=None):
        self.clawhub_client = clawhub_client
        self.github_client = github_client
        self.clawhub_config = clawhub_config
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
        """下载文件内容（自动使用 GitHub 镜像）"""
        if "raw.githubusercontent.com" in url:
            url = url.replace("https://raw.githubusercontent.com", "https://ghfast.top/https://raw.githubusercontent.com")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content

    def extract_display_name(self, skill_path: str) -> str:
        """从 skill.md 提取显示名称"""
        try:
            items = self.github_client.get_files(skill_path)
            for item in items:
                if item["type"] == "file" and item["name"].lower() == "skill.md":
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

    def _read_skill_md(self, skill_path: str) -> str:
        """从 GitHub 读取 SKILL.md 内容"""
        try:
            items = self.github_client.get_files(skill_path)
            for item in items:
                if item["type"] == "file" and item["name"].lower() == "skill.md":
                    content = self._download_file_content(item["download_url"])
                    return content.decode("utf-8")
        except Exception as e:
            self.logger.warning(f"读取 SKILL.md 失败: {str(e)}")
        return ""

    def extract_auto_changelog(self, skill_name: str, version: str, skill_path: str, ai_summary: str = "") -> str:
        """从 SKILL.md 自动提取功能概括，生成 '- ' 条目式 changelog

        如果提供 ai_summary，将其作为首条摘要注入（AI 摘要 + SKILL.md 功能点）。
        生成格式示例 (与 ClawHub v1.0.0 auto 格式一致):
        - Initial release of my-skill.
        - Supports feature A, feature B, and feature C.
        - Easy usage: run command X to do Y.
        - Outputs results directly to the terminal.
        """
        import re

        text = self._read_skill_md(skill_path)
        changelog_items = []

        # 0) AI 摘要作为首条（如果提供）
        if ai_summary:
            # 清理 AI 摘要：去掉 conventional commit 前缀 (chore:/feat:/fix:/docs: 等)
            cleaned = re.sub(r'^(chore|feat|fix|docs|refactor|style|test|build|ci|perf)(\([^)]*\))?:\s*', '', ai_summary).strip()
            if cleaned:
                if not cleaned.endswith('.'):
                    cleaned += '.'
                changelog_items.append(cleaned)

        if text:
            lines = text.split("\n")

            # 1) 解析 frontmatter
            fm = {}
            in_fm = False
            for line in lines:
                if line.strip() == "---":
                    if in_fm:
                        break
                    in_fm = True
                    continue
                if in_fm:
                    m = re.match(r'^(\w[\w-]*):\s*(.*)', line)
                    if m:
                        key, val = m.group(1), m.group(2).strip()
                        if val.startswith('[') and val.endswith(']'):
                            fm[key] = [x.strip().strip('"').strip("'") for x in val[1:-1].split(',') if x.strip()]
                        elif val and val not in ('|', '>'):
                            fm[key] = val.strip('"').strip("'")
                        else:
                            fm[key] = []

            # 2) 从 description 提取核心功能（仅在没有 AI 摘要时，避免重复）
            if not ai_summary:
                desc = fm.get("description", "")
                if desc:
                    sentences = re.split(r'(?<=[.。；;])\s+', desc)
                    functional = []
                    for s in sentences:
                        s = s.strip()
                        if not s or len(s) < 5:
                            continue
                        if re.match(r'^(触发|前置|不适用|NOT|Requires?\s)', s, re.IGNORECASE):
                            continue
                        functional.append(s)
                    if functional:
                        combined = ' '.join(functional)
                        if not combined.endswith('.'):
                            combined += '.'
                        changelog_items.append(combined)

            # 3) 从正文 ## 章节标题提取关键功能点（英文风格）
            heading_map = {
                "核心命令": "core commands", "核心操作": "core operations",
                "完整执行流程": "complete execution workflow", "执行流程": "execution workflow",
                "部署报告模板": "deployment report template",
                "清理临时文件": "cleanup of temporary files",
                "陷阱速查": "pitfalls quick reference", "常见错误速查": "common errors reference",
                "环境变量清单": "environment variables reference",
                "CCE 部署 YAML 模板": "CCE deployment YAML template",
                "CCE 连接参数": "CCE connection parameters",
                "SWR 登录信息": "SWR login configuration",
                "适用场景": "use case scenarios",
                "项目参数": "project parameters",
                "输出格式": "output format", "验证方法": "verification method",
            }
            skip_headings = {"概述", "Overview", "前置条件", "Prerequisites", "参考文档",
                             "References", "注意事项", "Notes", "Pitfalls", "最佳实践",
                             "Best Practices", "See Also", "Related", "Gotchas"}

            body_start = False
            for line in lines:
                if line.strip() == "---":
                    body_start = not body_start
                    continue
                if body_start:
                    continue
                m = re.match(r'^##\s+(.+)', line)
                if m:
                    heading = m.group(1).strip()
                    if heading in skip_headings:
                        continue
                    en = heading_map.get(heading)
                    if not en:
                        short = heading.split("（")[0].split("(")[0].strip()
                        if re.search(r'[\u4e00-\u9fff]', short):
                            continue
                        en = short.lower()
                    if not any(en in item for item in changelog_items):
                        changelog_items.append(f"Provides {en}.")

        # 4) 兜底
        if not changelog_items:
            return f"- Release {version} of {skill_name}."

        # 5) 限制条目数（最多6条），组装
        items = changelog_items[:6]
        # 首条用 "Initial release" 或 "Update" 语气
        first_body = items[0].lstrip('- ')
        if version == "1.0.0":
            items[0] = f"- Initial release of {skill_name}."
        elif version.endswith(".0"):
            items[0] = f"- Update of {skill_name}: {first_body}"
        else:
            items[0] = f"- Update {skill_name}: {first_body}"

        # 确保每条以 "- " 开头
        result = []
        for item in items:
            if not item.startswith("- "):
                item = f"- {item}"
            result.append(item)

        return "\n".join(result)

    def publish(self, skill_name: str, version: str, skill_path: str, changelog: str = "") -> PublishResponse:
        """发布技能"""
        try:
            local_path = self.download_skill(skill_path)

            display_name = self.extract_display_name(skill_path)
            self.logger.info(f"显示名称: {display_name}")

            if not changelog:
                changelog = self.extract_auto_changelog(skill_name, version, skill_path)
                self.logger.info(f"自动生成 changelog (source=auto):\n{changelog}")

            owner = self.clawhub_config.owner if self.clawhub_config else ""
            response = self.clawhub_client.publish_skill(
                skill_path=local_path,
                slug=skill_name,
                display_name=display_name,
                version=version,
                changelog=changelog,
                owner=owner
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
