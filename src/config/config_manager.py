import os
import yaml
import json
from models.models import AppConfig, ClawHubConfig, GitHubConfig
from ai.llm_client import AIConfig
from ai.agent_runtime import AgentConfig
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

        github_fields = ["owner", "repo", "branch", "token"]
        for field in github_fields:
            if field not in config["github"]:
                raise ValueError(f"配置文件缺少必填字段: github.{field}")

        ai_config = config.get("ai", {})
        if ai_config.get("enabled", False):
            if not ai_config.get("api_key"):
                raise ValueError("启用 AI changelog 功能但未配置 ai.api_key")
            if not ai_config.get("model"):
                raise ValueError("启用 AI changelog 功能但未配置 ai.model")
            valid_providers = ["openai", "azure_openai", "deepseek", "zhipu", "ollama", "ark", "volcengine", "custom"]
            provider = ai_config.get("provider", "openai")
            if provider not in valid_providers:
                raise ValueError(f"不支持的 AI 服务提供商: {provider}，支持的值: {', '.join(valid_providers)}")

        agent_config = config.get("agent", {})
        max_iter = agent_config.get("max_iterations", 5)
        if not isinstance(max_iter, int) or max_iter < 1:
            raise ValueError(f"agent.max_iterations 必须为正整数，当前值: {max_iter}")

        return True

    def get_app_config(self) -> AppConfig:
        """获取应用配置"""
        config = self.load_config()
        self.validate_config(config)

        clawhub_config = ClawHubConfig(owner=config["clawhub"].get("owner"))
        github_config = GitHubConfig(**config["github"])

        ai_config = self._parse_ai_config(config.get("ai", {}))
        agent_config = self._parse_agent_config(config.get("agent", {}))

        return AppConfig(
            clawhub=clawhub_config,
            github=github_config,
            mode=config["mode"],
            log_level=config.get("log_level", "INFO"),
            ai=ai_config,
            agent=agent_config,
        )

    def _parse_ai_config(self, ai_dict: dict) -> AIConfig:
        """解析 AI 服务配置"""
        return AIConfig(
            enabled=ai_dict.get("enabled", False),
            provider=ai_dict.get("provider", "openai"),
            api_key=ai_dict.get("api_key", ""),
            model=ai_dict.get("model", "gpt-4"),
            api_base=ai_dict.get("api_base", ""),
            max_tokens=ai_dict.get("max_tokens", 1024),
            temperature=ai_dict.get("temperature", 0.3),
            timeout=ai_dict.get("timeout", 20),
            max_retries=ai_dict.get("max_retries", 3),
        )

    def _parse_agent_config(self, agent_dict: dict) -> AgentConfig:
        """解析 Agent 配置"""
        return AgentConfig(
            enabled=agent_dict.get("enabled", False),
            max_iterations=agent_dict.get("max_iterations", 5),
            prompt_template=agent_dict.get("prompt_template", ""),
            tools=agent_dict.get("tools", []),
        )
