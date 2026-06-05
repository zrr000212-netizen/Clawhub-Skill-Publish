import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from publisher.monitor_publisher import MonitorPublisher
from publisher.skill_publisher import SkillPublisher
from client.github_client import GitHubClient
from client.clawhub_client import ClawHubClient


class TestMonitorPublisher:
    """测试 MonitorPublisher"""

    @pytest.fixture
    def mock_github_client(self):
        """模拟 GitHub 客户端"""
        client = Mock(spec=GitHubClient)
        return client

    @pytest.fixture
    def mock_clawhub_client(self):
        """模拟 ClawHub 客户端"""
        client = Mock(spec=ClawHubClient)
        return client

    @pytest.fixture
    def monitor_publisher(self, mock_github_client, mock_clawhub_client):
        """创建 MonitorPublisher 实例"""
        return MonitorPublisher(mock_github_client, mock_clawhub_client)

    def test_extract_skill_info_normal(self, monitor_publisher):
        """测试提取技能信息 - 正常情况"""
        commit_message = "update skill: skills/test-skill v0.0.1"
        mock_github_client = monitor_publisher.github_client
        mock_github_client.get_files.return_value = [
            {"type": "file", "name": "skill.md", "path": "skills/test-skill/skill.md"}
        ]

        result = monitor_publisher.extract_skill_info(commit_message)

        assert result["skill_name"] == "test-skill"
        assert result["version"] == "0.0.1"
        assert result["skill_path"] == "skills/test-skill"

    def test_extract_skill_info_with_protected_slug(self, monitor_publisher):
        """测试提取技能信息 - 受保护的 slug"""
        commit_message = "update skill: clawhub-api-guidance v0.0.1"
        mock_github_client = monitor_publisher.github_client
        mock_github_client.get_files.return_value = [
            {"type": "file", "name": "skill.md", "path": "clh-api-guidance/skill.md"}
        ]

        result = monitor_publisher.extract_skill_info(commit_message)

        assert result["skill_name"] == "clh-api-guidance"
        assert result["version"] == "0.0.1"

    def test_extract_skill_info_invalid_format(self, monitor_publisher):
        """测试提取技能信息 - 无效格式"""
        commit_message = "invalid commit message"

        with pytest.raises(ValueError, match="提交消息格式错误"):
            monitor_publisher.extract_skill_info(commit_message)

    def test_publish_skill_duplicate(self, monitor_publisher):
        """测试发布技能 - 重复发布"""
        monitor_publisher.published_versions.add("test-skill@0.0.1")

        monitor_publisher.publish_skill("test-skill", "0.0.1", "skills/test-skill")

        monitor_publisher.skill_publisher.publish.assert_not_called()

    def test_publish_skill_new_version(self, monitor_publisher):
        """测试发布技能 - 新版本"""
        monitor_publisher.publish_skill("test-skill", "0.0.1", "skills/test-skill")

        monitor_publisher.skill_publisher.publish.assert_called_once_with(
            "test-skill", "0.0.1", "skills/test-skill"
        )
        assert "test-skill@0.0.1" in monitor_publisher.published_versions

    def test_convert_protected_slug_clawhub_prefix(self, monitor_publisher):
        """测试转换受保护的 slug - clawhub- 前缀"""
        result = monitor_publisher.convert_protected_slug("clawhub-api-guidance")
        assert result == "clh-api-guidance"

    def test_convert_protected_slug_clawhub_suffix(self, monitor_publisher):
        """测试转换受保护的 slug - -clawhub 后缀"""
        result = monitor_publisher.convert_protected_slug("api-guidance-clawhub")
        assert result == "api-guidance-mai"

    def test_convert_protected_slug_normal(self, monitor_publisher):
        """测试转换受保护的 slug - 正常情况"""
        result = monitor_publisher.convert_protected_slug("test-skill")
        assert result == "test-skill"


class TestSkillPublisher:
    """测试 SkillPublisher"""

    @pytest.fixture
    def mock_github_client(self):
        """模拟 GitHub 客户端"""
        client = Mock(spec=GitHubClient)
        return client

    @pytest.fixture
    def mock_clawhub_client(self):
        """模拟 ClawHub 客户端"""
        client = Mock(spec=ClawHubClient)
        client.publish_skill.return_value = MagicMock(ok=True)
        return client

    @pytest.fixture
    def skill_publisher(self, mock_clawhub_client, mock_github_client):
        """创建 SkillPublisher 实例"""
        return SkillPublisher(mock_clawhub_client, mock_github_client)

    def test_publish_success(self, skill_publisher, mock_github_client, mock_clawhub_client):
        """测试发布成功"""
        mock_github_client.get_files.side_effect = [
            [
                {"type": "file", "name": "skill.md", "path": "test-skill/skill.md", "download_url": "http://example.com/skill.md"},
                {"type": "file", "name": "main.py", "path": "test-skill/main.py", "download_url": "http://example.com/main.py"}
            ]
        ]

        with patch('requests.get') as mock_get:
            mock_get.return_value.content = b"displayName: Test Skill"

            result = skill_publisher.publish("test-skill", "0.0.1", "test-skill")

            assert result.ok is True
            mock_clawhub_client.publish_skill.assert_called_once()

    def test_extract_display_name(self, skill_publisher, mock_github_client):
        """测试提取显示名称"""
        mock_github_client.get_files.return_value = [
            {"type": "file", "name": "skill.md", "path": "test-skill/skill.md", "download_url": "http://example.com/skill.md"}
        ]

        with patch('requests.get') as mock_get:
            mock_get.return_value.content = b"displayName: Test Skill\nversion: 0.0.1"

            result = skill_publisher.extract_display_name("test-skill")

            assert result == "Test Skill"

    def test_extract_display_name_fallback(self, skill_publisher, mock_github_client):
        """测试提取显示名称 - 回退到目录名"""
        mock_github_client.get_files.return_value = [
            {"type": "file", "name": "skill.md", "path": "test-skill/skill.md", "download_url": "http://example.com/skill.md"}
        ]

        with patch('requests.get') as mock_get:
            mock_get.return_value.content = b"version: 0.0.1"

            result = skill_publisher.extract_display_name("test-skill")

            assert result == "test-skill"