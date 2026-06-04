# ClawHub Skill Publisher 技术设计文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 功能名称 | ClawHub Skill Publisher |
| 文档版本 | v1.0 |
| 创建日期 | 2026-06-03 |
| 文档状态 | 待评审 |

---

## 1. 引言

### 1.1 文档目的

本文档旨在详细描述 ClawHub Skill Publisher 的技术设计方案，包括系统架构、模块设计、接口定义、数据模型等内容，为后续的开发实现提供指导。

### 1.2 参考文档

- ClawHub Skill Publisher 需求规格说明书 (spec.md)
- ClawHub API Guidance 技能文档
- ClawHub API 接口参考文档

---

## 2. 系统架构

### 2.1 总体架构

系统采用模块化设计，主要包含以下模块：

```
┌─────────────────────────────────────────────────────────────┐
│                     ClawHub Skill Publisher                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   配置管理   │  │  批量发布器  │  │  监控发布器  │      │
│  │  ConfigMgr   │  │ BatchPublshr │  │  MonitorPub  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                           │                                 │
│                   ┌───────┴───────┐                         │
│                   │  技能发布器   │                         │
│                   │ SkillPublisher │                         │
│                   └───────┬───────┘                         │
│                           │                                 │
│         ┌─────────────────┼─────────────────┐               │
│         │                 │                 │               │
│  ┌──────┴──────┐  ┌───────┴───────┐  ┌─────┴─────┐        │
│  │ ClawHub API │  │  GitHub API   │  │ Git Client│        │
│  │   Client    │  │    Client     │  │           │        │
│  └─────────────┘  └───────────────┘  └───────────┘        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块说明

| 模块名称 | 职责描述 |
|---------|---------|
| ConfigMgr | 配置管理模块，负责加载和验证配置文件 |
| BatchPublshr | 批量发布器，负责批量发布技能到 ClawHub |
| MonitorPub | 监控发布器，负责监控 GitHub 提交记录并发布技能 |
| SkillPublisher | 技能发布器，负责调用 ClawHub API 发布技能 |
| ClawHub API Client | ClawHub API 客户端，负责与 ClawHub 平台交互 |
| GitHub API Client | GitHub API 客户端，负责与 GitHub 平台交互 |
| Git Client | Git 客户端，负责执行 git 命令 |

---

## 3. 模块设计

### 3.1 配置管理模块 (ConfigMgr)

#### 3.1.1 职责

- 加载配置文件（YAML/JSON）
- 验证配置文件的完整性和正确性
- 提供配置信息的访问接口

#### 3.1.2 接口定义

```python
class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: str):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径
        """
        pass

    def load_config(self) -> dict:
        """
        加载配置文件

        Returns:
            配置字典

        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置文件格式错误
        """
        pass

    def validate_config(self, config: dict) -> bool:
        """
        验证配置文件

        Args:
            config: 配置字典

        Returns:
            验证结果

        Raises:
            ValueError: 配置文件验证失败
        """
        pass

    def get_clawhub_config(self) -> dict:
        """
        获取 ClawHub 配置

        Returns:
            ClawHub 配置字典
        """
        pass

    def get_github_config(self) -> dict:
        """
        获取 GitHub 配置

        Returns:
            GitHub 配置字典
        """
        pass
```

#### 3.1.3 数据模型

```python
@dataclass
class ClawHubConfig:
    """ClawHub 配置"""
    api_key: str

@dataclass
class GitHubConfig:
    """GitHub 配置"""
    owner: str
    repo: str
    branch: str
    token: str
```

---

### 3.2 批量发布器 (BatchPublshr)

#### 3.2.1 职责

- 扫描 GitHub 仓库中的所有 skill.md 文件
- 从 skill.md 文件中提取技能名称
- 调用技能发布器发布技能
- 显示发布进度

#### 3.2.2 接口定义

```python
class BatchPublisher:
    """批量发布器"""

    def __init__(self, github_client: GitHubClient, skill_publisher: SkillPublisher):
        """
        初始化批量发布器

        Args:
            github_client: GitHub 客户端
            skill_publisher: 技能发布器
        """
        pass

    def scan_skills(self) -> list[dict]:
        """
        扫描仓库中的所有技能

        Returns:
            技能列表，每个技能包含 skill_name 和 skill_path
        """
        pass

    def publish_skills(self, skills: list[dict]) -> dict:
        """
        批量发布技能

        Args:
            skills: 技能列表

        Returns:
            发布结果统计
        """
        pass

    def display_progress(self, total: int, current: int):
        """
        显示发布进度

        Args:
            total: 总技能数量
            current: 当前已发布数量
        """
        pass
```

#### 3.2.3 数据模型

```python
@dataclass
class SkillInfo:
    """技能信息"""
    skill_name: str
    skill_path: str
    version: str = "0.0.1"

@dataclass
class PublishResult:
    """发布结果"""
    total: int
    success: int
    failed: int
    failed_skills: list[dict]
```

---

### 3.3 监控发布器 (MonitorPub)

#### 3.3.1 职责

- 监控 GitHub 仓库的提交记录
- 从 commit message 中提取技能名称和版本号
- 调用技能发布器发布技能

#### 3.3.2 接口定义

```python
class MonitorPublisher:
    """监控发布器"""

    def __init__(self, github_client: GitHubClient, skill_publisher: SkillPublisher):
        """
        初始化监控发布器

        Args:
            github_client: GitHub 客户端
            skill_publisher: 技能发布器
        """
        pass

    def monitor_commits(self, interval: int = 60):
        """
        监控提交记录

        Args:
            interval: 监控间隔（秒）
        """
        pass

    def extract_skill_info(self, commit_message: str) -> dict:
        """
        从 commit message 中提取技能信息

        Args:
            commit_message: 提交消息

        Returns:
            技能信息字典，包含 skill_name 和 version

        Raises:
            ValueError: commit message 格式错误
        """
        pass

    def publish_skill(self, skill_name: str, version: str) -> bool:
        """
        发布技能

        Args:
            skill_name: 技能名称
            version: 版本号

        Returns:
            发布结果
        """
        pass
```

#### 3.3.3 数据模型

```python
@dataclass
class CommitInfo:
    """提交信息"""
    sha: str
    message: str
    author: str
    timestamp: datetime
```

---

### 3.4 技能发布器 (SkillPublisher)

#### 3.4.1 职责

- 打包技能文件
- 调用 ClawHub API 发布技能
- 处理发布错误

#### 3.4.2 接口定义

```python
class SkillPublisher:
    """技能发布器"""

    def __init__(self, clawhub_client: ClawHubClient):
        """
        初始化技能发布器

        Args:
            clawhub_client: ClawHub 客户端
        """
        pass

    def pack_skill(self, skill_path: str) -> bytes:
        """
        打包技能文件

        Args:
            skill_path: 技能路径

        Returns:
            技能 ZIP 文件内容
        """
        pass

    def publish(self, skill_name: str, version: str, skill_zip: bytes) -> dict:
        """
        发布技能

        Args:
            skill_name: 技能名称
            version: 版本号
            skill_zip: 技能 ZIP 文件内容

        Returns:
            发布结果

        Raises:
            PublishError: 发布失败
        """
        pass

    def retry_publish(self, skill_name: str, version: str, skill_zip: bytes, max_retries: int = 3) -> dict:
        """
        重试发布技能

        Args:
            skill_name: 技能名称
            version: 版本号
            skill_zip: 技能 ZIP 文件内容
            max_retries: 最大重试次数

        Returns:
            发布结果
        """
        pass
```

#### 3.4.3 数据模型

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
    skill_id: str | None = None
    version_id: str | None = None
    error: str | None = None
```

---

### 3.5 ClawHub API 客户端 (ClawHubClient)

#### 3.5.1 职责

- 封装 ClawHub API 调用
- 处理 API 响应和错误
- 实现限流和重试机制

#### 3.5.2 接口定义

```python
class ClawHubClient:
    """ClawHub API 客户端"""

    BASE_URL = "https://clawhub.ai/api/v1"

    def __init__(self, api_key: str):
        """
        初始化 ClawHub 客户端

        Args:
            api_key: API Key
        """
        pass

    def publish_skill(self, payload: dict, files: bytes) -> dict:
        """
        发布技能

        Args:
            payload: 发布载荷
            files: 技能 ZIP 文件

        Returns:
            发布响应

        Raises:
            APIError: API 调用失败
        """
        pass

    def handle_rate_limit(self, response: Response):
        """
        处理限流

        Args:
            response: HTTP 响应
        """
        pass

    def handle_error(self, response: Response):
        """
        处理错误

        Args:
            response: HTTP 响应

        Raises:
            APIError: API 调用失败
        """
        pass
```

#### 3.5.3 错误处理

```python
class APIError(Exception):
    """API 错误"""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{status_code}] {message}")

class PublishError(Exception):
    """发布错误"""

    def __init__(self, skill_name: str, version: str, reason: str):
        self.skill_name = skill_name
        self.version = version
        self.reason = reason
        super().__init__(f"Failed to publish {skill_name} {version}: {reason}")
```

---

### 3.6 GitHub API 客户端 (GitHubClient)

#### 3.6.1 职责

- 封装 GitHub API 调用
- 获取仓库提交记录
- 获取仓库文件列表

#### 3.6.2 接口定义

```python
class GitHubClient:
    """GitHub API 客户端"""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, owner: str, repo: str, branch: str = "main"):
        """
        初始化 GitHub 客户端

        Args:
            token: GitHub Token
            owner: 仓库所有者
            repo: 仓库名称
            branch: 分支名称
        """
        pass

    def get_commits(self, since: datetime | None = None) -> list[dict]:
        """
        获取提交记录

        Args:
            since: 起始时间

        Returns:
            提交记录列表
        """
        pass

    def get_files(self, path: str = "") -> list[dict]:
        """
        获取文件列表

        Args:
            path: 文件路径

        Returns:
            文件列表
        """
        pass

    def get_file_content(self, path: str) -> str:
        """
        获取文件内容

        Args:
            path: 文件路径

        Returns:
            文件内容
        """
        pass
```

---

### 3.7 Git 客户端 (GitClient)

#### 3.7.1 职责

- 执行 git 命令
- 克隆仓库
- 获取提交记录

#### 3.7.2 接口定义

```python
class GitClient:
    """Git 客户端"""

    def __init__(self, repo_url: str, local_path: str):
        """
        初始化 Git 客户端

        Args:
            repo_url: 仓库 URL
            local_path: 本地路径
        """
        pass

    def clone(self, branch: str = "main"):
        """
        克隆仓库

        Args:
            branch: 分支名称
        """
        pass

    def pull(self):
        """
        拉取最新代码
        """
        pass

    def get_commits(self, since: datetime | None = None) -> list[dict]:
        """
        获取提交记录

        Args:
            since: 起始时间

        Returns:
            提交记录列表
        """
        pass
```

---

## 4. 数据模型

### 4.1 配置数据模型

```python
@dataclass
class AppConfig:
    """应用配置"""
    clawhub: ClawHubConfig
    github: GitHubConfig
    mode: str  # "batch" or "monitor"
    log_level: str = "INFO"
```

### 4.2 技能数据模型

```python
@dataclass
class Skill:
    """技能"""
    name: str
    version: str
    display_name: str
    description: str
    files: list[SkillFile]
    tags: list[str] = field(default_factory=list)

@dataclass
class SkillFile:
    """技能文件"""
    path: str
    content: bytes
```

---

## 5. 接口设计

### 5.1 ClawHub API 接口

#### 5.1.1 发布技能

**接口地址**：`POST /api/v1/skills`

**请求头**：
```
Authorization: Bearer {api_key}
Content-Type: multipart/form-data
```

**请求体**：
```
payload: {PublishPayload}
files: {skill_zip}
```

**响应**：
```json
{
  "ok": true,
  "skillId": "skill_id",
  "versionId": "version_id"
}
```

---

### 5.2 GitHub API 接口

#### 5.2.1 获取提交记录

**接口地址**：`GET /repos/{owner}/{repo}/commits`

**请求头**：
```
Authorization: Bearer {token}
Accept: application/vnd.github.v3+json
```

**查询参数**：
- `sha`: 分支名称
- `since`: 起始时间（ISO 8601 格式）

**响应**：
```json
[
  {
    "sha": "commit_sha",
    "commit": {
      "message": "commit message",
      "author": {
        "date": "2024-01-01T00:00:00Z"
      }
    },
    "author": {
      "login": "author_login"
    }
  }
]
```

#### 5.2.2 获取文件列表

**接口地址**：`GET /repos/{owner}/{repo}/contents/{path}`

**请求头**：
```
Authorization: Bearer {token}
Accept: application/vnd.github.v3+json
```

**查询参数**：
- `ref`: 分支名称

**响应**：
```json
[
  {
    "name": "file_name",
    "path": "file_path",
    "type": "file"
  }
]
```

---

## 6. 错误处理

### 6.1 错误码定义

| 错误码 | 错误信息 | 处理方式 |
|-------|---------|---------|
| 401 | Unauthorized | 提示用户 API Key 或 Token 无效 |
| 403 | Forbidden | 提示用户权限不足 |
| 404 | Not Found | 提示用户资源不存在 |
| 413 | Payload Too Large | 提示用户文件过大 |
| 415 | Unsupported Media Type | 提示用户文件格式不支持 |
| 429 | Too Many Requests | 等待 Retry-After 指定的时间后重试 |
| 500 | Internal Server Error | 提示用户服务器错误，稍后重试 |

### 6.2 重试机制

```python
def retry_with_backoff(func: Callable, max_retries: int = 3, base_delay: float = 1.0) -> Any:
    """
    指数退避重试

    Args:
        func: 要重试的函数
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）

    Returns:
        函数返回值

    Raises:
        Exception: 重试失败后抛出原始异常
    """
    pass
```

---

## 7. 日志设计

### 7.1 日志级别

| 日志级别 | 用途 |
|---------|------|
| DEBUG | 调试信息 |
| INFO | 一般信息 |
| WARNING | 警告信息 |
| ERROR | 错误信息 |
| CRITICAL | 严重错误 |

### 7.2 日志格式

```
[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s
```

### 7.3 日志内容

- 系统启动日志
- 配置加载日志
- 技能发布日志
- 错误日志

---

## 8. 安全设计

### 8.1 API Key 保护

- API Key 不应在日志中完整显示
- API Key 不应在错误信息中完整显示
- API Key 应存储在配置文件中，不应硬编码

### 8.2 敏感信息脱敏

```python
def mask_api_key(api_key: str) -> str:
    """
    脱敏 API Key

    Args:
        api_key: API Key

    Returns:
        脱敏后的 API Key
    """
    if len(api_key) <= 8:
        return "***"
    return f"{api_key[:4]}***{api_key[-4:]}"
```

---

## 9. 部署设计

### 9.1 目录结构

```
clawhub-skill-publisher/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── config_manager.py
│   ├── publisher/
│   │   ├── __init__.py
│   │   ├── skill_publisher.py
│   │   ├── batch_publisher.py
│   │   └── monitor_publisher.py
│   ├── client/
│   │   ├── __init__.py
│   │   ├── clawhub_client.py
│   │   ├── github_client.py
│   │   └── git_client.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       └── retry.py
├── config.yaml
├── requirements.txt
├── README.md
└── .gitignore
```

### 9.2 依赖包

```
requests>=2.31.0
pyyaml>=6.0.0
gitpython>=3.1.40
```

---

## 10. 测试设计

### 10.1 单元测试

- 配置管理模块测试
- 技能发布器测试
- ClawHub API 客户端测试
- GitHub API 客户端测试

### 10.2 集成测试

- 批量发布流程测试
- 监控发布流程测试

### 10.3 端到端测试

- 完整发布流程测试

---

🎯
