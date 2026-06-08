from dataclasses import dataclass, field
from ai.llm_client import LLMClient, LLMError
from utils.logger import get_logger


@dataclass
class AgentConfig:
    enabled: bool = False
    max_iterations: int = 5
    prompt_template: str = ""
    tools: list[str] = field(default_factory=list)


STRATEGY_PROMPTS = {
    "docs": "本次变更仅涉及文档文件（.md, .txt, .rst 等），请重点分析文档变更的内容和目的。",
    "refactor": "本次变更涉及多个文件的重构，请重点分析重构的目的、影响范围和兼容性。",
    "feature": "本次变更包含新功能添加，请重点分析新增功能的描述和使用场景。",
    "bugfix": "本次变更看起来是 bug 修复，请重点分析修复的问题和修复方式。",
    "default": "请分析本次代码变更，生成准确的 changelog。",
}

DEFAULT_SYSTEM_PROMPT = """你是一个专业的代码变更分析助手。你的任务是分析 Git commit 的代码变更 diff，生成结构化的 changelog。

要求：
1. 输出格式必须为: `{变更类型}: {变更摘要}`
2. 变更类型必须是以下之一: feat, fix, refactor, docs, style, perf, test, chore
3. 变更摘要应简洁明了，不超过 200 字符，使用中文描述
4. 根据代码变更的实际内容选择最合适的变更类型
5. 不要输出任何额外解释，只输出 changelog 行

变更类型说明：
- feat: 新功能
- fix: 修复 bug
- refactor: 重构（不改变功能）
- docs: 文档变更
- style: 格式调整（不影响逻辑）
- perf: 性能优化
- test: 测试相关
- chore: 构建/工具/配置变更"""


class AgentRuntime:
    def __init__(self, llm_client: LLMClient, agent_config: AgentConfig = None, github_client=None):
        self.llm_client = llm_client
        self.config = agent_config or AgentConfig()
        self.github_client = github_client
        self.logger = get_logger(__name__)

    def run(self, diff: str, commit_message: str) -> str:
        strategy = self.select_strategy(diff)
        self.logger.info(f"Agent 选择分析策略: {strategy}")

        system_prompt = DEFAULT_SYSTEM_PROMPT
        if self.config.prompt_template:
            try:
                with open(self.config.prompt_template, 'r', encoding='utf-8') as f:
                    system_prompt = f.read()
            except Exception as e:
                self.logger.warning(f"加载自定义提示词模板失败: {e}")

        strategy_hint = STRATEGY_PROMPTS.get(strategy, STRATEGY_PROMPTS["default"])

        user_prompt = f"""{strategy_hint}

Commit Message: {commit_message}

代码变更 Diff:
```diff
{diff}
```

请分析以上代码变更，生成 changelog："""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        if self.config.enabled and self._has_tools():
            return self._run_with_tools(messages, diff)
        else:
            return self._run_direct(messages)

    def select_strategy(self, diff: str) -> str:
        lines = diff.split('\n')
        file_names = []
        for line in lines:
            if line.startswith('diff --git'):
                parts = line.split()
                if len(parts) >= 4:
                    file_names.append(parts[3])

        doc_extensions = {'.md', '.txt', '.rst', '.adoc', '.html'}
        all_docs = all(
            any(f.lower().endswith(ext) for ext in doc_extensions)
            for f in file_names if f
        )
        if all_docs and file_names:
            return "docs"

        unique_files = set(file_names)
        if len(unique_files) >= 5:
            has_refactor_keywords = any(
                kw in diff.lower()
                for kw in ['rename', 'move', 'restructure', 'reorganize', 'migrate']
            )
            if has_refactor_keywords:
                return "refactor"

        if any(kw in diff.lower() for kw in ['fix', 'bug', 'issue', 'patch', 'hotfix']):
            return "bugfix"

        if any(kw in diff.lower() for kw in ['add', 'new', 'create', 'implement', 'support']):
            return "feature"

        return "default"

    def _has_tools(self) -> bool:
        return len(self.config.tools) > 0

    def _run_direct(self, messages: list[dict]) -> str:
        try:
            response = self.llm_client.chat_completion(messages)
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip() if content else ""
        except LLMError as e:
            self.logger.error(f"LLM 调用失败: {e.message}")
            raise

    def _run_with_tools(self, messages: list[dict], diff: str) -> str:
        tool_definitions = self._get_tool_definitions()
        all_messages = list(messages)

        for iteration in range(self.config.max_iterations):
            self.logger.debug(f"Agent 迭代 {iteration + 1}/{self.config.max_iterations}")

            try:
                response = self.llm_client.chat_completion(all_messages, tools=tool_definitions)
            except LLMError as e:
                self.logger.error(f"Agent LLM 调用失败: {e.message}")
                raise

            choice = response.get("choices", [{}])[0]
            assistant_message = choice.get("message", {})
            all_messages.append(assistant_message)

            tool_calls = assistant_message.get("tool_calls")
            if not tool_calls:
                content = assistant_message.get("content", "")
                return content.strip() if content else ""

            for tool_call in tool_calls:
                tool_result = self._execute_tool(tool_call, diff)
                all_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", ""),
                    "content": tool_result,
                })

        self.logger.warning(f"Agent 达到最大迭代次数 {self.config.max_iterations}")
        last_content = all_messages[-1].get("content", "") if all_messages else ""
        return last_content.strip() if last_content else ""

    def _get_tool_definitions(self) -> list[dict]:
        all_tools = {
            "get_file_content": {
                "type": "function",
                "function": {
                    "name": "get_file_content",
                    "description": "获取指定文件的完整内容，用于深入分析关键变更文件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "文件路径（相对于仓库根目录）",
                            }
                        },
                        "required": ["file_path"],
                    },
                },
            },
            "count_changes": {
                "type": "function",
                "function": {
                    "name": "count_changes",
                    "description": "统计变更文件数量和变更类型分布，用于评估变更规模",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
        }

        if not self.config.tools:
            return list(all_tools.values())

        return [all_tools[name] for name in self.config.tools if name in all_tools]

    def _execute_tool(self, tool_call: dict, diff: str) -> str:
        function_name = tool_call.get("function", {}).get("name", "")
        arguments = tool_call.get("function", {}).get("arguments", "{}")
        self.logger.info(f"Agent 调用工具: {function_name} 参数: {arguments}")

        try:
            import json
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
        except Exception:
            args = {}

        if function_name == "get_file_content":
            return self._tool_get_file_content(args.get("file_path", ""))
        elif function_name == "count_changes":
            return self._tool_count_changes(diff)
        else:
            return f"未知工具: {function_name}"

    def _tool_get_file_content(self, file_path: str) -> str:
        if not file_path:
            return "错误: 未提供文件路径"
        if not self.github_client:
            return f"无法获取文件内容: GitHub 客户端未配置"
        try:
            content = self.github_client.get_file_content(file_path)
            return content[:2000] if len(content) > 2000 else content
        except Exception as e:
            return f"获取文件 {file_path} 失败: {str(e)}"

    def _tool_count_changes(self, diff: str) -> str:
        lines = diff.split('\n')
        files = set()
        additions = 0
        deletions = 0
        for line in lines:
            if line.startswith('diff --git'):
                parts = line.split()
                if len(parts) >= 4:
                    files.add(parts[3])
            elif line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1
        return f"变更文件: {len(files)} 个, 新增行: {additions}, 删除行: {deletions}"