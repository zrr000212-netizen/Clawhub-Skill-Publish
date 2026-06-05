import sys
from config.config_manager import ConfigManager
from client.github_client import GitHubClient, GitHubError
from client.clawhub_client import ClawHubClient, CLIError
from publisher.skill_publisher import SkillPublisher
from publisher.batch_publisher import BatchPublisher
from publisher.monitor_publisher import MonitorPublisher
from utils.logger import get_logger


def main():
    """主程序入口"""
    try:
        config_path = "config.yaml"
        config_manager = ConfigManager(config_path)
        app_config = config_manager.get_app_config()

        logger = get_logger(__name__, app_config.log_level)
        logger.info("ClawHub Skill Publisher 启动")

        # 检查 CLI 是否已安装
        clawhub_client = ClawHubClient()
        if not clawhub_client.check_cli_installed():
            logger.error("ClawHub CLI 未安装，请运行: npm install -g clawhub@0.18.0")
            sys.exit(1)

        # 检查登录状态
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

        if app_config.mode == "batch":
            batch_publisher = BatchPublisher(github_client, clawhub_client, app_config.clawhub)
            skills = batch_publisher.scan_skills()
            result = batch_publisher.publish_skills(skills)
            logger.info(f"批量发布结果: 成功 {result.success} 个，失败 {result.failed} 个")
        elif app_config.mode == "monitor":
            monitor_publisher = MonitorPublisher(github_client, clawhub_client, app_config.clawhub)
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
