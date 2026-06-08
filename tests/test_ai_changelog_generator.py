import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai.ai_changelog_generator import (
    AIChangelogGenerator, StructuredChangelog,
    VALID_CHANGE_TYPES, CHANGE_TYPE_ALIASES,
)
from ai.llm_client import LLMClient, AIConfig, LLMError
from ai.agent_runtime import AgentConfig
from client.github_client import GitHubClient


def _make_generator():
    ai_config = AIConfig(enabled=True, api_key="test-key", model="gpt-4")
    mock_llm = MagicMock(spec=LLMClient)
    mock_gh = MagicMock(spec=GitHubClient)
    mock_gh.owner = "test"
    mock_gh.repo = "test"
    mock_gh.token = "test"
    gen = AIChangelogGenerator(mock_llm, mock_gh, ai_config)
    return gen, mock_llm, mock_gh


class TestValidateChangelog:
    def setup_method(self):
        self.gen, _, _ = _make_generator()

    def test_conventional_commits_format(self):
        cl = self.gen.validate_changelog("feat: add user authentication")
        assert cl.change_type == "feat"
        assert cl.summary == "add user authentication"
        assert cl.source == "ai_generated"

    def test_with_scope(self):
        cl = self.gen.validate_changelog("fix(api): resolve timeout issue")
        assert cl.change_type == "fix"
        assert cl.scope == "api"
        assert cl.summary == "resolve timeout issue"

    def test_markdown_code_block_stripped(self):
        cl = self.gen.validate_changelog("```\nfeat: new feature\n```")
        assert cl.change_type == "feat"
        assert cl.summary == "new feature"

    def test_alias_type_normalized(self):
        cl = self.gen.validate_changelog("feature: new export function")
        assert cl.change_type == "feat"

    def test_bugfix_alias(self):
        cl = self.gen.validate_changelog("bugfix: fix login crash")
        assert cl.change_type == "fix"

    def test_unknown_type_becomes_chore(self):
        cl = self.gen.validate_changelog("unknown_type: something happened")
        assert cl.change_type == "chore"

    def test_freeform_text(self):
        cl = self.gen.validate_changelog("修复了登录超时问题")
        assert cl.change_type == "chore"
        assert "修复了登录超时问题" in cl.summary

    def test_summary_truncated(self):
        long_summary = "x" * 250
        cl = self.gen.validate_changelog(f"feat: {long_summary}")
        assert len(cl.summary) <= 203
        assert cl.summary.endswith("...")

    def test_sensitive_info_redacted(self):
        cl = self.gen.validate_changelog("feat: added key sk-1234567890abcdef1234567890abcdef1234567890abcdef1234")
        assert "sk-" not in cl.summary
        assert "[REDACTED]" in cl.summary


class TestNormalizeChangeType:
    def setup_method(self):
        self.gen, _, _ = _make_generator()

    def test_valid_types_unchanged(self):
        for t in VALID_CHANGE_TYPES:
            assert self.gen._normalize_change_type(t) == t

    def test_aliases(self):
        assert self.gen._normalize_change_type("feature") == "feat"
        assert self.gen._normalize_change_type("bugfix") == "fix"
        assert self.gen._normalize_change_type("bug") == "fix"
        assert self.gen._normalize_change_type("documentation") == "docs"
        assert self.gen._normalize_change_type("performance") == "perf"

    def test_unknown_becomes_chore(self):
        assert self.gen._normalize_change_type("unknown") == "chore"
        assert self.gen._normalize_change_type("random") == "chore"


class TestFallbackChangelog:
    def setup_method(self):
        self.gen, _, _ = _make_generator()

    def test_commit_message_with_description(self):
        cl = self.gen.fallback_changelog(
            "update skill: solution/sac/my-skill v0.0.1 - fixed login bug", "0.0.1"
        )
        assert cl.source == "commit_message"
        assert "fixed login bug" in cl.summary

    def test_commit_message_without_description(self):
        cl = self.gen.fallback_changelog(
            "update skill: solution/sac/my-skill v0.0.1", "0.0.1"
        )
        assert cl.source == "default_template"

    def test_empty_commit_message(self):
        cl = self.gen.fallback_changelog("", "0.0.1")
        assert cl.source == "default_template"
        assert "0.0.1" in cl.summary

    def test_default_template_format(self):
        cl = self.gen.fallback_changelog("", "1.2.3")
        assert cl.raw_text == "chore: Release 1.2.3"


class TestStructuredChangelog:
    def test_auto_raw_text(self):
        cl = StructuredChangelog(change_type="feat", summary="new feature")
        assert cl.raw_text == "feat: new feature"

    def test_auto_raw_text_with_scope(self):
        cl = StructuredChangelog(change_type="fix", summary="bug fix", scope="api")
        assert cl.raw_text == "fix(api): bug fix"

    def test_custom_raw_text(self):
        cl = StructuredChangelog(
            change_type="feat", summary="new feature",
            raw_text="custom text", source="commit_message"
        )
        assert cl.raw_text == "custom text"


class TestGenerateChangelog:
    def test_diff_empty_fallback(self):
        gen, mock_llm, mock_gh = _make_generator()

        with patch.object(gen, 'get_commit_diff', return_value=""):
            cl = gen.generate_changelog("abc123", "update skill: test v0.0.1", "0.0.1")
            assert cl.source in ("commit_message", "default_template")

    def test_llm_error_fallback(self):
        gen, mock_llm, mock_gh = _make_generator()
        mock_llm.chat_completion.side_effect = LLMError("permanent", "auth failed")

        with patch.object(gen, 'get_commit_diff', return_value="diff content"):
            cl = gen.generate_changelog("abc123", "commit msg", "0.0.1")
            assert cl.source in ("commit_message", "default_template")

    def test_successful_generation(self):
        gen, mock_llm, mock_gh = _make_generator()
        mock_llm.chat_completion.return_value = {
            "choices": [{"message": {"content": "feat: add new API endpoint"}}]
        }

        with patch.object(gen, 'get_commit_diff', return_value="diff --git a/main.py b/main.py\n+new code"):
            cl = gen.generate_changelog("abc123", "commit msg", "0.0.1")
            assert cl.change_type == "feat"
            assert cl.source == "ai_generated"
            assert "add new API endpoint" in cl.summary


class TestGetCommitDiff:
    def test_success(self):
        gen, mock_llm, mock_gh = _make_generator()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "diff --git a/main.py b/main.py\n+new line"

        with patch('requests.get', return_value=mock_response):
            diff = gen.get_commit_diff("abc123")
            assert "new line" in diff

    def test_404_error(self):
        gen, mock_llm, mock_gh = _make_generator()

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('requests.get', return_value=mock_response):
            diff = gen.get_commit_diff("nonexistent")
            assert diff == ""

    def test_exception(self):
        gen, mock_llm, mock_gh = _make_generator()

        with patch('requests.get', side_effect=Exception("network error")):
            diff = gen.get_commit_diff("abc123")
            assert diff == ""