import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai.agent_runtime import AgentRuntime, AgentConfig
from ai.llm_client import LLMClient, AIConfig, LLMError


class TestSelectStrategy:
    def setup_method(self):
        self.runtime = AgentRuntime(None)

    def test_docs_strategy(self):
        diff = "diff --git a/readme.md b/readme.md\n+new docs\n"
        assert self.runtime.select_strategy(diff) == "docs"

    def test_docs_mixed_extensions(self):
        diff = "diff --git a/guide.rst b/guide.rst\n+updated\n"
        assert self.runtime.select_strategy(diff) == "docs"

    def test_bugfix_strategy(self):
        diff = "diff --git a/main.py b/main.py\n+fix the login bug\n"
        assert self.runtime.select_strategy(diff) == "bugfix"

    def test_bugfix_issue_keyword(self):
        diff = "diff --git a/main.py b/main.py\n+resolve issue #123\n"
        assert self.runtime.select_strategy(diff) == "bugfix"

    def test_feature_strategy(self):
        diff = "diff --git a/main.py b/main.py\n+add new export feature\n"
        assert self.runtime.select_strategy(diff) == "feature"

    def test_feature_create_keyword(self):
        diff = "diff --git a/main.py b/main.py\n+create new module\n"
        assert self.runtime.select_strategy(diff) == "feature"

    def test_default_strategy(self):
        diff = "diff --git a/main.py b/main.py\n+some change\n"
        assert self.runtime.select_strategy(diff) == "default"

    def test_refactor_strategy(self):
        lines = []
        for i in range(6):
            lines.append(f"diff --git a/file{i}.py b/file{i}.py")
            lines.append("+rename class OldClass to NewClass")
        diff = "\n".join(lines) + "\n"
        assert self.runtime.select_strategy(diff) == "refactor"


class TestRunDirect:
    def test_successful_call(self):
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.chat_completion.return_value = {
            "choices": [{"message": {"content": "feat: add new API endpoint"}}]
        }
        config = AgentConfig(enabled=False)
        runtime = AgentRuntime(mock_llm, config)

        result = runtime._run_direct([{"role": "user", "content": "test"}])
        assert result == "feat: add new API endpoint"

    def test_empty_content(self):
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.chat_completion.return_value = {
            "choices": [{"message": {"content": ""}}]
        }
        config = AgentConfig(enabled=False)
        runtime = AgentRuntime(mock_llm, config)

        result = runtime._run_direct([{"role": "user", "content": "test"}])
        assert result == ""

    def test_llm_error(self):
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.chat_completion.side_effect = LLMError("transient", "timeout", retryable=True)
        config = AgentConfig(enabled=False)
        runtime = AgentRuntime(mock_llm, config)

        with pytest.raises(LLMError):
            runtime._run_direct([{"role": "user", "content": "test"}])


class TestRunWithTools:
    def test_agent_returns_content_without_tool_calls(self):
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.chat_completion.return_value = {
            "choices": [{"message": {"content": "fix: resolved timeout issue", "tool_calls": None}}]
        }
        config = AgentConfig(enabled=True, max_iterations=3, tools=["get_file_content"])
        runtime = AgentRuntime(mock_llm, config)

        result = runtime._run_with_tools(
            [{"role": "user", "content": "test"}], "diff content"
        )
        assert result == "fix: resolved timeout issue"

    def test_agent_max_iterations(self):
        mock_llm = MagicMock(spec=LLMClient)

        tool_call = {
            "id": "call_1",
            "function": {"name": "get_file_content", "arguments": "{}"},
        }

        mock_llm.chat_completion.return_value = {
            "choices": [{"message": {"content": "", "tool_calls": [tool_call]}}]
        }
        config = AgentConfig(enabled=True, max_iterations=2, tools=["get_file_content"])
        runtime = AgentRuntime(mock_llm, config)

        result = runtime._run_with_tools(
            [{"role": "user", "content": "test"}], "diff content"
        )
        assert mock_llm.chat_completion.call_count == 2


class TestRun:
    def test_agent_disabled_uses_direct(self):
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.chat_completion.return_value = {
            "choices": [{"message": {"content": "chore: update config"}}]
        }
        config = AgentConfig(enabled=False)
        runtime = AgentRuntime(mock_llm, config)

        result = runtime.run("some diff", "commit msg")
        assert result == "chore: update config"

    def test_custom_prompt_template_file_not_found(self):
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.chat_completion.return_value = {
            "choices": [{"message": {"content": "feat: test"}}]
        }
        config = AgentConfig(enabled=False, prompt_template="/nonexistent/path.txt")
        runtime = AgentRuntime(mock_llm, config)

        result = runtime.run("diff", "msg")
        assert result == "feat: test"