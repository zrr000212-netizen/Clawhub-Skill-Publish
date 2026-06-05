# -*- coding: utf-8 -*-
import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import Mock, patch, MagicMock
from publisher.monitor_publisher import MonitorPublisher
from publisher.skill_publisher import SkillPublisher
from client.github_client import GitHubClient
from client.clawhub_client import ClawHubClient


def test_version_handling():
    """测试版本号处理逻辑"""
    print("\n=== 测试版本号处理逻辑 ===")

    mock_github_client = Mock(spec=GitHubClient)
    mock_clawhub_client = Mock(spec=ClawHubClient)

    monitor_publisher = MonitorPublisher(mock_github_client, mock_clawhub_client)

    test_cases = [
        ("update skill: test-skill v0.0.1", "0.0.1"),
        ("update skill: test-skill v1.0.0", "1.0.0"),
        ("update skill: test-skill v2.3.4", "2.3.4"),
    ]

    for commit_message, expected_version in test_cases:
        with patch.object(monitor_publisher, 'find_skill_path', return_value="test-skill"):
            result = monitor_publisher.extract_skill_info(commit_message)
            print(f"输入: {commit_message}")
            print(f"提取的版本号: {result['version']}")
            assert result['version'] == expected_version, f"Expected '{expected_version}', got '{result['version']}'"
            print("✓ 版本号正确")

    print("✓ 测试通过")


def test_no_duplicate_publish():
    """测试不会重复发布同一版本"""
    print("\n=== 测试不会重复发布 ===")

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

            commit_message = "update skill: test-skill v0.0.1"

            with patch.object(monitor_publisher, 'find_skill_path', return_value="test-skill"):
                skill_info = monitor_publisher.extract_skill_info(commit_message)

            print(f"第一次发布 {skill_info['skill_name']} {skill_info['version']}")
            monitor_publisher.publish_skill(skill_info['skill_name'], skill_info['version'], skill_info['skill_path'])
            print(f"发布调用次数: {mock_skill_publisher.publish.call_count}")
            assert mock_skill_publisher.publish.call_count == 1, "应该调用一次 publish"

            print(f"第二次尝试发布 {skill_info['skill_name']} {skill_info['version']}")
            monitor_publisher.publish_skill(skill_info['skill_name'], skill_info['version'], skill_info['skill_path'])
            print(f"发布调用次数: {mock_skill_publisher.publish.call_count}")
            assert mock_skill_publisher.publish.call_count == 1, "不应该再次调用 publish"

            print("✓ 测试通过：重复发布被正确阻止")


def test_different_versions_can_publish():
    """测试不同版本可以正常发布"""
    print("\n=== 测试不同版本可以发布 ===")

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

            versions = ["0.0.1", "0.0.2", "0.0.3"]

            for version in versions:
                commit_message = f"update skill: test-skill v{version}"
                with patch.object(monitor_publisher, 'find_skill_path', return_value="test-skill"):
                    skill_info = monitor_publisher.extract_skill_info(commit_message)

                print(f"发布版本 {version}")
                monitor_publisher.publish_skill(skill_info['skill_name'], skill_info['version'], skill_info['skill_path'])

            print(f"总发布调用次数: {mock_skill_publisher.publish.call_count}")
            assert mock_skill_publisher.publish.call_count == 3, f"应该调用 3 次 publish，实际调用 {mock_skill_publisher.publish.call_count} 次"

            print("✓ 测试通过：不同版本都成功发布")


def test_commit_message_patterns():
    """测试不同的 commit message 格式"""
    print("\n=== 测试 commit message 格式 ===")

    mock_github_client = Mock(spec=GitHubClient)
    mock_clawhub_client = Mock(spec=ClawHubClient)

    monitor_publisher = MonitorPublisher(mock_github_client, mock_clawhub_client)

    test_cases = [
        ("update skill: test-skill v0.0.1", "test-skill", "0.0.1"),
        ("update skill: skills/test-skill v0.0.1", "test-skill", "0.0.1"),
        ("update skill: category/subcategory/test-skill v1.0.0", "test-skill", "1.0.0"),
    ]

    for commit_message, expected_name, expected_version in test_cases:
        with patch.object(monitor_publisher, 'find_skill_path', return_value=expected_name):
            result = monitor_publisher.extract_skill_info(commit_message)
            print(f"输入: {commit_message}")
            print(f"提取的技能名: {result['skill_name']}, 版本: {result['version']}")
            assert result['skill_name'] == expected_name
            assert result['version'] == expected_version
            print("✓ 格式正确")

    print("✓ 测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("开始运行版本处理和发布逻辑测试")
    print("=" * 60)

    tests = [
        test_version_handling,
        test_no_duplicate_publish,
        test_different_versions_can_publish,
        test_commit_message_patterns,
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
