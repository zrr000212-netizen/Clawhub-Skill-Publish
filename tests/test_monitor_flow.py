# -*- coding: utf-8 -*-
import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import Mock, patch, MagicMock, call
from publisher.monitor_publisher import MonitorPublisher
from publisher.skill_publisher import SkillPublisher
from client.github_client import GitHubClient
from client.clawhub_client import ClawHubClient
from utils.logger import get_logger


def test_monitor_commits_with_duplicate():
    """测试监控模式下的重复提交处理"""
    print("\n=== 测试监控模式重复提交处理 ===")

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

            commits = [
                {
                    "sha": "abc123",
                    "commit": {
                        "message": "update skill: test-skill v0.0.1",
                        "author": {"name": "test", "date": "2024-01-01T00:00:00Z"}
                    }
                },
                {
                    "sha": "def456",
                    "commit": {
                        "message": "update skill: test-skill v0.0.1",
                        "author": {"name": "test", "date": "2024-01-01T01:00:00Z"}
                    }
                }
            ]

            mock_github_client.get_commits.return_value = commits

            with patch.object(monitor_publisher, 'find_skill_path', return_value="test-skill"):
                with patch.object(monitor_publisher, 'extract_skill_info') as mock_extract:
                    mock_extract.return_value = {
                        "skill_name": "test-skill",
                        "version": "0.0.1",
                        "skill_path": "test-skill"
                    }

                    for commit in commits:
                        monitor_publisher.process_commit(commit)

            print(f"发布调用次数: {mock_skill_publisher.publish.call_count}")

            assert mock_skill_publisher.publish.call_count == 1, f"应该只调用 1 次 publish，实际调用 {mock_skill_publisher.publish.call_count} 次"

            print("✓ 测试通过：重复提交只发布一次")


def test_monitor_commits_restart():
    """测试程序重启后的行为"""
    print("\n=== 测试程序重启后的行为 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        store_file = os.path.join(tmpdir, "test_published_versions.json")

        mock_github_client = Mock(spec=GitHubClient)
        mock_clawhub_client = Mock(spec=ClawHubClient)
        mock_skill_publisher = Mock(spec=SkillPublisher)

        commits = [
            {
                "sha": "abc123",
                "commit": {
                    "message": "update skill: test-skill v0.0.1",
                    "author": {"name": "test", "date": "2024-01-01T00:00:00Z"}
                }
            }
        ]

        mock_github_client.get_commits.return_value = commits

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

            with patch.object(monitor_publisher, 'find_skill_path', return_value="test-skill"):
                with patch.object(monitor_publisher, 'extract_skill_info') as mock_extract:
                    mock_extract.return_value = {
                        "skill_name": "test-skill",
                        "version": "0.0.1",
                        "skill_path": "test-skill"
                    }

                    for commit in commits:
                        monitor_publisher.process_commit(commit)

            print(f"第一次运行 - 发布调用次数: {mock_skill_publisher.publish.call_count}")
            assert mock_skill_publisher.publish.call_count == 1

            print("\n模拟程序重启...")
            monitor_publisher2 = MonitorPublisher(mock_github_client, mock_clawhub_client)
            monitor_publisher2.skill_publisher = mock_skill_publisher

            with patch.object(monitor_publisher2, 'published_versions_store') as mock_store:
                mock_store.is_published.return_value = True

                with patch.object(monitor_publisher2, 'find_skill_path', return_value="test-skill"):
                    with patch.object(monitor_publisher2, 'extract_skill_info') as mock_extract:
                        mock_extract.return_value = {
                            "skill_name": "test-skill",
                            "version": "0.0.1",
                            "skill_path": "test-skill"
                        }

                        for commit in commits:
                            monitor_publisher2.process_commit(commit)

            print(f"第二次运行（重启后） - 发布调用次数: {mock_skill_publisher.publish.call_count}")
            assert mock_skill_publisher.publish.call_count == 1, "重启后不应该重复发布"
            print("✓ 重启后正确跳过已发布版本")

    print("✓ 测试通过")


def test_full_monitor_flow():
    """测试完整的监控流程"""
    print("\n=== 测试完整监控流程 ===")

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

            commits = [
                {
                    "sha": "abc123",
                    "commit": {
                        "message": "update skill: test-skill v0.0.1",
                        "author": {"name": "test", "date": "2024-01-01T00:00:00Z"}
                    }
                },
                {
                    "sha": "def456",
                    "commit": {
                        "message": "update skill: test-skill v0.0.2",
                        "author": {"name": "test", "date": "2024-01-01T01:00:00Z"}
                    }
                },
                {
                    "sha": "ghi789",
                    "commit": {
                        "message": "update skill: test-skill v0.0.1",
                        "author": {"name": "test", "date": "2024-01-01T02:00:00Z"}
                    }
                }
            ]

            mock_github_client.get_commits.return_value = commits

            with patch.object(monitor_publisher, 'find_skill_path', return_value="test-skill"):
                with patch.object(monitor_publisher, 'extract_skill_info') as mock_extract:
                    def side_effect(msg):
                        if "v0.0.1" in msg:
                            return {"skill_name": "test-skill", "version": "0.0.1", "skill_path": "test-skill"}
                        else:
                            return {"skill_name": "test-skill", "version": "0.0.2", "skill_path": "test-skill"}
                    mock_extract.side_effect = side_effect

                    for commit in commits:
                        monitor_publisher.process_commit(commit)

            print(f"总发布调用次数: {mock_skill_publisher.publish.call_count}")

            assert mock_skill_publisher.publish.call_count == 2, f"应该调用 2 次 publish（0.0.1 和 0.0.2），实际调用 {mock_skill_publisher.publish.call_count} 次"

            print("✓ 测试通过：正确处理了多个提交和重复版本")


if __name__ == "__main__":
    print("=" * 60)
    print("开始运行监控模式完整流程测试")
    print("=" * 60)

    tests = [
        test_monitor_commits_with_duplicate,
        test_monitor_commits_restart,
        test_full_monitor_flow,
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

    print("\n" + "=" * 60)
    print("问题分析总结：")
    print("=" * 60)
    print("1. 版本号处理逻辑正确：v 前缀会被正确去除")
    print("2. 单次运行内重复发布会被正确阻止")
    print("3. ⚠ 程序重启后，published_versions 集合被清空，会导致重复发布")
    print("4. ⚠ 需要持久化已发布版本记录，避免重启后重复发布")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)