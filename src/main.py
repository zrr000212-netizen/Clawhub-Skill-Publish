import sys
import os
from config.config_manager import ConfigManager
from client.github_client import GitHubClient, GitHubError
from client.clawhub_client import ClawHubClient, CLIError
from publisher.skill_publisher import SkillPublisher
from publisher.batch_publisher import BatchPublisher
from publisher.monitor_publisher import MonitorPublisher
from ai.llm_client import LLMClient
from ai.ai_changelog_generator import AIChangelogGenerator
from utils.published_versions_store import PublishedVersionsStore
from utils.logger import get_logger


def main():
    """主程序入口"""
    logger = get_logger(__name__)
    try:
        config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
        config_manager = ConfigManager(config_path)
        app_config = config_manager.get_app_config()
        logger.info("ClawHub Skill Publisher 启动")

        repo_dir = os.path.dirname(os.path.abspath(config_path))
        store = PublishedVersionsStore(
            store_file=os.path.join(repo_dir, ".published_versions.json"),
            repo_dir=repo_dir
        )
        store.git_pull()

        clawhub_client = ClawHubClient()
        if not clawhub_client.check_cli_installed():
            logger.error("ClawHub CLI 未安装，请运行: npm install -g clawhub@0.18.0")
            sys.exit(1)

        if not clawhub_client.check_login_status():
            logger.error("未登录，请先运行: clawhub login")
            sys.exit(1)

        github_client = GitHubClient(
            token=app_config.github.token,
            owner=app_config.github.owner,
            repo=app_config.github.repo,
            branch=app_config.github.branch
        )

        skill_publisher = SkillPublisher(clawhub_client, github_client)

        ai_changelog_generator = None
        if app_config.mode == "monitor" and app_config.ai and app_config.ai.enabled:
            try:
                llm_client = LLMClient(app_config.ai)
                ai_changelog_generator = AIChangelogGenerator(
                    llm_client=llm_client,
                    github_client=github_client,
                    ai_config=app_config.ai,
                    agent_config=app_config.agent,
                )
                logger.info(f"AI Changelog 生成器已初始化 (模型: {app_config.ai.model})")
            except Exception as e:
                logger.warning(f"AI Changelog 生成器初始化失败，将使用传统方式: {str(e)}")

        if app_config.mode == "batch":
            batch_publisher = BatchPublisher(github_client, clawhub_client, app_config.clawhub, store=store)
            skills = batch_publisher.scan_skills()
            result = batch_publisher.publish_skills(skills)
            logger.info(f"批量发布结果: 成功 {result.success} 个，失败 {result.failed} 个")
        elif app_config.mode == "monitor":
            monitor_publisher = MonitorPublisher(
                github_client, clawhub_client, app_config.clawhub,
                ai_changelog_generator=ai_changelog_generator,
                store=store,
            )
            monitor_publisher.monitor_commits()
        else:
            logger.error(f"不支持的发布模式: {app_config.mode}")
            sys.exit(1)

    except GitHubError as e:
        logger.error(f"GitHub API 错误: {e.message}")
        sys.exit(1)
    except CLIError as e:
        logger.error(f"ClawHub CLI 错误: {e.message}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序运行失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
