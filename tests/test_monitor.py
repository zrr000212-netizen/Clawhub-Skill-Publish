import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import Mock, patch, MagicMock
from publisher.monitor_publisher import MonitorPublisher
from publisher.skill_publisher import SkillPublisher
from client.github_client import GitHubClient
from client.clawhub_client import ClawHubClient


def test_extract_skill_info_normal():
    """测试提取技能信息 - 正常情况"""
    print("\n=== 测试 extract_skill_info_normal ===")

    mock_github_client = Mock(spec=GitHubClient)
    mock_clawhub_client = Mock(spec=ClawHubClient)

    monitor_publisher = MonitorPublisher(mock_github_client, mock_clawhub_client)

    commit_message = "update skill: skills/test-skill v0.0.1"

    with patch.object(monitor_publisher, 'find_skill_path', return_value="skills/test-skill"):
        result = monitor_publisher.extract_skill_info(commit_message)

    print(f"skill_name: {result['skill_name']}")
    print(f"version: {result['version']}")
    print(f"skill_path: {result['skill_path']}")

    assert result["skill_name"] == "test-skill", f"Expected 'test-skill', got '{result['skill_name']}'"
    assert result["version"] == "0.0.1", f"Expected '0.0.1', got '{result['version']}'"
    assert result["skill_path"] == "skills/test-skill", f"Expected 'skills/test-skill', got '{result['skill_path']}'"

    print("✓ 测试通过")


def test_extract_skill_info_with_protected_slug():
    """测试提取技能信息 - 受保护的 slug"""
    print("\n=== 测试 extract_skill_info_with_protected_slug ===")

    mock_github_client = Mock(spec=GitHubClient)
    mock_clawhub_client = Mock(spec=ClawHubClient)

    monitor_publisher = MonitorPublisher(mock_github_client, mock_clawhub_client)

    commit_message = "update skill: clawhub-api-guidance v0.0.1"

    with patch.object(monitor_publisher, 'find_skill_path', return_value="clh-api-guidance"):
        result = monitor_publisher.extract_skill_info(commit_message)

    print(f"skill_name: {result['skill_name']}")
    print(f"version: {result['version']}")

    assert result["skill_name"] == "clh-api-guidance", f"Expected 'clh-api-guidance', got '{result['skill_name']}'"
    assert result["version"] == "0.0.1", f"Expected '0.0.1', got '{result['version']}'"

    print("✓ 测试通过")


def test_extract_skill_info_invalid_format():
    """测试提取技能信息 - 无效格式"""
    print("\n=== 测试 extract_skill_info_invalid_format ===")

    mock_github_client = Mock(spec=GitHubClient)
    mock_clawhub_client = Mock(spec=ClawHubClient)

    monitor_publisher = MonitorPublisher(mock_github_client, mock_clawhub_client)

    commit_message = "invalid commit message"

    try:
        result = monitor_publisher.extract_skill_info(commit_message)
        print(f"✗ 测试失败：应该抛出 ValueError，但返回了 {result}")
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        print(f"✓ 测试通过：正确抛出 ValueError: {e}")


def test_publish_skill_duplicate():
    """测试发布技能 - 重复发布"""
    print("\n=== 测试 publish_skill_duplicate ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        store_file = os.path.join(tmpdir, "test_published_versions.json")

        mock_github_client = Mock(spec=GitHubClient)
        mock_clawhub_client = Mock(spec=ClawHubClient)
        mock_skill_publisher = Mock(spec=SkillPublisher)

        with patch('publisher.monitor_publisher.PublishedVersionsStore') as MockStore:
            MockStore.return_value.__class__ = type('Store', (), {
                'is_published': lambda self, name, ver: False,
                'mark_published': lambda self, name, ver: None
            })

            monitor_publisher = MonitorPublisher(mock_github_client, mock_clawhub_client)
            monitor_publisher.skill_publisher = mock_skill_publisher

            monitor_publisher.published_versions_store.mark_published("test-skill", "0.0.1")

            monitor_publisher.publish_skill("test-skill", "0.0.1", "skills/test-skill")

            mock_skill_publisher.publish.assert_not_called()
            print("✓ 测试通过：重复发布被正确跳过")


def test_publish_skill_new_version():
    """测试发布技能 - 新版本"""
    print("\n=== 测试 publish_skill_new_version ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        store_file = os.path.join(tmpdir, "test_published_versions.json")

        mock_github_client = Mock(spec=GitHubClient)
        mock_clawhub_client = Mock(spec=ClawHubClient)
        mock_skill_publisher = Mock(spec=SkillPublisher)

        with patch('publisher.monitor_publisher.PublishedVersionsStore') as MockStore:
            published_set = set()

            class TestStore:
                def is_published(self, name, ver):
                    return f"{name}@{ver}" in published_set

                def mark_published(self, name, ver):
                    published_set.add(f"{name}@{ver}")

            MockStore.return_value = TestStore()

            monitor_publisher = MonitorPublisher(mock_github_client, mock_clawhub_client)
            monitor_publisher.skill_publisher = mock_skill_publisher

            monitor_publisher.publish_skill("test-skill", "0.0.1", "skills/test-skill")

            mock_skill_publisher.publish.assert_called_once_with(
                "test-skill", "0.0.1", "skills/test-skill"
            )
            print("✓ 测试通过：新版本发布成功")


def test_convert_protected_slug_clawhub_prefix():
    """测试转换受保护的 slug - clawhub- 前缀"""
    print("\n=== 测试 convert_protected_slug_clawhub_prefix ===")

    mock_github_client = Mock(spec=GitHubClient)
    mock_clawhub_client = Mock(spec=ClawHubClient)

    monitor_publisher = MonitorPublisher(mock_github_client, mock_clawhub_client)

    result = monitor_publisher.convert_protected_slug("clawhub-api-guidance")
    print(f"Input: clawhub-api-guidance, Output: {result}")

    assert result == "clh-api-guidance", f"Expected 'clh-api-guidance', got '{result}'"
    print("✓ 测试通过")


def test_convert_protected_slug_clawhub_suffix():
    """测试转换受保护的 slug - -clawhub 后缀"""
    print("\n=== 测试 convert_protected_slug_clawhub_suffix ===")

    mock_github_client = Mock(spec=GitHubClient)
    mock_clawhub_client = Mock(spec=ClawHubClient)

    monitor_publisher = MonitorPublisher(mock_github_client, mock_clawhub_client)

    result = monitor_publisher.convert_protected_slug("api-guidance-clawhub")
    print(f"Input: api-guidance-clawhub, Output: {result}")

    assert result == "api-guidance-mai", f"Expected 'api-guidance-mai', got '{result}'"
    print("✓ 测试通过")


def test_convert_protected_slug_normal():
    """测试转换受保护的 slug - 正常情况"""
    print("\n=== 测试 convert_protected_slug_normal ===")

    mock_github_client = Mock(spec=GitHubClient)
    mock_clawhub_client = Mock(spec=ClawHubClient)

    monitor_publisher = MonitorPublisher(mock_github_client, mock_clawhub_client)

    result = monitor_publisher.convert_protected_slug("test-skill")
    print(f"Input: test-skill, Output: {result}")

    assert result == "test-skill", f"Expected 'test-skill', got '{result}'"
    print("✓ 测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("开始运行 MonitorPublisher 测试")
    print("=" * 60)

    tests = [
        test_extract_skill_info_normal,
        test_extract_skill_info_with_protected_slug,
        test_extract_skill_info_invalid_format,
        test_publish_skill_duplicate,
        test_publish_skill_new_version,
        test_convert_protected_slug_clawhub_prefix,
        test_convert_protected_slug_clawhub_suffix,
        test_convert_protected_slug_normal,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试完成: 通过 {passed} 个, 失败 {failed} 个")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)