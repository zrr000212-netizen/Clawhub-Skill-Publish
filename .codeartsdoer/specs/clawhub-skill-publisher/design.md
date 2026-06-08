# ClawHub Skill Publisher 技术设计文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 功能名称 | ClawHub Skill Publisher |
| 文档版本 | v2.1 |
| 创建日期 | 2026-06-03 |
| 更新日期 | 2026-06-07 |
| 文档状态 | 已评审 |

---

# 1. 实现模型

## 1.1 上下文视图

系统与外部实体的交互关系如下：

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ClawHub Skill Publisher                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐           │
│  │  配置管理    │   │  批量发布器  │   │  监控发布器  │           │
│  │ ConfigMgr    │   │ BatchPublshr │   │  MonitorPub  │           │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘           │
│         │                  │                   │                    │
│         └──────────────────┴───────────────────┘                    │
│                            │                                        │
│                    ┌───────┴───────┐                                │
│                    │  技能发布器   │                                │
│                    │ SkillPublisher │                                │
│                    └───────┬───────┘                                │
│                            │                                        │
│         ┌──────────────────┼──────────────────┐                     │
│         │                  │                  │                     │
│  ┌──────┴──────┐   ┌──────┴──────┐   ┌──────┴──────┐             │
│  │ClawHub CLI  │   │ GitHub API  │   │  AI Changelog │             │
│  │  Client     │   │   Client    │   │  Generator    │             │
│  └─────────────┘   └─────────────┘   └──────┬──────┘             │
│                                              │                    │
│                    ┌─────────────────────────┼──────────┐         │
│                    │                         │          │         │
│              ┌─────┴─────┐  ┌───────┴──────┐  ┌────┴─────┐      │
│              │LLM Client │  │Agent Runtime │  │   Diff    │      │
│              │           │  │              │  │ Processor │      │
│              └───────────┘  └──────────────┘  └───────────┘     │
│                                                                   │
└─────────────────────────────────────────────────────────────────────┘

外部依赖：
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  GitHub API  │  │  LLM Service │  │  ClawHub CLI │
  │ (REST API)   │  │(OpenAI 兼容) │  │  (npm 全局)  │
  └──────────────┘  └──────────────┘  └──────────────┘
```

### 外部系统交互说明

| 外部系统 | 交互方式 | 用途 |
|---------|---------|------|
| GitHub REST API | HTTPS GET 请求 | 获取提交记录、文件列表、commit diff |
| LLM Service | HTTPS POST 请求（OpenAI 兼容接口） | 调用大模型分析代码变更生成 changelog |
| ClawHub CLI | subprocess 子进程调用 | 技能发布、登录状态检查 |

---

## 1.2 服务/组件总体架构

### 1.2.1 核心发布流程架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        主程序 (main.py)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 加载配置 → ConfigManager.get_app_config()                   │
│  2. 初始化客户端 → ClawHubClient, GitHubClient                  │
│  3. 条件初始化 AI → LLMClient → AIChangelogGenerator           │
│  4. 按模式执行:                                                  │
│     ├── batch  → BatchPublisher.scan_skills() → publish_skills()│
│     └── monitor → MonitorPublisher.monitor_commits()            │
│                       │                                         │
│                       ├── process_commit()                      │
│                       │     ├── extract_skill_info()            │
│                       │     ├── generate_changelog()  ← AI 增强 │
│                       │     └── publish_skill()                │
│                       └── 循环监控                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2.2 AI Changelog 生成架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                  AI Changelog Generator 完整流程                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  输入: commit_sha, commit_message, version                            │
│       │                                                               │
│       ▼                                                               │
│  ┌─────────────────────────────────────────┐                          │
│  │ 1. get_commit_diff(commit_sha)          │                          │
│  │    → GitHub API: Accept: v3.diff       │                          │
│  │    → 获取原始 diff 文本                 │                          │
│  └──────────────────┬──────────────────────┘                          │
│                     │ diff 为空?                                       │
│            ┌────────┴────────┐                                        │
│            │ Yes             │ No                                     │
│            ▼                 ▼                                        │
│     fallback_changelog   ┌────────────────────────────────────┐      │
│                          │ 2. DiffProcessor.process(diff)    │      │
│                          │    2a. remove_binary_diffs()      │      │
│                          │    2b. truncate_long_diffs()      │      │
│                          │    2c. redact_sensitive_info()    │      │
│                          │    2d. truncate_by_size()         │      │
│                          └──────────────┬─────────────────┘         │
│                                         │                            │
│                                         ▼                            │
│                          ┌────────────────────────────────────┐      │
│                          │ 3. AgentRuntime.run(diff, msg)    │      │
│                          │    3a. select_strategy(diff)       │      │
│                          │    3b. 构建提示词 (system+user)   │      │
│                          │    3c. Agent 启用?                 │      │
│                          │        ├── Yes → _run_with_tools() │      │
│                          │        └── No  → _run_direct()    │      │
│                          └──────────────┬─────────────────┘         │
│                                         │                            │
│                                         ▼                            │
│                          ┌────────────────────────────────────┐      │
│                          │ 4. validate_changelog(text)        │      │
│                          │    4a. 去除 Markdown 代码块标记   │      │
│                          │    4b. 正则匹配 Conventional 格式  │      │
│                          │    4c. 自由文本解析 (_parse_freeform)│    │
│                          │    4d. 归一化变更类型              │      │
│                          │    4e. 截断摘要 (≤200字符)        │      │
│                          │    4f. changelog 脱敏              │      │
│                          └──────────────┬─────────────────┘         │
│                                         │                            │
│                                         ▼                            │
│                          输出: StructuredChangelog                   │
│                                                                       │
│  异常路径:                                                             │
│    LLMError / Exception → fallback_changelog(commit_message, version)│
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2.3 Changelog 回退策略架构

```
changelog 来源优先级：

  AI 生成成功 ──────────────────► source = "ai_generated"
       │
       │ 失败
       ▼
  commit message 可用 ──────────► source = "commit_message"
       │                              (去除 "update skill:" 前缀)
       │ 不可用
       ▼
  默认模板 ─────────────────────► source = "default_template"
                                    (summary = "Release {version}")
```

### 1.2.4 LLM Client 熔断器架构

```
┌───────────────────────────────────────────────────┐
│              LLM Client 熔断器状态机               │
├───────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────┐   永久性错误 ≥ 3次   ┌──────────┐  │
│  │  CLOSED  │ ──────────────────► │   OPEN   │  │
│  │ (正常)   │                      │ (熔断)   │  │
│  └──────────┘                      └────┬─────┘  │
│       ▲                                 │         │
│       │          300s 超时              │         │
│       └─────────────────────────────────┘         │
│            (自动恢复到 CLOSED)                      │
│                                                    │
│  参数:                                             │
│    - threshold: 3 (连续永久性错误触发熔断)          │
│    - reset_timeout: 300s (熔断恢复等待时间)        │
│                                                    │
└───────────────────────────────────────────────────┘
```

---

## 1.3 实现设计文档

### 1.3.1 配置管理模块 (ConfigManager)

**文件路径**: `src/config/config_manager.py`

**职责**:
- 加载配置文件（YAML/JSON）
- 验证配置文件的完整性和正确性（含 AI 服务配置验证）
- 解析 AI 服务配置和 Agent 配置
- 提供应用配置的统一访问接口

**关键实现细节**:

1. **配置加载**: 根据文件扩展名（`.yaml`/`.yml`/`.json`）选择对应解析器
2. **必填字段验证**: `clawhub`、`github`、`mode` 为顶层必填字段；`github` 下 `owner`、`repo`、`branch`、`token` 为必填
3. **AI 配置验证**: 当 `ai.enabled=True` 时，强制要求 `ai.api_key` 和 `ai.model` 非空
4. **环境变量解析**: API Key 支持 `${env:ENV_VAR_NAME}` 格式，运行时从环境变量读取

**接口定义**:

```python
class ConfigManager:
    def __init__(self, config_path: str)
    def load_config(self) -> dict
    def validate_config(self, config: dict) -> bool
    def get_app_config(self) -> AppConfig
    def _parse_ai_config(self, ai_dict: dict) -> AIConfig
    def _parse_agent_config(self, agent_dict: dict) -> AgentConfig
```

---

### 1.3.2 批量发布器 (BatchPublisher)

**文件路径**: `src/publisher/batch_publisher.py`

**职责**:
- 递归扫描 GitHub 仓库中的所有 `skill.md` 文件
- 从技能路径中提取技能名称
- 转换受保护的 slug（`clawhub-` → `clh-`，`-clawhub` → `-mai`）
- 批量调用技能发布器发布技能
- 显示发布进度条

**关键实现细节**:

1. **技能扫描**: 递归遍历仓库目录树，查找 `skill.md` 文件
2. **技能名称提取**: 取路径最后一段作为 skill_name
3. **版本号固定**: 批量模式下所有技能版本号固定为 `0.0.1`
4. **受保护 slug 转换**: 避免与 ClawHub 平台保留名称冲突

**接口定义**:

```python
class BatchPublisher:
    def __init__(self, github_client: GitHubClient, clawhub_client: ClawHubClient, clawhub_config=None)
    def scan_skills(self) -> list[SkillInfo]
    def extract_skill_name(self, skill_path: str) -> str
    def convert_protected_slug(self, slug: str) -> str
    def publish_skills(self, skills: list[SkillInfo]) -> PublishResult
    def display_progress(self, total: int, current: int)
```

---

### 1.3.3 监控发布器 (MonitorPublisher)

**文件路径**: `src/publisher/monitor_publisher.py`

**职责**:
- 定期轮询 GitHub 仓库提交记录
- 从 commit message 中提取技能名称和版本号
- 生成 changelog（AI 优先，回退到默认模板）
- 调用技能发布器发布技能
- 已发布版本去重（持久化存储）

**关键实现细节**:

1. **Commit Message 解析**: 使用正则 `update skill: (?:skills/)?(?:\w+/)*(\S+) (v\d+\.\d+\.\d+)` 提取技能名称和版本号
2. **版本号处理**: 去除版本号中的 `v` 前缀（ClawHub CLI 自动添加）
3. **技能路径查找**: 递归搜索仓库目录树，匹配技能名称并验证 `skill.md` 存在
4. **AI Changelog 集成**: 当 `ai_changelog_generator` 非空时，调用 AI 生成 changelog；否则使用默认模板 `Release {version}`
5. **已发布版本去重**: 通过 `PublishedVersionsStore` 持久化记录已发布版本，避免重复发布

**接口定义**:

```python
class MonitorPublisher:
    COMMIT_MESSAGE_PATTERN: re.Pattern  # 预编译正则

    def __init__(self, github_client, clawhub_client, clawhub_config=None, ai_changelog_generator=None)
    def monitor_commits(self, interval: int = 60)
    def process_commit(self, commit: dict)
    def extract_skill_info(self, commit_message: str) -> dict
    def convert_protected_slug(self, slug: str) -> str
    def find_skill_path(self, skill_name: str) -> str
    def generate_changelog(self, commit_sha: str, commit_message: str, version: str) -> str
    def publish_skill(self, skill_name: str, version: str, skill_path: str, changelog: str = "")
```

**Changelog 生成流程**:

```python
def generate_changelog(self, commit_sha, commit_message, version):
    if self.ai_changelog_generator:
        try:
            structured = self.ai_changelog_generator.generate_changelog(
                commit_sha, commit_message, version
            )
            # structured.source 标识来源: "ai_generated" / "commit_message" / "default_template"
            return structured.raw_text
        except Exception:
            pass  # 回退到默认模板
    return f"Release {version}"  # 默认模板
```

---

### 1.3.4 AI Changelog Generator

**文件路径**: `src/ai/ai_changelog_generator.py`

**职责**:
- 获取 commit 的代码变更 diff（通过 GitHub API）
- 预处理 diff 数据（委托 DiffProcessor）
- 调用 Agent Runtime 生成 changelog 文本
- 校验和修正 AI 生成的 changelog
- 提供 changelog 回退策略（commit message → 默认模板）
- 记录 AI 生成过程的完整信息（耗时、来源、类型、摘要）

**关键实现细节**:

1. **Diff 获取**: 通过 GitHub API 的 `application/vnd.github.v3.diff` Accept 头获取 commit 的 diff 格式文本
2. **Diff 为空处理**: merge commit 等场景 diff 可能为空，直接回退到 commit message
3. **Changelog 校验流程**:
   - 去除 LLM 可能输出的 Markdown 代码块标记（` ``` `）
   - 正则匹配 Conventional Commits 格式：`{type}({scope}): {summary}`
   - 自由文本解析：逐行尝试匹配，匹配失败则归为 `chore` 类型
   - 变更类型归一化：通过别名映射表将非标准类型映射到标准类型
   - 摘要截断：超过 200 字符时截断
   - Changelog 脱敏：过滤 API Key、GitHub Token、OpenAI Key 等敏感信息
4. **回退策略**:
   - commit message 可用时：去除 `update skill:` 前缀，提取描述部分
   - commit message 不可用时：使用 `Release {version}` 默认模板

**变更类型别名映射表**:

```python
CHANGE_TYPE_ALIASES = {
    "feature": "feat",      "bugfix": "fix",        "bug": "fix",
    "hotfix": "fix",        "patch": "fix",         "improvement": "improve",
    "enhancement": "feat",  "documentation": "docs", "performance": "perf",
    "refactoring": "refactor", "testing": "test",   "build": "chore",
    "ci": "chore",
}
```

**接口定义**:

```python
class AIChangelogGenerator:
    def __init__(self, llm_client: LLMClient, github_client: GitHubClient,
                 ai_config: AIConfig, agent_config: AgentConfig = None,
                 diff_config: DiffConfig = None)
    def generate_changelog(self, commit_sha: str, commit_message: str, version: str = "") -> StructuredChangelog
    def get_commit_diff(self, commit_sha: str) -> str
    def validate_changelog(self, changelog_text: str) -> StructuredChangelog
    def _parse_freeform_changelog(self, text: str) -> tuple[str, str, str]
    def _normalize_change_type(self, change_type: str) -> str
    def _redact_sensitive_in_changelog(self, text: str) -> str
    def fallback_changelog(self, commit_message: str, version: str = "") -> StructuredChangelog
```

---

### 1.3.5 LLM Client

**文件路径**: `src/ai/llm_client.py`

**职责**:
- 封装 OpenAI 兼容 API 调用（Chat Completion）
- 支持多种 LLM 服务提供商（OpenAI、Azure OpenAI、自定义端点）
- API Key 环境变量解析
- API Base URL 自动推断
- 指数退避重试机制
- 熔断器保护机制
- 区分临时性错误和永久性错误

**关键实现细节**:

1. **API Key 解析**: 支持 `${env:ENV_VAR_NAME}` 格式，运行时从 `os.environ` 读取
2. **API Base 推断**:
   - 用户配置 `api_base` 优先
   - `provider=openai` → `https://api.openai.com/v1`
   - `provider=azure_openai` → 空字符串（需用户自行配置）
   - 默认 → `https://api.openai.com/v1`
3. **重试机制**: 指数退避策略，延迟 = `1.0 * 2^attempt` 秒
4. **错误分类**:

| 状态码 | 错误类型 | 可重试 | 说明 |
|-------|---------|--------|------|
| 401 | permanent | No | API Key 无效或已过期 |
| 403 | permanent | No | 权限不足 |
| 404 | permanent | No | 模型不存在或 API 端点错误 |
| 429 | transient | Yes | 限流，等待 Retry-After 后重试 |
| ≥500 | transient | Yes | 服务器错误 |
| Timeout | transient | Yes | 请求超时 |
| RequestException | transient | Yes | 网络请求异常 |

5. **熔断器**:
   - 触发条件：连续永久性错误 ≥ 3 次
   - 熔断期：300 秒内不再调用 LLM 服务
   - 恢复机制：熔断期结束后自动重置失败计数，尝试恢复调用

**接口定义**:

```python
class LLMClient:
    def __init__(self, ai_config: AIConfig)
    def chat_completion(self, messages: list[dict], tools: list[dict] = None) -> dict
    def _resolve_api_key(self, api_key: str) -> str
    def _resolve_api_base(self, ai_config: AIConfig) -> str
    def _is_circuit_breaker_open(self) -> bool
    def _record_failure(self, error_type: str)
    def _handle_response(self, response: requests.Response) -> dict
```

**API 调用请求格式**:

```json
POST {api_base}/chat/completions
Headers:
  Authorization: Bearer {api_key}
  Content-Type: application/json
Body:
{
  "model": "{model}",
  "messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
  "max_tokens": 1024,
  "temperature": 0.3,
  "tools": [...]  // 可选，Agent 模式
}
```

---

### 1.3.6 Agent Runtime

**文件路径**: `src/ai/agent_runtime.py`

**职责**:
- 根据 diff 特征自主选择分析策略
- 构建系统提示词和用户提示词
- 支持自定义提示词模板（从文件加载）
- 支持直接 LLM 调用模式和 Agent 工具调用模式
- 控制最大迭代次数

**关键实现细节**:

1. **策略选择逻辑** (`select_strategy`):

| 策略 | 触发条件 | 提示词侧重 |
|------|---------|-----------|
| `docs` | 所有变更文件均为文档扩展名（.md, .txt, .rst, .adoc, .html） | 文档变更内容和目的 |
| `refactor` | 变更文件 ≥ 5 个且 diff 包含重构关键词（rename, move, restructure, reorganize, migrate） | 重构目的、影响范围、兼容性 |
| `bugfix` | diff 包含修复关键词（fix, bug, issue, patch, hotfix） | 修复的问题和修复方式 |
| `feature` | diff 包含新增关键词（add, new, create, implement, support） | 新增功能描述和使用场景 |
| `default` | 以上均不匹配 | 通用代码变更分析 |

2. **提示词构建**:
   - **System Prompt**: 默认使用 `DEFAULT_SYSTEM_PROMPT`，支持通过 `prompt_template` 配置项加载自定义模板文件
   - **User Prompt**: 策略提示 + Commit Message + Diff 代码块

3. **执行模式**:
   - **直接调用模式** (`_run_direct`): Agent 未启用或无工具定义时，单次 LLM 调用
   - **工具调用模式** (`_run_with_tools`): Agent 启用且有工具定义时，多轮迭代调用 LLM，处理 `tool_calls` 响应

4. **Agent 迭代循环**:
   - 每轮将 LLM 响应的 `assistant_message` 追加到消息列表
   - 若响应包含 `tool_calls`，执行工具并将结果追加为 `tool` 角色消息
   - 若响应无 `tool_calls`，提取 `content` 作为最终结果
   - 达到 `max_iterations` 时停止迭代，返回最后一条消息内容

**默认系统提示词**:

```
你是一个专业的代码变更分析助手。你的任务是分析 Git commit 的代码变更 diff，生成结构化的 changelog。

要求：
1. 输出格式必须为: `{变更类型}: {变更摘要}`
2. 变更类型必须是以下之一: feat, fix, refactor, docs, style, perf, test, chore
3. 变更摘要应简洁明了，不超过 200 字符，使用中文描述
4. 根据代码变更的实际内容选择最合适的变更类型
5. 不要输出任何额外解释，只输出 changelog 行
```

**接口定义**:

```python
class AgentRuntime:
    def __init__(self, llm_client: LLMClient, agent_config: AgentConfig = None)
    def run(self, diff: str, commit_message: str) -> str
    def select_strategy(self, diff: str) -> str
    def _has_tools(self) -> bool
    def _run_direct(self, messages: list[dict]) -> str
    def _run_with_tools(self, messages: list[dict], diff: str) -> str
    def _get_tool_definitions(self) -> list[dict]
    def _execute_tool(self, tool_call: dict, diff: str) -> str
```

---

### 1.3.7 Diff Processor

**文件路径**: `src/ai/diff_processor.py`

**职责**:
- 去除二进制文件 diff
- 截断过长文件 diff
- 过滤敏感信息（正则替换为 `[REDACTED]`）
- 按总大小截断 diff

**关键实现细节**:

1. **处理流水线**（按顺序执行）:

```
原始 diff
  │
  ▼
remove_binary_diffs()    → 去除二进制文件 diff
  │
  ▼
truncate_long_diffs()    → 截断单文件过长 diff
  │
  ▼
redact_sensitive_info()  → 敏感信息脱敏
  │
  ▼
truncate_by_size()       → 按总字节大小截断
  │
  ▼
处理后 diff
```

2. **二进制文件识别**: 基于文件扩展名黑名单，覆盖图片、压缩包、办公文档、字体、编译产物、音视频等类型
3. **单文件 diff 截断**: 超过 `max_file_diff_lines`（默认 500）行时截断，并添加截断标记
4. **敏感信息脱敏**: 使用正则匹配 `api_key`、`token`、`secret`、`password`、`credential` 等关键词后的值，替换为 `[REDACTED]`
5. **总大小截断**: 超过 `max_diff_size`（默认 512000 字节）时截断，并添加截断标记

**接口定义**:

```python
class DiffProcessor:
    def __init__(self, diff_config: DiffConfig = None)
    def process(self, diff: str) -> str
    def remove_binary_diffs(self, diff: str) -> str
    def truncate_long_diffs(self, diff: str) -> str
    def redact_sensitive_info(self, diff: str) -> str
    def truncate_by_size(self, diff: str) -> str
```

---

### 1.3.8 技能发布器 (SkillPublisher)

**文件路径**: `src/publisher/skill_publisher.py`

**职责**:
- 从 GitHub 仓库下载技能文件到本地临时目录
- 从 `skill.md` 提取 `displayName`
- 调用 ClawHub CLI 发布技能
- 清理临时目录

**关键实现细节**:

1. **文件下载**: 递归遍历 GitHub 仓库目录，下载文件内容到本地临时目录
2. **displayName 提取**: 解析 `skill.md` 文件，提取 `displayName:` 字段值
3. **ClawHub CLI 发布**: 通过 subprocess 调用 `clawhub publish` 命令
4. **changelog 参数**: 通过 `--changelog` 参数传递给 ClawHub CLI
5. **临时目录清理**: 在 `finally` 块中确保清理临时目录

**接口定义**:

```python
class SkillPublisher:
    def __init__(self, clawhub_client: ClawHubClient, github_client: GitHubClient, clawhub_config=None)
    def download_skill(self, skill_path: str) -> str
    def extract_display_name(self, skill_path: str) -> str
    def publish(self, skill_name: str, version: str, skill_path: str, changelog: str = "") -> PublishResponse
```

---

### 1.3.9 ClawHub CLI 客户端 (ClawHubClient)

**文件路径**: `src/client/clawhub_client.py`

**职责**:
- 检查 ClawHub CLI 是否已安装
- 检查登录状态
- 调用 ClawHub CLI 发布技能

**关键实现细节**:

1. **CLI 检查**: 执行 `clawhub -V` 检查版本号
2. **登录检查**: 执行 `clawhub whoami` 检查登录状态
3. **发布命令**: `clawhub publish {skill_path} --slug {slug} --name {display_name} --version {version} [--changelog {changelog}] [--owner {owner}]`
4. **版本号校验**: 禁止版本号包含 `v` 前缀（ClawHub CLI 自动添加）
5. **Windows 兼容**: 使用 `shell=True` 和编码修复处理 Windows 平台问题

**接口定义**:

```python
class ClawHubClient:
    def __init__(self)
    def check_cli_installed(self) -> bool
    def check_login_status(self) -> bool
    def publish_skill(self, skill_path: str, slug: str, display_name: str,
                      version: str, changelog: str = "", owner: str = "") -> PublishResponse
```

---

### 1.3.10 GitHub API 客户端 (GitHubClient)

**文件路径**: `src/client/github_client.py`

**职责**:
- 获取仓库提交记录
- 获取仓库文件列表
- 处理 GitHub API 错误和限流

**关键实现细节**:

1. **重试装饰器**: `get_commits` 和 `get_files` 方法使用 `@retry_with_backoff` 装饰器
2. **限流处理**: 429 状态码时等待 `Retry-After` 头指定的时间
3. **错误映射**: 401 → Token 无效、403 → 权限不足、404 → 仓库不存在

**接口定义**:

```python
class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, owner: str, repo: str, branch: str = "main")
    def get_commits(self, since: Optional[datetime] = None) -> list[dict]
    def get_files(self, path: str = "") -> list[dict]
    def handle_error(self, response: requests.Response)
```

---

### 1.3.11 已发布版本存储 (PublishedVersionsStore)

**文件路径**: `src/utils/published_versions_store.py`

**职责**:
- 持久化记录已发布的技能版本
- 避免重复发布同一技能的同一版本

**关键实现细节**:

1. **存储格式**: JSON 文件 `.published_versions.json`，包含 `versions` 列表
2. **版本标识**: `{skill_name}@{version}` 格式的唯一键
3. **启动加载**: 初始化时从文件加载已发布版本集合
4. **发布后持久化**: 每次标记发布后立即写入文件

**接口定义**:

```python
class PublishedVersionsStore:
    def __init__(self, store_file: str = ".published_versions.json")
    def is_published(self, skill_name: str, version: str) -> bool
    def mark_published(self, skill_name: str, version: str)
    def clear(self)
```

---

### 1.3.12 主程序 (main)

**文件路径**: `src/main.py`

**职责**:
- 加载配置并初始化所有组件
- 根据发布模式执行对应流程
- AI 模块条件初始化

**关键实现细节**:

1. **AI 初始化条件**: 仅在 `mode=monitor` 且 `ai.enabled=True` 时初始化 AI Changelog Generator
2. **AI 初始化失败容错**: 初始化失败时记录警告日志，降级为传统 changelog 方式
3. **ClawHub CLI 前置检查**: 启动时检查 CLI 安装和登录状态，不满足则退出

**初始化流程**:

```python
# 1. 加载配置
app_config = ConfigManager("config.yaml").get_app_config()

# 2. 初始化客户端
clawhub_client = ClawHubClient()
github_client = GitHubClient(token, owner, repo, branch)

# 3. 条件初始化 AI（仅 monitor 模式）
ai_changelog_generator = None
if mode == "monitor" and ai.enabled:
    llm_client = LLMClient(ai_config)
    ai_changelog_generator = AIChangelogGenerator(
        llm_client, github_client, ai_config, agent_config
    )

# 4. 按模式执行
if mode == "batch":
    BatchPublisher(github_client, clawhub_client, clawhub_config).publish_skills(skills)
elif mode == "monitor":
    MonitorPublisher(github_client, clawhub_client, clawhub_config,
                     ai_changelog_generator=ai_changelog_generator).monitor_commits()
```

---

# 2. 接口设计

## 2.1 总体设计

系统通过以下方式与外部交互：

| 接口类型 | 协议 | 用途 |
|---------|------|------|
| GitHub REST API | HTTPS GET | 获取提交记录、文件列表、commit diff |
| LLM Service API | HTTPS POST (OpenAI 兼容) | Chat Completion 调用 |
| ClawHub CLI | subprocess | 技能发布 |
| 配置文件 | YAML/JSON 文件 I/O | 配置加载 |
| 已发布版本存储 | JSON 文件 I/O | 发布去重 |

## 2.2 接口清单

### 2.2.1 GitHub API - 获取提交记录

| 属性 | 值 |
|------|-----|
| 接口地址 | `GET /repos/{owner}/{repo}/commits` |
| 认证方式 | `Authorization: Bearer {token}` |
| Accept | `application/vnd.github.v3+json` |
| 查询参数 | `sha` (分支), `since` (起始时间 ISO 8601) |
| 重试 | `@retry_with_backoff(max_retries=3, base_delay=1.0)` |

### 2.2.2 GitHub API - 获取文件列表

| 属性 | 值 |
|------|-----|
| 接口地址 | `GET /repos/{owner}/{repo}/contents/{path}` |
| 认证方式 | `Authorization: Bearer {token}` |
| Accept | `application/vnd.github.v3+json` |
| 查询参数 | `ref` (分支) |
| 重试 | `@retry_with_backoff(max_retries=3, base_delay=1.0)` |

### 2.2.3 GitHub API - 获取 Commit Diff

| 属性 | 值 |
|------|-----|
| 接口地址 | `GET /repos/{owner}/{repo}/commits/{commit_sha}` |
| 认证方式 | `Authorization: Bearer {token}` |
| Accept | `application/vnd.github.v3.diff` |
| 超时 | 30 秒 |
| 说明 | 返回 commit 的 unified diff 格式文本 |

### 2.2.4 LLM Service - Chat Completion

| 属性 | 值 |
|------|-----|
| 接口地址 | `POST {api_base}/chat/completions` |
| 认证方式 | `Authorization: Bearer {api_key}` |
| Content-Type | `application/json` |
| 请求体 | `{model, messages, max_tokens, temperature, tools?}` |
| 超时 | 可配置（默认 20 秒） |
| 重试 | 指数退避，最大重试次数可配置（默认 3 次） |

### 2.2.5 ClawHub CLI - 发布技能

| 属性 | 值 |
|------|-----|
| 命令 | `clawhub publish {skill_path} --slug {slug} --name {name} --version {version}` |
| 可选参数 | `--changelog {changelog}`, `--owner {owner}` |
| 执行方式 | subprocess (shell=True) |
| 编码 | UTF-8 (errors='replace') |

---

# 4. 数据模型

## 4.1 设计目标

- 使用 Python `dataclass` 定义强类型数据模型
- 配置模型支持默认值，确保可选特性向后兼容
- AI 相关配置独立定义，与核心业务配置解耦
- 结构化 Changelog 模型包含来源标识，支持溯源

## 4.2 模型实现

### 4.2.1 核心配置模型

```python
@dataclass
class ClawHubConfig:
    """ClawHub 配置"""
    owner: Optional[str] = None

@dataclass
class GitHubConfig:
    """GitHub 配置"""
    owner: str
    repo: str
    branch: str
    token: str

@dataclass
class AppConfig:
    """应用配置"""
    clawhub: ClawHubConfig
    github: GitHubConfig
    mode: str  # "batch" or "monitor"
    log_level: str = "INFO"
    ai: Any = None       # AIConfig 实例
    agent: Any = None    # AgentConfig 实例
```

### 4.2.2 AI 服务配置模型

```python
@dataclass
class AIConfig:
    """AI 服务配置（定义于 llm_client.py）"""
    enabled: bool = False
    provider: str = "openai"       # openai | azure_openai | custom
    api_key: str = ""              # 支持明文或 ${env:VAR} 格式
    model: str = "gpt-4"
    api_base: str = ""             # 自定义 API 端点
    max_tokens: int = 1024
    temperature: float = 0.3
    timeout: int = 20              # 秒
    max_retries: int = 3

@dataclass
class AgentConfig:
    """Agent 配置（定义于 agent_runtime.py）"""
    enabled: bool = False
    max_iterations: int = 5
    prompt_template: str = ""      # 自定义提示词模板文件路径
    tools: list[str] = field(default_factory=list)  # 工具名称列表

@dataclass
class DiffConfig:
    """Diff 处理配置（定义于 diff_processor.py）"""
    max_diff_size: int = 512000           # 最大 diff 总大小（字节）
    max_file_diff_lines: int = 500        # 单文件 diff 最大行数
    exclude_binary: bool = True           # 是否排除二进制文件
    sensitive_patterns: list[str] = field(default_factory=lambda: [
        r'(?:api[_-]?key|token|secret|password|credential|apikey)\s*[:=]\s*["\']?[\w\-]{8,}',
    ])
```

### 4.2.3 技能数据模型

```python
@dataclass
class SkillInfo:
    """技能信息"""
    skill_name: str
    skill_path: str
    version: str = "0.0.1"

@dataclass
class CommitInfo:
    """提交信息"""
    sha: str
    message: str
    author: str
    timestamp: datetime
```

### 4.2.4 发布数据模型

```python
@dataclass
class PublishPayload:
    """发布载荷"""
    slug: str
    displayName: str
    version: str
    changelog: str
    tags: list[str] = field(default_factory=list)
    forkOf: dict = field(default_factory=dict)
    files: list[dict] = field(default_factory=list)

@dataclass
class PublishResponse:
    """发布响应"""
    ok: bool
    skill_id: Optional[str] = None
    version_id: Optional[str] = None
    error: Optional[str] = None

@dataclass
class PublishResult:
    """批量发布结果"""
    total: int
    success: int
    failed: int
    failed_skills: list[dict] = field(default_factory=list)
```

### 4.2.5 Changelog 数据模型

```python
VALID_CHANGE_TYPES = ["feat", "fix", "refactor", "docs", "style", "perf", "test", "chore"]

@dataclass
class StructuredChangelog:
    """结构化 Changelog（定义于 ai_changelog_generator.py）"""
    change_type: str       # Conventional Commits 类型
    summary: str           # 变更摘要（≤200 字符）
    scope: str = ""        # 变更范围（可选）
    raw_text: str = ""     # 完整文本（自动生成）
    source: str = "ai_generated"  # 来源标识: ai_generated | commit_message | default_template

    def __post_init__(self):
        """自动生成 raw_text"""
        if not self.raw_text:
            if self.scope:
                self.raw_text = f"{self.change_type}({self.scope}): {self.summary}"
            else:
                self.raw_text = f"{self.change_type}: {self.summary}"
```

### 4.2.6 错误模型

```python
class LLMError(Exception):
    """LLM 服务错误"""
    def __init__(self, error_type: str, message: str, retryable: bool = False):
        self.error_type = error_type    # "transient" | "permanent"
        self.message = message
        self.retryable = retryable

class GitHubError(Exception):
    """GitHub API 错误"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message

class CLIError(Exception):
    """ClawHub CLI 错误"""
    def __init__(self, message: str):
        self.message = message

class PublishError(Exception):
    """发布错误"""
    def __init__(self, skill_name: str, version: str, reason: str):
        self.skill_name = skill_name
        self.version = version
        self.reason = reason
```

---

# 5. 错误处理

## 5.1 错误码定义

### 5.1.1 GitHub API 错误

| 状态码 | 错误信息 | 处理方式 |
|-------|---------|---------|
| 401 | GitHub Token 无效或已过期 | 抛出 GitHubError，终止 |
| 403 | GitHub 权限不足 | 抛出 GitHubError，终止 |
| 404 | GitHub 仓库不存在 | 抛出 GitHubError，终止 |
| 429 | 限流 | 等待 Retry-After 后重试 |

### 5.1.2 LLM Service 错误

| 状态码 | 错误类型 | 可重试 | 处理方式 |
|-------|---------|--------|---------|
| 401 | permanent | No | 记录失败，触发熔断检查，抛出 |
| 403 | permanent | No | 记录失败，触发熔断检查，抛出 |
| 404 | permanent | No | 记录失败，触发熔断检查，抛出 |
| 429 | transient | Yes | 等待 Retry-After，指数退避重试 |
| ≥500 | transient | Yes | 指数退避重试 |
| Timeout | transient | Yes | 指数退避重试 |

### 5.1.3 ClawHub CLI 错误

| 场景 | 处理方式 |
|------|---------|
| CLI 未安装 | 记录错误，退出程序 |
| 未登录 | 记录错误，退出程序 |
| 版本号包含 v 前缀 | 抛出 CLIError |
| 发布返回非零 | 抛出 CLIError |
| 发布超时 | 抛出 CLIError |

## 5.2 重试机制

### 5.2.1 通用指数退避重试

```python
@retry_with_backoff(max_retries=3, base_delay=1.0)
# 延迟 = base_delay * 2^attempt + random(0, 1) 秒
# 特殊: "version already exists" 错误不重试
```

### 5.2.2 LLM 专用重试

```python
# 延迟 = 1.0 * 2^attempt 秒（无随机抖动）
# 仅对 retryable=True 的错误重试
# 永久性错误直接抛出
```

## 5.3 熔断器机制

| 参数 | 值 | 说明 |
|------|-----|------|
| threshold | 3 | 连续永久性错误次数阈值 |
| reset_timeout | 300s | 熔断恢复等待时间 |
| 触发条件 | 连续永久性错误 ≥ threshold | |
| 恢复条件 | 距最后一次失败超过 reset_timeout | 自动重置失败计数 |

---

# 6. 日志设计

## 6.1 日志级别

| 级别 | 用途 |
|------|------|
| DEBUG | LLM 调用详情、diff 处理细节、目录搜索过程 |
| INFO | 系统启动、技能发布、AI changelog 生成结果、策略选择 |
| WARNING | AI 初始化失败降级、diff 截断、LLM 重试、熔断触发 |
| ERROR | API 调用失败、发布失败、AI 生成异常 |

## 6.2 日志格式

```
[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s
```

## 6.3 日志输出

- 控制台输出：StreamHandler
- 文件输出：`clawhub_publisher.log`（UTF-8 编码）

## 6.4 AI 模块关键日志

| 场景 | 日志内容 |
|------|---------|
| AI 初始化 | `AI Changelog 生成器已初始化 (模型: {model})` |
| AI 初始化失败 | `AI Changelog 生成器初始化失败，将使用传统方式: {error}` |
| Diff 预处理 | `diff 预处理完成，原始大小: {orig}, 处理后大小: {processed}` |
| 策略选择 | `Agent 选择分析策略: {strategy}` |
| LLM 调用 | `调用 LLM API (尝试 {n}/{max})` |
| LLM 重试 | `LLM 调用失败 (临时性错误)，{delay}s 后重试: {msg}` |
| 熔断触发 | `熔断器触发，{timeout} 秒内不再调用 LLM 服务` |
| 熔断恢复 | `熔断器恢复，尝试重新调用 LLM 服务` |
| AI 生成完成 | `AI changelog 生成完成 \| 耗时: {elapsed}s \| 来源: {source} \| 类型: {type} \| 摘要: {summary}` |
| AI 生成失败 | `AI changelog 生成失败 ({error_type}): {msg} \| 耗时: {elapsed}s` |
| Changelog 来源 | `changelog 来源: {source} \| {raw_text}` |

---

# 7. 安全设计

## 7.1 API Key 保护

- API Key 不在日志中完整显示
- API Key 不在错误信息中完整显示
- API Key 支持环境变量引用格式 `${env:VAR}`，避免配置文件明文存储

## 7.2 敏感信息脱敏

### 7.2.1 Diff 预处理脱敏

```python
# 匹配模式：api_key/token/secret/password/credential 赋值语句
pattern = r'(?:api[_-]?key|token|secret|password|credential|apikey)\s*[:=]\s*["\']?[\w\-]{8,}'
# 替换为 [REDACTED]
```

### 7.2.2 Changelog 脱敏

```python
# 额外匹配 GitHub Token 和 OpenAI Key 格式
patterns = [
    r'(?:api[_-]?key|token|secret|password|credential)\s*[:=]\s*["\']?[\w\-]{8,}',
    r'ghp_[\w]{36}',     # GitHub Personal Access Token
    r'gho_[\w]{36}',     # GitHub OAuth Token
    r'sk-[\w]{48}',      # OpenAI API Key
]
# 替换为 [REDACTED]
```

---

# 8. 部署设计

## 8.1 目录结构

```
clawhub-skill-publisher/
├── src/
│   ├── __init__.py
│   ├── main.py                         # 主程序入口
│   ├── config/
│   │   ├── __init__.py
│   │   └── config_manager.py           # 配置管理
│   ├── publisher/
│   │   ├── __init__.py
│   │   ├── skill_publisher.py          # 技能发布器
│   │   ├── batch_publisher.py          # 批量发布器
│   │   └── monitor_publisher.py        # 监控发布器（含 AI 集成）
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── ai_changelog_generator.py   # AI Changelog 生成器
│   │   ├── llm_client.py              # LLM 客户端（含 AIConfig、LLMError）
│   │   ├── agent_runtime.py           # Agent 运行时（含 AgentConfig）
│   │   └── diff_processor.py          # Diff 预处理器（含 DiffConfig）
│   ├── client/
│   │   ├── __init__.py
│   │   ├── clawhub_client.py          # ClawHub CLI 客户端
│   │   ├── github_client.py           # GitHub API 客户端
│   │   └── git_client.py             # Git 客户端
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py                  # 核心数据模型
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                  # 日志工具
│       ├── retry.py                   # 重试装饰器
│       └── published_versions_store.py # 已发布版本存储
├── config.yaml                         # 配置文件
├── requirements.txt                    # 依赖包
├── README.md
└── .gitignore
```

## 8.2 依赖包

```
requests>=2.31.0
pyyaml>=6.0.0
```

> **说明**: 实际实现未使用 `openai` SDK 和 `gitpython`，而是直接通过 `requests` 库调用 OpenAI 兼容 API 和 GitHub REST API。

## 8.3 外部依赖

| 依赖 | 用途 | 安装方式 |
|------|------|---------|
| ClawHub CLI | 技能发布 | `npm install -g clawhub@0.18.0` |
| LLM Service | AI changelog 生成 | 外部 API 服务（OpenAI 兼容） |

---

# 9. 配置文件设计

## 9.1 完整配置示例 (YAML)

```yaml
clawhub:
  owner: "your-org"

github:
  owner: "your-username"
  repo: "your-repo-name"
  branch: "main"
  token: "ghp_your_github_token_here"

mode: "monitor"
log_level: "INFO"

ai:
  enabled: true
  provider: "openai"
  api_key: "${env:OPENAI_API_KEY}"
  model: "gpt-4"
  api_base: ""
  max_tokens: 1024
  temperature: 0.3
  timeout: 20
  max_retries: 3

agent:
  enabled: false
  max_iterations: 5
  prompt_template: ""
  tools: []
```

## 9.2 配置项说明

### 9.2.1 AI 配置项

| 配置项 | 类型 | 默认值 | 必填 | 说明 |
|-------|------|--------|------|------|
| ai.enabled | bool | false | 否 | 是否启用 AI changelog 生成 |
| ai.provider | string | "openai" | 否 | LLM 服务提供商（openai/azure_openai/custom） |
| ai.api_key | string | "" | 是* | API Key，支持 `${env:VAR}` 格式 |
| ai.model | string | "gpt-4" | 是* | 模型名称 |
| ai.api_base | string | "" | 否 | 自定义 API 端点 |
| ai.max_tokens | int | 1024 | 否 | 最大生成 token 数 |
| ai.temperature | float | 0.3 | 否 | 生成温度 |
| ai.timeout | int | 20 | 否 | API 调用超时（秒） |
| ai.max_retries | int | 3 | 否 | 最大重试次数 |

> *当 `ai.enabled=True` 时必填

### 9.2.2 Agent 配置项

| 配置项 | 类型 | 默认值 | 必填 | 说明 |
|-------|------|--------|------|------|
| agent.enabled | bool | false | 否 | 是否启用 Agent 工具调用模式 |
| agent.max_iterations | int | 5 | 否 | Agent 最大迭代次数 |
| agent.prompt_template | string | "" | 否 | 自定义提示词模板文件路径 |
| agent.tools | list | [] | 否 | 工具名称列表 |

---

# 10. 测试设计

## 10.1 单元测试

| 测试模块 | 测试内容 |
|---------|---------|
| ConfigManager | 配置加载、验证、AI 配置解析 |
| DiffProcessor | 二进制去除、截断、脱敏、大小限制 |
| LLMClient | API 调用、重试、熔断器、错误处理 |
| AgentRuntime | 策略选择、直接调用、工具调用模式 |
| AIChangelogGenerator | 完整流程、校验、回退 |
| StructuredChangelog | 格式化、类型归一化 |

## 10.2 集成测试

| 测试场景 | 测试内容 |
|---------|---------|
| 监控发布 + AI | 完整监控流程集成 AI changelog |
| AI 回退 | LLM 失败后回退到 commit message |
| 熔断恢复 | 熔断触发后自动恢复 |

## 10.3 端到端测试

| 测试场景 | 测试内容 |
|---------|---------|
| 完整发布流程 | 从 commit 检测到技能发布的完整流程 |
