# ClawHub Skill Publisher 编码任务列表

## 文档信息

| 项目 | 内容 |
|------|------|
| 功能名称 | ClawHub Skill Publisher - AI Changelog 生成 |
| 文档版本 | v1.0 |
| 创建日期 | 2026-06-07 |
| 关联需求 | REQ-016 ~ REQ-022 |
| 关联设计 | AI Changelog Generator 模块 |

---

## 1. Diff 预处理器单元测试

> 对应需求：REQ-016（获取 Commit 代码变更 Diff）、REQ-021（AI 生成 Changelog 质量保障）
> 对应设计：1.3.7 Diff Processor

- [ ] 编写 `tests/test_diff_processor.py`，测试 `DiffProcessor.process()` 完整流水线：原始 diff → 去除二进制 → 截断长文件 diff → 敏感信息脱敏 → 总大小截断
- [ ] 测试 `remove_binary_diffs()`：验证图片/压缩包/编译产物等二进制文件 diff 被正确移除，文本文件 diff 保留
- [ ] 测试 `truncate_long_diffs()`：验证单文件 diff 超过 `max_file_diff_lines` 时截断并添加截断标记，未超限时不截断
- [ ] 测试 `redact_sensitive_info()`：验证 `api_key=xxx`、`token: yyy`、`password="zzz"` 等敏感信息被替换为 `[REDACTED]`
- [ ] 测试 `truncate_by_size()`：验证 diff 超过 `max_diff_size` 字节时截断并添加截断标记，未超限时不截断
- [ ] 测试空 diff 输入和纯二进制 diff 输入的边界情况

**优先级**：P0 | **依赖**：无 | **验收标准**：所有测试通过，覆盖 DiffProcessor 全部公开方法和边界情况

---

## 2. LLM Client 单元测试

> 对应需求：REQ-019（AI 服务配置管理）、REQ-020（AI 服务错误处理与回退）
> 对应设计：1.3.5 LLM Client

- [ ] 编写 `tests/test_llm_client.py`，使用 `unittest.mock` 模拟 HTTP 请求
- [ ] 测试 `_resolve_api_key()`：验证明文 API Key 直接返回，`${env:VAR_NAME}` 格式从环境变量读取，环境变量未设置时返回空串并记录警告
- [ ] 测试 `_resolve_api_base()`：验证 `provider=openai` 推断为 `https://api.openai.com/v1`，`provider=azure_openai` 返回空串，用户配置 `api_base` 优先
- [ ] 测试 `chat_completion()` 正常调用：模拟 200 响应，验证返回 JSON 结果
- [ ] 测试错误分类：模拟 401/403/404 响应，验证抛出 `LLMError(error_type="permanent")`；模拟 429/500/Timeout 响应，验证抛出 `LLMError(error_type="transient")`
- [ ] 测试重试机制：模拟临时性错误连续出现，验证指数退避重试行为（延迟 = 1.0 * 2^attempt）
- [ ] 测试熔断器：模拟连续 3 次永久性错误，验证熔断器触发后抛出 "熔断器已开启" 错误；模拟熔断期结束后自动恢复

**优先级**：P0 | **依赖**：无 | **验收标准**：所有测试通过，覆盖 LLMClient 全部核心逻辑路径

---

## 3. Agent Runtime 单元测试

> 对应需求：REQ-018（Agent 能力增强）
> 对应设计：1.3.6 Agent Runtime

- [ ] 编写 `tests/test_agent_runtime.py`，使用 `unittest.mock` 模拟 LLMClient
- [ ] 测试 `select_strategy()`：验证全文档变更 → `docs`，≥5 文件且含重构关键词 → `refactor`，含 fix/bug 关键词 → `bugfix`，含 add/new 关键词 → `feature`，其余 → `default`
- [ ] 测试 `_run_direct()`：模拟 LLM 返回有效 changelog 文本，验证正确提取 content
- [ ] 测试 `_run_with_tools()`：模拟 Agent 多轮迭代，验证 tool_calls 处理和 tool 角色消息追加；模拟无 tool_calls 时提前返回 content
- [ ] 测试 Agent 最大迭代次数限制：模拟持续产生 tool_calls，验证达到 `max_iterations` 后停止并返回最后一条消息
- [ ] 测试自定义提示词模板：验证 `prompt_template` 指向有效文件时加载自定义 system prompt，指向无效文件时回退到默认 prompt 并记录警告
- [ ] 测试 Agent 未启用时走 `_run_direct()` 路径

**优先级**：P0 | **依赖**：无 | **验收标准**：所有测试通过，覆盖策略选择、直接调用、工具调用三种模式

---

## 4. AI Changelog Generator 单元测试

> 对应需求：REQ-017（AI 大模型分析代码变更生成 Changelog）、REQ-021（AI 生成 Changelog 质量保障）
> 对应设计：1.3.4 AI Changelog Generator

- [ ] 编写 `tests/test_ai_changelog_generator.py`，使用 `unittest.mock` 模拟 LLMClient 和 GitHubClient
- [ ] 测试 `generate_changelog()` 完整流程：模拟 diff 获取 → 预处理 → Agent 运行 → 校验，验证返回 `StructuredChangelog`
- [ ] 测试 diff 为空时回退：模拟 `get_commit_diff()` 返回空串，验证回退到 `fallback_changelog()`
- [ ] 测试 AI 生成空 changelog 时回退：模拟 Agent 返回空串，验证回退到 `fallback_changelog()`
- [ ] 测试 `validate_changelog()`：验证 Conventional Commits 格式正确解析、Markdown 代码块标记去除、自由文本解析、变更类型归一化、摘要截断（>200 字符）
- [ ] 测试 `_normalize_change_type()`：验证标准类型原样返回，别名类型映射正确（`feature→feat`、`bugfix→fix` 等），未知类型归为 `chore`
- [ ] 测试 `_redact_sensitive_in_changelog()`：验证 GitHub Token (`ghp_`)、OpenAI Key (`sk-`)、敏感赋值语句被替换为 `[REDACTED]`
- [ ] 测试 `fallback_changelog()`：验证 commit message 可用时提取描述并标记 `source="commit_message"`，不可用时使用默认模板并标记 `source="default_template"`
- [ ] 测试 `StructuredChangelog` 数据模型：验证 `__post_init__` 自动生成 `raw_text`，含 scope 和不含 scope 两种格式

**优先级**：P0 | **依赖**：任务 1、2、3 | **验收标准**：所有测试通过，覆盖完整生成流程、校验逻辑、回退策略

---

## 5. 配置管理 AI 配置验证测试

> 对应需求：REQ-019（AI 服务配置管理）
> 对应设计：1.3.1 配置管理模块

- [ ] 编写 `tests/test_config_manager_ai.py`，测试 AI 相关配置解析和验证
- [ ] 测试 `validate_config()`：验证 `ai.enabled=True` 但缺少 `api_key` 时抛出 ValueError，缺少 `model` 时抛出 ValueError
- [ ] 测试 `_parse_ai_config()`：验证完整 AI 配置正确解析为 `AIConfig` 实例，默认值正确（`provider=openai`、`max_tokens=1024` 等）
- [ ] 测试 `_parse_agent_config()`：验证完整 Agent 配置正确解析为 `AgentConfig` 实例，默认值正确（`enabled=False`、`max_iterations=5` 等）
- [ ] 测试 AI 配置未提供时：验证 `ai` 和 `agent` 字段使用默认值，不影响原有功能
- [ ] 测试环境变量 API Key 格式：验证 `${env:OPENAI_API_KEY}` 格式在配置解析阶段原样保留，运行时由 LLMClient 解析

**优先级**：P1 | **依赖**：无 | **验收标准**：所有测试通过，覆盖 AI 配置验证的全部边界情况

---

## 6. Agent 工具定义完善

> 对应需求：REQ-018（Agent 能力增强 - Agent 应能调用辅助工具获取额外上下文信息）
> 对应设计：1.3.6 Agent Runtime - `_get_tool_definitions()` 和 `_execute_tool()`

- [ ] 实现 `_get_tool_definitions()` 返回有意义的工具定义列表，至少包含：
  - `get_file_content`：获取指定文件的完整内容（用于 Agent 深入分析关键文件）
  - `count_changes`：统计变更文件数量和变更类型分布（用于 Agent 评估变更规模）
- [ ] 实现 `_execute_tool()` 根据工具名称分发执行，调用 GitHubClient 获取实际数据
- [ ] 在 `AgentConfig.tools` 中支持配置启用的工具子集，`_get_tool_definitions()` 仅返回已启用的工具
- [ ] 编写单元测试验证工具定义格式符合 OpenAI function calling 规范，工具执行返回有效结果

**优先级**：P1 | **依赖**：任务 3 | **验收标准**：Agent 启用时能通过工具获取额外上下文，工具定义符合 OpenAI 规范

---

## 7. LLM Provider 扩展支持

> 对应需求：REQ-019（支持配置不同的 LLM 服务提供商和模型）
> 对应设计：1.3.5 LLM Client - API Base 推断逻辑

- [ ] 在 `_resolve_api_base()` 中增加对 `provider=deepseek` 的支持，推断为 `https://api.deepseek.com/v1`
- [ ] 在 `_resolve_api_base()` 中增加对 `provider=zhipu` 的支持，推断为 `https://open.bigmodel.cn/api/paas/v4`
- [ ] 在 `_resolve_api_base()` 中增加对 `provider=ollama` 的支持，推断为 `http://localhost:11434/v1`
- [ ] 更新 `config-example.yaml` 中 `ai.provider` 的注释说明，列出所有支持的 provider
- [ ] 编写单元测试验证各 provider 的 API Base 推断逻辑

**优先级**：P2 | **依赖**：任务 2 | **验收标准**：支持 openai/azure_openai/deepseek/zhipu/ollama/custom 六种 provider，配置示例更新

---

## 8. AI 服务错误处理与回退完善

> 对应需求：REQ-020（AI 服务错误处理与回退）
> 对应设计：1.3.4 回退策略、1.3.5 熔断器

- [ ] 完善 `AIChangelogGenerator.generate_changelog()` 的错误日志：记录 diff 大小、模型名称、耗时、回退状态等完整信息（对应 REQ-020 "系统应记录所有 AI 服务错误的完整信息"）
- [ ] 在 `LLMClient` 中增加 `_record_success()` 方法，成功调用后重置熔断器失败计数，避免偶发永久性错误误触发熔断
- [ ] 在 `MonitorPublisher.generate_changelog()` 中增加 changelog 来源标识日志：明确记录 `source` 为 `ai_generated` / `commit_message` / `default_template`（对应 REQ-007 验收标准）
- [ ] 编写测试验证：LLM 调用成功后熔断器失败计数重置；AI 生成失败后正确回退到 commit message；commit message 不可用时回退到默认模板

**优先级**：P1 | **依赖**：任务 2、4 | **验收标准**：回退策略完整实现（AI → commit message → 默认模板），熔断器行为正确，日志信息完整

---

## 9. Changelog 质量校验增强

> 对应需求：REQ-021（AI 生成 Changelog 质量保障）
> 对应设计：1.3.4 validate_changelog 流程

- [ ] 在 `validate_changelog()` 中增加对多行 changelog 的处理：当 LLM 返回多行时，取第一行有效 changelog 行，忽略空行和注释行
- [ ] 在 `validate_changelog()` 中增加对 changelog 包含中英文混合变更类型的容错处理（如 "feat: 新增feature"）
- [ ] 在 `AIChangelogGenerator` 中增加生成耗时统计和结构化日志输出，格式为：`AI changelog 生成完成 | 耗时: {elapsed}s | 来源: {source} | 类型: {type} | 摘要: {summary} | diff大小: {diff_size}`
- [ ] 编写测试验证多行 changelog 解析、中英混合类型容错、耗时统计输出

**优先级**：P2 | **依赖**：任务 4 | **验收标准**：LLM 返回的各种非标准格式均能正确解析或回退，生成日志信息完整

---

## 10. 监控模式 + AI Changelog 集成测试

> 对应需求：REQ-005~007（监控发布模式）、REQ-016~017（AI Changelog 生成）
> 对应设计：1.2.2 AI Changelog 生成架构、1.2.3 回退策略架构

- [ ] 编写 `tests/test_integration_ai_changelog.py`，测试监控模式下 AI changelog 的完整集成
- [ ] 测试场景 1：AI 生成成功 → 发布载荷使用 AI changelog，日志记录 `source=ai_generated`
- [ ] 测试场景 2：AI 生成失败（LLMError） → 回退到 commit message 提取，日志记录 `source=commit_message`
- [ ] 测试场景 3：AI 生成失败且 commit message 无描述 → 回退到默认模板，日志记录 `source=default_template`
- [ ] 测试场景 4：AI 未启用 → 直接使用默认模板 `Release {version}`
- [ ] 测试场景 5：diff 为空（merge commit）→ 回退到 commit message
- [ ] 测试场景 6：熔断器触发后 → 后续 commit 使用 commit message 回退，熔断恢复后重新尝试 AI

**优先级**：P0 | **依赖**：任务 4、8 | **验收标准**：6 个集成场景全部通过，覆盖 AI changelog 的完整生命周期

---

## 11. 端到端测试：监控模式完整发布流程

> 对应需求：REQ-005~007、REQ-016~021
> 对应设计：1.2.1 核心发布流程架构

- [ ] 编写 `tests/test_e2e_monitor_publish.py`，模拟从 commit 检测到技能发布的完整流程
- [ ] 测试完整流程：GitHub API 返回 commit → 提取技能信息 → 获取 diff → AI 生成 changelog → 调用 ClawHub CLI 发布
- [ ] 验证发布命令中 `--changelog` 参数传递了 AI 生成的 changelog 文本
- [ ] 验证已发布版本去重：同一技能同一版本不重复发布
- [ ] 验证不同技能不同版本正常发布

**优先级**：P1 | **依赖**：任务 10 | **验收标准**：端到端流程测试通过，changelog 正确传递到发布命令

---

## 12. 配置验证与错误处理完善

> 对应需求：REQ-019（AI 服务配置管理）、REQ-002（配置文件验证）
> 对应设计：1.3.1 配置管理模块

- [ ] 在 `ConfigManager.validate_config()` 中增加对 `ai.provider` 的校验：当 `ai.enabled=True` 时，`provider` 必须为支持的值之一（openai/azure_openai/custom/deepseek/zhipu/ollama）
- [ ] 在 `ConfigManager.validate_config()` 中增加对 `ai.api_key` 环境变量格式的校验：`${env:VAR}` 格式时验证 VAR 非空
- [ ] 在 `ConfigManager.validate_config()` 中增加对 `agent.max_iterations` 的范围校验：必须为正整数
- [ ] 在 `main.py` 中增加 AI 初始化时的配置摘要日志：输出 provider、model、agent_enabled 等关键配置（脱敏后）
- [ ] 编写测试验证新增校验逻辑

**优先级**：P1 | **依赖**：任务 5、7 | **验收标准**：无效 AI 配置在启动时被拦截并给出明确错误提示，有效配置正常通过

---

## 13. requirements.txt 依赖清理

> 对应需求：无（技术债务清理）
> 对应设计：8.2 依赖包

- [ ] 移除 `requirements.txt` 中未实际使用的 `openai>=1.30.0` 依赖（当前实现直接使用 `requests` 调用 OpenAI 兼容 API）
- [ ] 移除 `requirements.txt` 中未实际使用的 `gitpython>=3.1.40` 依赖（当前实现通过 GitHub REST API 获取数据）
- [ ] 添加 `pytest>=7.0.0` 到开发依赖（或创建 `requirements-dev.txt`）
- [ ] 验证移除依赖后所有功能正常运行

**优先级**：P2 | **依赖**：无 | **验收标准**：`requirements.txt` 仅包含实际使用的依赖，功能不受影响

---

## 14. 文档更新

> 对应需求：REQ-014（日志记录）、REQ-019（AI 服务配置管理）
> 对应设计：9.1 完整配置示例

- [ ] 更新 `config-example.yaml`：添加 AI 和 Agent 配置的完整注释说明，列出所有支持的 provider 和配置项
- [ ] 更新 `README.md`（如存在）：添加 AI Changelog 功能的使用说明，包括配置方式、启用条件、回退策略说明
- [ ] 添加 AI 模块架构说明文档 `docs/ai_changelog_architecture.md`：包含流程图、配置说明、回退策略、熔断器机制

**优先级**：P2 | **依赖**：任务 7、12 | **验收标准**：配置示例完整可用，文档准确描述 AI Changelog 功能

---

## 15. 最终验证与回归测试

> 对应需求：全部需求 REQ-016~022
> 对应设计：10.1~10.3 测试设计

- [ ] 运行全部单元测试：`pytest tests/ -v`，确保所有测试通过
- [ ] 运行集成测试和端到端测试，确保 AI changelog 完整流程正常
- [ ] 验证无 AI 配置时系统保持原有行为（向后兼容）
- [ ] 验证 AI 配置无效时系统启动报错并给出明确提示
- [ ] 检查代码覆盖率：AI 模块核心逻辑覆盖率 ≥ 80%
- [ ] 检查所有日志输出不包含 API Key 完整内容（安全性验证）

**优先级**：P0 | **依赖**：任务 1~14 | **验收标准**：全部测试通过，向后兼容，安全性验证通过

---

## 任务依赖关系图

```
任务 1 (Diff Processor 测试) ──────┐
任务 2 (LLM Client 测试) ──────────┤
任务 3 (Agent Runtime 测试) ───────┤
任务 5 (Config AI 测试) ───────────┤
任务 13 (依赖清理) ────────────────┤
                                    ├─→ 任务 4 (AI Generator 测试) ──→ 任务 8 (错误处理完善) ──→ 任务 10 (集成测试)
任务 3 ──→ 任务 6 (Agent 工具完善)  ┤                                                          │
任务 2 ──→ 任务 7 (Provider 扩展)  ┤                                                          │
任务 5,7 ──→ 任务 12 (配置校验) ───┤                                                          │
任务 7,12 ──→ 任务 14 (文档更新) ──┤                                                          │
                                    └──────────────────────────────────────────────────────────┘
                                                                               │
                                                                    任务 10 ──→ 任务 11 (端到端测试)
                                                                               │
                                                         任务 1~14 ──→ 任务 15 (最终验证)
```

## 任务统计

| 统计项 | 数量 |
|--------|------|
| 主任务数 | 15 |
| 子任务数 | 62 |
| P0 优先级 | 5（任务 1、2、3、4、10、15） |
| P1 优先级 | 5（任务 5、6、8、11、12） |
| P2 优先级 | 4（任务 7、9、13、14） |
| 覆盖需求 | REQ-016 ~ REQ-022（全部 7 个需求） |
