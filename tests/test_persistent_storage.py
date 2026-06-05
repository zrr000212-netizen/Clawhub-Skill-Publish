import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import Mock, patch
from publisher.monitor_publisher import MonitorPublisher
from publisher.skill_publisher import SkillPublisher
from client.github_client import GitHubClient
from client.clawhub_client import ClawHubClient


def test_persistent_storage():
    """测试持久化存储功能"""
    print("\n=== 测试持久化存储功能 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        store_file = os.path.join(tmpdir, "test_published_versions.json")

        mock_github_client = Mock(spec=GitHubClient)
        mock_clawhub_client = Mock(spec=ClawHubClient)
        mock_skill_publisher = Mock(spec=SkillPublisher)

        from utils.published_versions_store import PublishedVersionsStore

        store = PublishedVersionsStore(store_file)

        assert not store.is_published("test-skill", "0.0.1"), "初始状态应该未发布"
        print("✓ 初始状态正确")

        store.mark_published("test-skill", "0.0.1")
        assert store.is_published("test-skill", "0.0.1"), "标记后应该已发布"
        print("✓ 标记发布成功")

        store.mark_published("test-skill", "0.0.2")
        store.mark_published("another-skill", "1.0.0")

        assert os.path.exists(store_file), "存储文件应该存在"
        print("✓ 存储文件已创建")

        with open(store_file, 'r') as f:
            data = json.load(f)
            assert set(data['versions']) == {"test-skill@0.0.1", "test-skill@0.0.2", "another-skill@1.0.0"}
        print("✓ 存储内容正确")

        store2 = PublishedVersionsStore(store_file)
        assert store2.is_published("test-skill", "0.0.1"), "重新加载后应该保持已发布状态"
        assert store2.is_published("test-skill", "0.0.2"), "重新加载后应该保持已发布状态"
        assert store2.is_published("another-skill", "1.0.0"), "重新加载后应该保持已发布状态"
        print("✓ 重新加载后状态保持正确")

    print("✓ 测试通过")


def test_monitor_with_persistent_storage():
    """测试监控模式使用持久化存储"""
    print("\n=== 测试监控模式使用持久化存储 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        store_file = os.path.join(tmpdir, "test_published_versions.json")

        mock_github_client = Mock(spec=GitHubClient)
        mock_clawhub_client = Mock(spec=ClawHubClient)
        mock_skill_publisher = Mock(spec=SkillPublisher)

        monitor_publisher = MonitorPublisher(mock_github_client, mock_clawhub_client)
        monitor_publisher.skill_publisher = mock_skill_publisher

        with patch('utils.published_versions_store.PublishedVersionsStore') as MockStore:
            MockStore.return_value.__class__ = type('Store', (), {
                'is_published': lambda self, name, ver: False,
                'mark_published': lambda self, name, ver: None
            })

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


if __name__ == "__main__":
    print("=" * 60)
    print("开始运行持久化存储测试")
    print("=" * 60)

    tests = [
        test_persistent_storage,
        test_monitor_with_persistent_storage,
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