import os
import yaml
import json
from models.models import AppConfig, ClawHubConfig, GitHubConfig
from utils.logger import get_logger


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.logger = get_logger(__name__)

    def load_config(self) -> dict:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            if self.config_path.endswith(".yaml") or self.config_path.endswith(".yml"):
                return yaml.safe_load(f)
            elif self.config_path.endswith(".json"):
                return json.load(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {self.config_path}")

    def validate_config(self, config: dict) -> bool:
        """验证配置文件"""
        required_fields = ["clawhub", "github", "mode"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"配置文件缺少必填字段: {field}")

        # CLI 模式下不需要验证 clawhub 字段
        # clawhub_fields = ["api_key"]
        # for field in clawhub_fields:
        #     if field not in config["clawhub"]:
        #         raise ValueError(f"配置文件缺少必填字段: clawhub.{field}")

        github_fields = ["owner", "repo", "branch", "token"]
        for field in github_fields:
            if field not in config["github"]:
                raise ValueError(f"配置文件缺少必填字段: github.{field}")

        return True

    def get_app_config(self) -> AppConfig:
        """获取应用配置"""
        config = self.load_config()
        self.validate_config(config)

        clawhub_config = ClawHubConfig()
        github_config = GitHubConfig(**config["github"])

        return AppConfig(
            clawhub=clawhub_config,
            github=github_config,
            mode=config["mode"],
            log_level=config.get("log_level", "INFO")
        )
