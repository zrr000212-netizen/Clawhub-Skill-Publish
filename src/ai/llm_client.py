import os
import time
import requests
from dataclasses import dataclass
from typing import Optional
from utils.logger import get_logger


class LLMError(Exception):
    def __init__(self, error_type: str, message: str, retryable: bool = False):
        self.error_type = error_type
        self.message = message
        self.retryable = retryable
        super().__init__(f"[{error_type}] {message}")


@dataclass
class AIConfig:
    enabled: bool = False
    provider: str = "openai"
    api_key: str = ""
    model: str = "gpt-4"
    api_base: str = ""
    max_tokens: int = 1024
    temperature: float = 0.3
    timeout: int = 20
    max_retries: int = 3


class LLMClient:
    def __init__(self, ai_config: AIConfig):
        self.config = ai_config
        self.logger = get_logger(__name__)
        self.api_key = self._resolve_api_key(ai_config.api_key)
        self.api_base = self._resolve_api_base(ai_config)
        self._circuit_breaker_failures = 0
        self._circuit_breaker_threshold = 3
        self._circuit_breaker_reset_timeout = 300
        self._circuit_breaker_last_failure_time = 0

    def _resolve_api_key(self, api_key: str) -> str:
        if api_key.startswith("${env:") and api_key.endswith("}"):
            env_var = api_key[6:-1]
            value = os.environ.get(env_var, "")
            if not value:
                self.logger.warning(f"环境变量 {env_var} 未设置")
            return value
        return api_key

    def _resolve_api_base(self, ai_config: AIConfig) -> str:
        if ai_config.api_base:
            return ai_config.api_base.rstrip('/')
        provider_bases = {
            "openai": "https://api.openai.com/v1",
            "azure_openai": "",
            "deepseek": "https://api.deepseek.com/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "ollama": "http://localhost:11434/v1",
            "ark": "https://ark.cn-beijing.volces.com/api/v3",
            "volcengine": "https://ark.cn-beijing.volces.com/api/v3",
        }
        return provider_bases.get(ai_config.provider, "https://api.openai.com/v1")

    def _is_circuit_breaker_open(self) -> bool:
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            elapsed = time.time() - self._circuit_breaker_last_failure_time
            if elapsed < self._circuit_breaker_reset_timeout:
                return True
            else:
                self.logger.info("熔断器恢复，尝试重新调用 LLM 服务")
                self._circuit_breaker_failures = 0
        return False

    def _record_failure(self, error_type: str):
        if error_type == "permanent":
            self._circuit_breaker_failures += 1
            self._circuit_breaker_last_failure_time = time.time()
            if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
                self.logger.warning(f"熔断器触发，{self._circuit_breaker_reset_timeout} 秒内不再调用 LLM 服务")

    def _record_success(self):
        if self._circuit_breaker_failures > 0:
            self._circuit_breaker_failures = 0
            self.logger.info("LLM 调用成功，熔断器失败计数已重置")

    def chat_completion(self, messages: list[dict], tools: list[dict] = None) -> dict:
        if self._is_circuit_breaker_open():
            raise LLMError("permanent", "熔断器已开启，跳过 LLM 调用", retryable=False)

        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }
        if tools:
            payload["tools"] = tools

        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                self.logger.debug(f"调用 LLM API (尝试 {attempt + 1}/{self.config.max_retries + 1})")
                response = requests.post(
                    url, headers=headers, json=payload,
                    timeout=self.config.timeout
                )
                result = self._handle_response(response)
                self._record_success()
                return result
            except LLMError as e:
                last_error = e
                if not e.retryable:
                    self._record_failure(e.error_type)
                    raise
                if attempt < self.config.max_retries:
                    delay = 1.0 * (2 ** attempt)
                    self.logger.warning(f"LLM 调用失败 (临时性错误)，{delay:.1f}s 后重试: {e.message}")
                    time.sleep(delay)
                else:
                    self._record_failure(e.error_type)
            except requests.exceptions.Timeout:
                last_error = LLMError("transient", "LLM API 调用超时", retryable=True)
                if attempt < self.config.max_retries:
                    delay = 1.0 * (2 ** attempt)
                    self.logger.warning(f"LLM 调用超时，{delay:.1f}s 后重试")
                    time.sleep(delay)
                else:
                    self._record_failure("transient")
            except requests.exceptions.RequestException as e:
                last_error = LLMError("transient", f"请求失败: {str(e)}", retryable=True)
                if attempt < self.config.max_retries:
                    delay = 1.0 * (2 ** attempt)
                    time.sleep(delay)
                else:
                    self._record_failure("transient")

        raise last_error or LLMError("transient", "LLM 调用失败", retryable=False)

    def _handle_response(self, response: requests.Response) -> dict:
        if response.status_code == 200:
            return response.json()

        error_detail = ""
        try:
            error_body = response.json()
            error_detail = error_body.get("error", {}).get("message", "")
        except Exception:
            pass

        if response.status_code == 401:
            msg = f"API Key 无效或已过期: {error_detail}" if error_detail else "API Key 无效或已过期"
            raise LLMError("permanent", msg, retryable=False)
        elif response.status_code == 403:
            msg = f"权限不足: {error_detail}" if error_detail else "权限不足"
            raise LLMError("permanent", msg, retryable=False)
        elif response.status_code == 404:
            msg = f"模型不存在或 API 端点错误: {error_detail}" if error_detail else "模型不存在或 API 端点错误"
            raise LLMError("permanent", msg, retryable=False)
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "5"))
            self.logger.warning(f"LLM 限流，等待 {retry_after} 秒")
            time.sleep(retry_after)
            raise LLMError("transient", "限流", retryable=True)
        elif response.status_code >= 500:
            raise LLMError("transient", f"服务器错误: {response.status_code}", retryable=True)
        else:
            raise LLMError("permanent", f"未知错误: {response.status_code}", retryable=False)