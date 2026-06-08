import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai.ai_changelog_generator import AIChangelogGenerator, StructuredChangelog
from ai.llm_client import LLMClient, AIConfig, LLMError
from ai.agent_runtime import AgentConfig
from client.github_client import GitHubClient
from publisher.monitor_publisher import MonitorPublisher
from publisher.skill_publisher import SkillPublisher
from client.clawhub_client import ClawHubClient


def _make_ai_generator(llm_side_effect=None):
    ai_config = AIConfig(enabled=True, api_key="test-key", model="gpt-4")
    mock_llm = MagicMock(spec=LLMClient)
    if llm_side_effect:
        mock_llm.chat_completion.side_effect = llm_side_effect
    else:
        mock_llm.chat_completion.return_value = {
            "choices": [{"message": {"content": "feat: add new feature"}}]
        }
    mock_gh = MagicMock(spec=GitHubClient)
    mock_gh.owner = "test"
    mock_gh.repo = "test"
    mock_gh.token = "test"
    gen = AIChangelogGenerator(mock_llm, mock_gh, ai_config)
    return gen, mock_llm, mock_gh


class TestIntegrationAIChangelog:
    def test_scenario1_ai_success(self):
        gen, mock_llm, mock_gh = _make_ai_generator()

        mock_clawhub = MagicMock(spec=ClawHubClient)
        mock_clawhub.publish_skill.return_value = MagicMock(ok=True)

        with patch.object(gen, 'get_commit_diff', return_value="diff --git a/main.py b/main.py\n+new code"):
            changelog = gen.generate_changelog("abc123", "update skill: test v0.0.1", "0.0.1")
            assert changelog.source == "ai_generated"
            assert changelog.change_type == "feat"

    def test_scenario2_ai_fallback_to_commit_message(self):
        gen, mock_llm, mock_gh = _make_ai_generator(
            llm_side_effect=LLMError("permanent", "auth failed")
        )

        with patch.object(gen, 'get_commit_diff', return_value="some diff"):
            changelog = gen.generate_changelog(
                "abc123",
                "update skill: solution/sac/my-skill v0.0.1 - fixed login bug",
                "0.0.1"
            )
            assert changelog.source in ("commit_message", "default_template")

    def test_scenario3_ai_fallback_to_default_template(self):
        gen, mock_llm, mock_gh = _make_ai_generator(
            llm_side_effect=LLMError("permanent", "auth failed")
        )

        with patch.object(gen, 'get_commit_diff', return_value="some diff"):
            changelog = gen.generate_changelog(
                "abc123",
                "update skill: solution/sac/my-skill v0.0.1",
                "0.0.1"
            )
            assert changelog.source == "default_template"

    def test_scenario4_ai_disabled(self):
        mock_gh = MagicMock(spec=GitHubClient)
        mock_gh.owner = "test"
        mock_gh.repo = "test"
        mock_gh.token = "test"
        mock_gh.get_commits.return_value = []

        mock_clawhub = MagicMock(spec=ClawHubClient)

        monitor = MonitorPublisher(mock_gh, mock_clawhub, ai_changelog_generator=None)
        changelog = monitor.generate_changelog("abc123", "msg", "0.0.1")
        assert changelog == "Release 0.0.1"

    def test_scenario5_empty_diff_fallback(self):
        gen, mock_llm, mock_gh = _make_ai_generator()

        with patch.object(gen, 'get_commit_diff', return_value=""):
            changelog = gen.generate_changelog(
                "abc123",
                "update skill: solution/sac/my-skill v0.0.1 - fixed bug",
                "0.0.1"
            )
            assert changelog.source in ("commit_message", "default_template")

    def test_scenario6_circuit_breaker_then_fallback(self):
        ai_config = AIConfig(enabled=True, api_key="test-key", model="gpt-4", max_retries=0)
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.chat_completion.side_effect = LLMError("permanent", "auth failed")
        mock_llm._is_circuit_breaker_open = MagicMock(return_value=False)
        mock_llm._record_failure = MagicMock()

        mock_gh = MagicMock(spec=GitHubClient)
        mock_gh.owner = "test"
        mock_gh.repo = "test"
        mock_gh.token = "test"

        gen = AIChangelogGenerator(mock_llm, mock_gh, ai_config)

        with patch.object(gen, 'get_commit_diff', return_value="some diff"):
            changelog = gen.generate_changelog("abc123", "msg", "0.0.1")
            assert changelog.source in ("commit_message", "default_template")


class TestMonitorPublisherIntegration:
    def test_monitor_with_ai_changelog(self):
        gen, mock_llm, mock_gh = _make_ai_generator()

        mock_clawhub = MagicMock(spec=ClawHubClient)
        mock_skill_publisher = MagicMock(spec=SkillPublisher)

        with patch.object(gen, 'get_commit_diff', return_value="diff content"):
            monitor = MonitorPublisher(
                mock_gh, mock_clawhub,
                ai_changelog_generator=gen,
            )
            monitor.skill_publisher = mock_skill_publisher
            monitor.published_versions_store = MagicMock()
            monitor.published_versions_store.is_published.return_value = False

            changelog = monitor.generate_changelog("abc123", "msg", "0.0.1")
            assert changelog != "Release 0.0.1"

    def test_monitor_without_ai_changelog(self):
        mock_gh = MagicMock(spec=GitHubClient)
        mock_clawhub = MagicMock(spec=ClawHubClient)

        monitor = MonitorPublisher(mock_gh, mock_clawhub, ai_changelog_generator=None)
        changelog = monitor.generate_changelog("abc123", "msg", "0.0.1")
        assert changelog == "Release 0.0.1"