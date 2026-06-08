# ClawHub Skill Publisher 需求规格说明书

## 文档信息

| 项目　　 | 内容　　　　　　　　　　|
| ----------| -------------------------|
| 功能名称 | ClawHub Skill Publisher |
| 文档版本 | v2.0　　　　　　　　　　|
| 创建日期 | 2026-06-03　　　　　　　|
| 文档状态 | 待评审　　　　　　　　　|

---

## 1. 引言

### 1.1 背景

ClawHub 是一个技能分发平台，支持开发者发布和管理技能。当前，开发者需要手动将技能打包并上传到 ClawHub，流程繁琐且容易出错。为了提高开发效率，需要开发一个自动化工具，能够从 GitHub 仓库自动发布技能到 ClawHub。

### 1.2 目的

本文档旨在明确 ClawHub Skill Publisher 的功能需求，为后续的设计和开发提供依据。

### 1.3 范围

本系统支持两种发布模式：
- **批量发布模式**：一次性将 GitHub 仓库中的所有技能发布到 ClawHub
- **监控发布模式**：监控 GitHub 仓库的提交记录，自动检测新提交并发布对应的技能，支持 AI 大模型分析代码变更自动生成 changelog

### 1.4 术语定义

| 术语 | 定义 |
|------|------|
| Skill | ClawHub 平台上的技能单元，包含技能描述、代码和配置文件 |
| Skill Name | 技能的唯一标识符，从 skill.md 文件中读取 |
| Version | 技能的版本号，遵循语义化版本规范（如 v0.0.1） |
| Commit Message | Git 提交消息，包含技能名称和版本号信息 |
| ClawHub API | ClawHub 平台提供的 RESTful API，用于技能的发布和管理 |
| Code Diff | 一个 commit 中所有文件变更的差异数据，包含新增、修改、删除文件的具体变更内容 |
| AI Changelog | 由 AI 大模型通过分析代码变更 diff 自动生成的结构化变更日志 |
| LLM Service | 提供大语言模型推理能力的外部 API 服务（如 OpenAI、Azure OpenAI 等） |
| Agent Capability | 基于 LLM 的自主决策和工具调用能力，允许 AI 在分析代码变更时自主选择分析策略 |
| Changelog Fallback | 当 AI 生成 changelog 失败时的兜底方案，优先级：AI 生成 → commit message → 默认模板 |
| Change Type | 代码变更的语义分类，遵循 Conventional Commits 规范（feat/fix/refactor/docs/style/perf/test/chore） |

---

## 2. 总体需求

### 2.1 功能概述

系统提供以下核心功能：
1. 配置管理：支持通过配置文件输入 ClawHub 账号信息、GitHub 仓库信息和 AI 服务配置
2. 批量发布：支持将 GitHub 仓库中的所有技能一次性发布到 ClawHub
3. 监控发布：支持监控 GitHub 仓库的提交记录，自动发布新提交的技能
4. AI Changelog 生成：支持通过 AI 大模型分析代码变更 diff 自动生成结构化 changelog
5. 错误处理：支持发布失败时的错误提示和重试机制

### 2.2 用户角色

| 角色 | 描述 |
|------|------|
| 开发者 | 使用本工具发布技能到 ClawHub 的用户 |

---

## 3. 功能需求

### 3.1 配置管理

#### REQ-001: 配置文件支持

**描述**：系统应支持通过配置文件输入 ClawHub 账号信息和 GitHub 仓库信息。

**验收标准**：
- WHEN 用户提供配置文件 THEN 系统应能够解析配置文件中的 ClawHub API Key
- WHEN 用户提供配置文件 THEN 系统应能够解析配置文件中的 GitHub 仓库信息（包括仓库所有者、仓库名称、分支名称）
- WHEN 配置文件格式为 YAML THEN 系统应能够正确解析 YAML 格式的配置文件
- WHEN 配置文件格式为 JSON THEN 系统应能够正确解析 JSON 格式的配置文件
- WHEN 配置文件缺少必填字段 THEN 系统应提示用户缺少的必填字段
- WHEN 配置文件中的 API Key 格式不正确 THEN 系统应提示用户 API Key 格式错误

#### REQ-002: 配置文件验证

**描述**：系统应在启动时验证配置文件的完整性和正确性。

**验收标准**：
- WHEN 配置文件不存在 THEN 系统应提示用户配置文件不存在
- WHEN 配置文件中的 ClawHub API Key 为空 THEN 系统应提示用户 API Key 不能为空
- WHEN 配置文件中的 GitHub 仓库信息不完整 THEN 系统应提示用户仓库信息不完整
- WHEN 配置文件验证通过 THEN 系统应继续执行后续操作

---

### 3.2 批量发布模式

#### REQ-003: 批量发布技能

**描述**：系统应支持将 GitHub 仓库中的所有技能一次性发布到 ClawHub。

**验收标准**：
- WHEN 用户选择批量发布模式 THEN 系统应扫描 GitHub 仓库中的所有 skill.md 文件
- WHEN 系统扫描到 skill.md 文件 THEN 系统应从 skill.md 文件中提取技能名称
- WHEN 系统提取到技能名称 THEN 系统应将技能的版本号设置为 0.0.1
- WHEN 系统完成技能信息提取 THEN 系统应依次将所有技能发布到 ClawHub
- WHEN 技能发布成功 THEN 系统应提示用户技能发布成功
- WHEN 技能发布失败 THEN 系统应提示用户技能发布失败的原因

#### REQ-004: 批量发布进度显示

**描述**：系统应显示批量发布的进度信息。

**验收标准**：
- WHEN 系统开始批量发布 THEN 系统应显示总技能数量
- WHEN 系统发布一个技能 THEN 系统应更新已发布的技能数量
- WHEN 系统完成批量发布 THEN 系统应显示发布结果统计（成功数量、失败数量）

---

### 3.3 监控发布模式

#### REQ-005: 监控 GitHub 提交记录

**描述**：系统应支持监控 GitHub 仓库的提交记录，检测新提交。

**验收标准**：
- WHEN 用户选择监控发布模式 THEN 系统应定期查询 GitHub 仓库的提交记录
- WHEN 系统检测到新提交 THEN 系统应读取新提交的 commit message 并获取该提交的代码变更 diff
- WHEN 系统未检测到新提交 THEN 系统应继续监控

#### REQ-006: 提取技能信息

**描述**：系统应从 commit message 中提取技能名称和版本号，changelog 通过 AI 分析代码变更 diff 自动生成。

**验收标准**：
- WHEN commit message 格式为 `update skill: solution/sac/huawei-cloud-sac-new-api v0.0.1` THEN 系统应提取技能名称为 `huawei-cloud-sac-new-api`
- WHEN commit message 格式为 `update skill: solution/sac/huawei-cloud-sac-new-api v0.0.1` THEN 系统应提取版本号为 `v0.0.1`
- WHEN commit message 格式不符合要求 THEN 系统应提示用户 commit message 格式错误
- WHEN commit message 中缺少版本号 THEN 系统应提示用户 commit message 中缺少版本号
- WHEN AI 功能启用且获取到代码变更 diff THEN 系统应通过 AI 分析 diff 自动生成 changelog
- WHEN AI 功能未启用 THEN 系统应从 commit message 或默认模板生成 changelog

#### REQ-007: 监控模式发布技能

**描述**：系统应将检测到的技能发布到 ClawHub，changelog 优先使用 AI 生成的结果。

**验收标准**：
- WHEN 系统提取到技能名称和版本号 THEN 系统应将该技能发布到 ClawHub
- WHEN AI 功能启用且 changelog 生成成功 THEN 发布载荷的 changelog 字段应使用 AI 生成的 changelog
- WHEN AI changelog 生成失败且 commit message 可用 THEN 发布时应使用 commit message 提取的 changelog
- WHEN AI changelog 和 commit message 均不可用 THEN 发布时应使用默认模板 changelog
- WHEN 技能发布成功 THEN 系统应提示用户技能发布成功
- WHEN 技能发布失败 THEN 系统应提示用户技能发布失败的原因
- 系统应在发布日志中记录 changelog 的来源标识（AI 生成 / commit message / 默认模板）

---

### 3.5 AI Changelog 生成

#### REQ-016: 获取 Commit 代码变更 Diff

**描述**：系统应在监控模式检测到新 commit 时，获取该 commit 的代码变更 diff 数据。

**验收标准**：
- WHEN 监控模式检测到新 commit THEN 系统应调用 GitHub API 获取该 commit 的代码变更 diff
- WHEN diff 数据超过配置的最大大小 THEN 系统应截断 diff 并记录警告日志
- WHEN GitHub API 返回 diff 获取错误 THEN 系统应记录错误并回退到 commit message 提取模式
- IF commit 的 diff 数据为空（如 merge commit）THEN 系统应使用 commit message 作为 changelog 来源

#### REQ-017: AI 大模型分析代码变更生成 Changelog

**描述**：系统应将 commit 的代码变更 diff 发送给 LLM 服务，由 LLM 分析并生成结构化 changelog。

**验收标准**：
- WHEN 系统获取到 commit diff 数据 THEN 系统应将 diff 和 commit message 发送给 LLM 服务生成结构化 changelog
- AI 生成的 changelog 格式必须为 `{变更类型}: {变更摘要}`
- 变更类型必须为 Conventional Commits 规范定义的类型之一（feat/fix/refactor/docs/style/perf/test/chore）
- WHEN changelog 摘要长度超过 200 字符 THEN 系统应截断至 200 字符
- 系统应在发送给 LLM 前对 diff 进行预处理（去除二进制文件 diff、截断过长文件 diff、过滤敏感信息）
- WHEN commit message 可用 THEN 系统应将 commit message 作为辅助上下文一同发送给 LLM

#### REQ-018: Agent 能力增强

**描述**：系统应支持 Agent 自主决策和工具调用能力，实现更智能的 changelog 生成。

**验收标准**：
- WHEN Agent 功能已启用 THEN Agent 应根据 diff 特征自主选择分析策略
- WHEN Agent 功能已启用 THEN Agent 应能调用辅助工具获取额外上下文信息
- 系统应支持外部配置 Agent 的提示词模板
- WHEN Agent 迭代次数达到最大值 THEN 系统应停止迭代并使用当前结果
- WHEN Agent 功能未启用 THEN 系统应使用直接 LLM 调用模式

#### REQ-019: AI 服务配置管理

**描述**：系统应支持 AI 服务的配置管理，包括 LLM 服务配置和 Agent 配置。

**验收标准**：
- WHEN 启用 AI changelog 功能但未配置 API Key THEN 系统启动时应报错并提示缺少配置
- WHEN AI 服务配置未提供 THEN 系统应保持原有行为（从 commit message 提取 changelog）
- 系统应支持通过环境变量引用 API Key，禁止明文存储
- 系统应支持配置不同的 LLM 服务提供商和模型（openai、azure_openai、custom）
- WHEN AI 服务配置无效 THEN 系统启动时应报错并提示配置错误

#### REQ-020: AI 服务错误处理与回退

**描述**：系统应处理 AI 服务调用过程中的错误，并提供回退策略。

**验收标准**：
- WHEN AI changelog 生成失败 THEN 系统应按优先级执行回退策略：commit message → 默认模板
- 系统应区分临时性错误（可重试）和永久性错误（禁止重试）
- WHILE 遇到临时性错误 THEN 系统应采用指数退避策略重试
- WHEN 连续出现永久性错误达到阈值 THEN 系统应触发熔断机制
- WHEN 熔断期结束 THEN 系统应尝试恢复 AI 服务调用
- 系统应记录所有 AI 服务错误的完整信息

#### REQ-021: AI 生成 Changelog 质量保障

**描述**：系统应对 AI 生成的 changelog 进行质量校验和保障。

**验收标准**：
- WHEN AI 生成的 changelog 为空 THEN 系统应执行回退策略
- WHEN changelog 格式不符合规范 THEN 系统应尝试修正或执行回退策略
- WHEN 变更类型不在 Conventional Commits 规范中 THEN 系统应修正为最接近的合法类型
- 系统应记录 AI 生成 changelog 的完整过程信息（diff 大小、模型、耗时、结果、回退状态）
- IF changelog 包含敏感信息 THEN 系统应对敏感信息脱敏处理

---

### 3.4 错误处理

#### REQ-008: API 调用错误处理

**描述**：系统应处理 ClawHub API 调用过程中的错误。

**验收标准**：
- WHEN ClawHub API 返回 401 错误 THEN 系统应提示用户 API Key 无效或已过期
- WHEN ClawHub API 返回 403 错误 THEN 系统应提示用户权限不足
- WHEN ClawHub API 返回 404 错误 THEN 系统应提示用户技能不存在
- WHEN ClawHub API 返回 413 错误 THEN 系统应提示用户文件过大
- WHEN ClawHub API 返回 415 错误 THEN 系统应提示用户文件格式不支持
- WHEN ClawHub API 返回 429 错误 THEN 系统应等待 Retry-After 指定的时间后重试
- WHEN ClawHub API 返回 500 错误 THEN 系统应提示用户服务器错误，稍后重试

#### REQ-009: 网络错误处理

**描述**：系统应处理网络连接过程中的错误。

**验收标准**：
- WHEN 网络连接超时 THEN 系统应提示用户网络连接超时，请检查网络连接
- WHEN 网络连接失败 THEN 系统应提示用户网络连接失败，请检查网络连接
- WHEN 网络连接恢复 THEN 系统应继续执行后续操作

#### REQ-010: GitHub API 错误处理

**描述**：系统应处理 GitHub API 调用过程中的错误。

**验收标准**：
- WHEN GitHub API 返回 401 错误 THEN 系统应提示用户 GitHub Token 无效或已过期
- WHEN GitHub API 返回 403 错误 THEN 系统应提示用户 GitHub 权限不足
- WHEN GitHub API 返回 404 错误 THEN 系统应提示用户 GitHub 仓库不存在
- WHEN GitHub API 返回 429 错误 THEN 系统应等待 Retry-After 指定的时间后重试

---

## 4. 非功能需求

### 4.1 性能需求

#### REQ-011: 批量发布性能

**描述**：系统应在合理的时间内完成批量发布。

**验收标准**：
- WHEN 批量发布 10 个技能 THEN 系统应在 5 分钟内完成发布

#### REQ-012: 监控模式响应时间

**描述**：系统应在合理的时间内检测到新提交。

**验收标准**：
- WHEN GitHub 仓库有新提交 THEN 系统应在 1 分钟内检测到新提交

---

### 4.2 可靠性需求

#### REQ-013: 发布失败重试

**描述**：系统应在发布失败时进行重试。

**验收标准**：
- WHEN 技能发布失败 THEN 系统应重试 3 次
- WHEN 3 次重试均失败 THEN 系统应提示用户发布失败

---

### 4.3 可维护性需求

#### REQ-014: 日志记录

**描述**：系统应记录关键操作的日志。

**验收标准**：
- WHEN 系统启动 THEN 系统应记录启动日志
- WHEN 系统发布技能 THEN 系统应记录发布日志
- WHEN 系统检测到错误 THEN 系统应记录错误日志

---

### 4.4 安全性需求

#### REQ-015: API Key 保护

**描述**：系统应保护用户的 API Key 不泄露。

**验收标准**：
- WHEN 系统记录日志 THEN 系统不应记录 API Key 的完整内容
- WHEN 系统显示错误信息 THEN 系统不应显示 API Key 的完整内容

---

## 5. 约束条件

### 5.1 技术约束

- 系统使用 Python 语言开发
- 系统使用 requests 库调用 ClawHub API
- 系统使用 GitHub API 或 git 命令获取仓库信息
- 配置文件格式支持 YAML 或 JSON
- AI 服务通过 OpenAI 兼容 API 接口调用 LLM
- Agent 能力基于 LLM 的 function calling 实现

### 5.2 业务约束

- 技能名称从 skill.md 文件中读取
- 批量发布模式下，所有技能的版本号固定为 0.0.1
- 监控发布模式下，技能名称和版本号从 commit message 中提取
- commit message 格式为 `update skill: solution/sac/{skill-name} {version}`
- AI changelog 生成功能为可选特性，未配置时系统保持原有行为
- changelog 来源优先级：AI 生成 → commit message → 默认模板

---

## 6. 附录

### 6.1 配置文件示例

#### YAML 格式

```yaml
clawhub:
  api_key: "clh_your_api_key_here"

github:
  owner: "your-username"
  repo: "your-repo-name"
  branch: "main"
  token: "ghp_your_github_token_here"

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
```

#### JSON 格式

```json
{
  "clawhub": {
    "api_key": "clh_your_api_key_here"
  },
  "github": {
    "owner": "your-username",
    "repo": "your-repo-name",
    "branch": "main",
    "token": "ghp_your_github_token_here"
  }
}
```

### 6.2 Commit Message 格式示例

```
update skill: solution/sac/huawei-cloud-sac-new-api v0.0.1
```

### 6.3 ClawHub API 发布接口

**接口地址**：`POST /api/v1/skills`

**请求头**：
```
Authorization: Bearer clh_your_api_key_here
Content-Type: multipart/form-data
```

**请求体**：
```
payload: JSON 字符串，包含技能信息
files: 技能 ZIP 文件
```

**响应**：
```json
{
  "ok": true,
  "skillId": "string",
  "versionId": "string"
}
```

---

🎯
