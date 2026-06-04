# ClawHub Skill Publisher

自动从 GitHub 发布技能到 ClawHub 的工具。

## 功能特性

- **批量发布模式**：一次性将 GitHub 仓库中的所有技能发布到 ClawHub
- **监控发布模式**：监控 GitHub 仓库的提交记录，自动发布新提交的技能
- **CLI 模式**：使用官方 clawhub CLI 工具进行发布，更可靠、更安全
- **自动检测**：自动检测 CLI 安装状态和登录状态
- **配置文件管理**：通过 YAML 配置文件管理 GitHub 仓库信息
- **错误处理和重试**：自动处理发布错误，支持指数退避重试
- **详细日志**：记录发布过程的详细日志

## 系统要求

- Python 3.8+
- Node.js 16+ （用于安装 clawhub CLI）
- clawhub CLI 0.18.0+

## 安装方法

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 clawhub CLI

```bash
npm install -g clawhub@0.18.0
```

### 3. 登录 ClawHub

```bash
clawhub login
```

这会打开浏览器进行 OAuth 认证。

### 4. 验证安装

```bash
# 检查 CLI 版本
clawhub -V

# 检查登录状态
clawhub whoami
```

## 配置方法

复制 `config.yaml` 示例文件，并修改配置：

```yaml
# ClawHub 配置（CLI 模式）
# 注意：使用 CLI 模式时，不需要 API Key
# 请先运行 `clawhub login` 进行 OAuth 认证
clawhub: {}

# GitHub 配置
github:
  owner: "your-username"
  repo: "your-repo-name"
  branch: "main"
  token: "ghp_your_github_token_here"

# 发布模式：batch（批量发布）或 monitor（监控发布）
mode: "batch"

# 日志级别：DEBUG, INFO, WARNING, ERROR
log_level: "INFO"
```

### 获取 GitHub Token

1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 选择 `repo` 权限
4. 生成并复制 token

## 使用方法

### 批量发布模式

批量发布模式会扫描 GitHub 仓库中所有包含 `skill.md` 文件的目录，并发布到 ClawHub。

```bash
python src/main.py
```

### 监控发布模式

监控发布模式会持续监控 GitHub 仓库的提交记录，当检测到符合格式的提交时，自动发布技能。

1. 修改 `config.yaml` 中的 `mode` 为 `"monitor"`
2. 运行程序：

```bash
python src/main.py
```

### Commit Message 格式

监控模式下，提交消息需要符合以下格式：

```
update skill: skills/xx/xx/{skill-name} v{version}
```

或

```
update skill: xx/xx/{skill-name} v{version}
```

**说明**：
- `skills` 在路径中不是必须的
- `xx/xx` 的个数不限定
- 以路径最后的 `{skill-name}` 作为技能名称
- 如果 commit 不符合上述格式，直接跳过不处理

**示例**：

```
update skill: skills/clh-api-guidance v0.0.1
update skill: skills/huawei-cloud-sac-new-api v1.0.0
update skill: solution/sac/hwc-cli-guidance v0.0.1
update skill: tools/my-tool v2.0.0
update skill: my-skill v0.0.1
```

## 项目结构

```
clawhub-skill-publish/
├── src/
│   ├── client/
│   │   ├── clawhub_client.py    # ClawHub CLI 客户端
│   │   ├── github_client.py     # GitHub API 客户端
│   │   └── git_client.py        # Git 客户端
│   ├── publisher/
│   │   ├── skill_publisher.py   # 技能发布器
│   │   ├── batch_publisher.py   # 批量发布器
│   │   └── monitor_publisher.py # 监控发布器
│   ├── models/
│   │   └── models.py            # 数据模型
│   ├── utils/
│   │   ├── logger.py            # 日志工具
│   │   └── retry.py             # 重试工具
│   └── main.py                  # 主程序入口
├── config.yaml                  # 配置文件
├── requirements.txt             # Python 依赖
└── README.md                    # 项目文档
```

## 工作原理

### 批量发布模式

1. 扫描 GitHub 仓库，查找所有包含 `skill.md` 文件的目录
2. 从目录路径提取技能名称
3. 从 GitHub 下载技能文件到本地临时目录
4. 从 `skill.md` 提取显示名称（displayName）
5. 使用 clawhub CLI 发布技能

### 监控发布模式

1. 定期获取 GitHub 仓库的最新提交记录
2. 解析提交消息，提取技能名称和版本号
3. 从 GitHub 下载技能文件到本地临时目录
4. 从 `skill.md` 提取显示名称（displayName）
5. 使用 clawhub CLI 发布技能

## CLI vs API

| 特性 | 直接调用 API | 使用 clawhub CLI |
|------|------------|----------------|
| 认证方式 | Bearer Token | OAuth 浏览器认证 |
| 许可证处理 | 需要手动接受 MIT-0 | CLI 自动处理 |
| 文件打包 | 手动 ZIP 打包 | CLI 自动处理 |
| 错误提示 | 基础错误信息 | 友好的错误提示 |
| 官方支持 | 无 | 官方维护 |

**结论**：使用 clawhub CLI 更简单、更可靠！

## 常见问题

### 1. 如何获取 clawhub API Key？

使用 CLI 模式不需要 API Key，只需运行 `clawhub login` 进行 OAuth 认证。

### 2. 如何获取 GitHub Token？

1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 选择 `repo` 权限
4. 生成并复制 token

### 3. 发布失败怎么办？

1. 检查 clawhub CLI 是否已安装：`clawhub -V`
2. 检查是否已登录：`clawhub whoami`
3. 检查 GitHub Token 是否有效
4. 查看日志文件获取详细错误信息

### 4. Slug 命名限制

ClawHub 有受保护的命名空间：
- ❌ 不能以 "clawhub-" 开头
- ❌ 不能以 "-clawhub" 结尾

**示例**：
```yaml
# 错误
slug: clawhub-api-guidance  # ❌ 使用受保护的命名空间

# 正确
slug: clh-api-guidance     # ✓ 使用缩写
slug: api-guidance-mai     # ✓ 添加后缀
```

### 5. Windows 控制台编码问题

程序会自动修复 Windows 控制台的 UTF-8 编码问题，确保中文正常显示。

## 许可证

MIT License
