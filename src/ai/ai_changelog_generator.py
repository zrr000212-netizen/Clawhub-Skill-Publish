import re
import time
from dataclasses import dataclass, field
from typing import Optional
from client.github_client import GitHubClient, GitHubError
from ai.llm_client import LLMClient, LLMError, AIConfig
from ai.agent_runtime import AgentRuntime, AgentConfig
from ai.diff_processor import DiffProcessor, DiffConfig
from utils.logger import get_logger


VALID_CHANGE_TYPES = ["feat", "fix", "refactor", "docs", "style", "perf", "test", "chore"]

CHANGE_TYPE_ALIASES = {
    "feature": "feat",
    "bugfix": "fix",
    "bug": "fix",
    "hotfix": "fix",
    "patch": "fix",
    "improvement": "improve",
    "enhancement": "feat",
    "documentation": "docs",
    "performance": "perf",
    "refactoring": "refactor",
    "testing": "test",
    "build": "chore",
    "ci": "chore",
    "chore": "chore",
}


@dataclass
class StructuredChangelog:
    change_type: str
    summary: str
    scope: str = ""
    raw_text: str = ""
    source: str = "ai_generated"

    def __post_init__(self):
        if not self.raw_text:
            if self.scope:
                self.raw_text = f"{self.change_type}({self.scope}): {self.summary}"
            else:
                self.raw_text = f"{self.change_type}: {self.summary}"


class AIChangelogGenerator:
    def __init__(
        self,
        llm_client: LLMClient,
        github_client: GitHubClient,
        ai_config: AIConfig,
        agent_config: AgentConfig = None,
        diff_config: DiffConfig = None,
    ):
        self.llm_client = llm_client
        self.github_client = github_client
        self.ai_config = ai_config
        self.agent_config = agent_config or AgentConfig()
        self.diff_processor = DiffProcessor(diff_config)
        self.agent_runtime = AgentRuntime(llm_client, self.agent_config, github_client)
        self.logger = get_logger(__name__)

    def generate_changelog(self, commit_sha: str, commit_message: str, version: str = "") -> StructuredChangelog:
        start_time = time.time()
        try:
            diff = self.get_commit_diff(commit_sha)
            if not diff:
                self.logger.warning(f"commit {commit_sha} 的 diff 为空，回退到 commit message")
                return self.fallback_changelog(commit_message, version)

            processed_diff = self.diff_processor.process(diff)
            self.logger.info(f"diff 预处理完成，原始大小: {len(diff)}, 处理后大小: {len(processed_diff)}")

            changelog_text = self.agent_runtime.run(processed_diff, commit_message)
            if not changelog_text:
                self.logger.warning("AI 生成的 changelog 为空，回退到 commit message")
                return self.fallback_changelog(commit_message, version)

            changelog = self.validate_changelog(changelog_text)

            elapsed = time.time() - start_time
            self.logger.info(
                f"AI changelog 生成完成 | 耗时: {elapsed:.2f}s | "
                f"来源: {changelog.source} | 类型: {changelog.change_type} | "
                f"摘要: {changelog.summary[:50]}"
            )
            return changelog

        except LLMError as e:
            elapsed = time.time() - start_time
            self.logger.error(f"AI changelog 生成失败 ({e.error_type}): {e.message} | 耗时: {elapsed:.2f}s")
            return self.fallback_changelog(commit_message, version)
        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(f"AI changelog 生成异常: {str(e)} | 耗时: {elapsed:.2f}s")
            return self.fallback_changelog(commit_message, version)

    def get_commit_diff(self, commit_sha: str) -> str:
        try:
            url = f"{GitHubClient.BASE_URL}/repos/{self.github_client.owner}/{self.github_client.repo}/commits/{commit_sha}"
            headers = {
                "Authorization": f"Bearer {self.github_client.token}",
                "Accept": "application/vnd.github.v3.diff",
            }
            import requests
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                self.logger.error(f"commit {commit_sha} 不存在")
                return ""
            else:
                self.logger.error(f"获取 commit diff 失败: {response.status_code}")
                return ""
        except Exception as e:
            self.logger.error(f"获取 commit diff 异常: {str(e)}")
            return ""

    def validate_changelog(self, changelog_text: str) -> StructuredChangelog:
        changelog_text = changelog_text.strip()

        changelog_text = re.sub(r'^```[\w]*\n?', '', changelog_text)
        changelog_text = re.sub(r'\n?```$', '', changelog_text)
        changelog_text = changelog_text.strip()

        pattern = r'^(feat|fix|refactor|docs|style|perf|test|chore)(\([^)]+\))?:\s*(.+)$'
        match = re.match(pattern, changelog_text, re.IGNORECASE)

        if match:
            change_type = match.group(1).lower()
            scope = match.group(2).strip("()") if match.group(2) else ""
            summary = match.group(3).strip()
        else:
            change_type, scope, summary = self._parse_freeform_changelog(changelog_text)

        change_type = self._normalize_change_type(change_type)
        summary = summary[:200] + "..." if len(summary) > 200 else summary

        summary = self._redact_sensitive_in_changelog(summary)

        return StructuredChangelog(
            change_type=change_type,
            summary=summary,
            scope=scope,
            source="ai_generated",
        )

    def _parse_freeform_changelog(self, text: str) -> tuple[str, str, str]:
        for line in text.split('\n'):
            line = line.strip().lstrip('- •*').strip()
            if not line:
                continue

            type_pattern = r'^(feat|fix|refactor|docs|style|perf|test|chore|feature|bugfix|bug|hotfix|improvement|enhancement|documentation|performance|refactoring|testing|build|ci|chore)(\([^)]+\))?:\s*(.+)$'
            match = re.match(type_pattern, line, re.IGNORECASE)
            if match:
                return match.group(1).lower(), match.group(2).strip("()") if match.group(2) else "", match.group(3).strip()

        return "chore", "", text[:200]

    def _normalize_change_type(self, change_type: str) -> str:
        change_type = change_type.lower().strip()
        if change_type in VALID_CHANGE_TYPES:
            return change_type
        return CHANGE_TYPE_ALIASES.get(change_type, "chore")

    def _redact_sensitive_in_changelog(self, text: str) -> str:
        sensitive_patterns = [
            r'(?:api[_-]?key|token|secret|password|credential)\s*[:=]\s*["\']?[\w\-]{8,}',
            r'ghp_[\w]{36}',
            r'gho_[\w]{36}',
            r'sk-[\w]{48}',
        ]
        result = text
        for pattern in sensitive_patterns:
            result = re.sub(pattern, '[REDACTED]', result, flags=re.IGNORECASE)
        return result

    def fallback_changelog(self, commit_message: str, version: str = "") -> StructuredChangelog:
        if commit_message:
            clean_msg = commit_message.strip().split('\n')[0]
            clean_msg = re.sub(r'^update skill:\s*\S+\s+v?[\d.]+\s*', '', clean_msg).strip()
            clean_msg = clean_msg.lstrip('-: ').strip()
            if clean_msg:
                return StructuredChangelog(
                    change_type="chore",
                    summary=clean_msg[:200],
                    source="commit_message",
                )

        default_summary = f"Release {version}" if version else "Release"
        return StructuredChangelog(
            change_type="chore",
            summary=default_summary,
            source="default_template",
        )