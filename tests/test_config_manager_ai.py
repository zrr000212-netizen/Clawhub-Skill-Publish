import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.config_manager import ConfigManager
from ai.llm_client import AIConfig
from ai.agent_runtime import AgentConfig


def test_backward_compatibility():
    yaml_content = """
clawhub:
  owner: test
github:
  owner: test
  repo: test
  branch: main
  token: test
mode: monitor
"""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
    f.write(yaml_content)
    f.close()

    cm = ConfigManager(f.name)
    cfg = cm.get_app_config()

    assert cfg.ai.enabled == False
    assert cfg.agent.enabled == False
    assert cfg.mode == "monitor"

    os.unlink(f.name)
    print("Backward compatibility: OK - no AI config, system works as before")


def test_ai_config_parsing():
    yaml_content = """
clawhub:
  owner: test
github:
  owner: test
  repo: test
  branch: main
  token: test
mode: monitor
ai:
  enabled: true
  provider: deepseek
  api_key: test-key
  model: deepseek-chat
agent:
  enabled: true
  max_iterations: 3
"""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
    f.write(yaml_content)
    f.close()

    cm = ConfigManager(f.name)
    cfg = cm.get_app_config()

    assert cfg.ai.enabled == True
    assert cfg.ai.provider == "deepseek"
    assert cfg.ai.model == "deepseek-chat"
    assert cfg.agent.enabled == True
    assert cfg.agent.max_iterations == 3

    os.unlink(f.name)
    print("AI config parsing: OK")


def test_invalid_provider():
    yaml_content = """
clawhub:
  owner: test
github:
  owner: test
  repo: test
  branch: main
  token: test
mode: monitor
ai:
  enabled: true
  provider: invalid_provider
  api_key: test-key
  model: test
"""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
    f.write(yaml_content)
    f.close()

    cm = ConfigManager(f.name)
    try:
        cm.get_app_config()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "不支持的 AI 服务提供商" in str(e)

    os.unlink(f.name)
    print("Invalid provider validation: OK")


def test_missing_api_key():
    yaml_content = """
clawhub:
  owner: test
github:
  owner: test
  repo: test
  branch: main
  token: test
mode: monitor
ai:
  enabled: true
  model: test
"""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
    f.write(yaml_content)
    f.close()

    cm = ConfigManager(f.name)
    try:
        cm.get_app_config()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "api_key" in str(e)

    os.unlink(f.name)
    print("Missing API key validation: OK")


if __name__ == "__main__":
    test_backward_compatibility()
    test_ai_config_parsing()
    test_invalid_provider()
    test_missing_api_key()
    print("\nAll config tests passed!")