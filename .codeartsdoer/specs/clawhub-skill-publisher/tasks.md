# ClawHub Skill Publisher 编码任务规划

## 文档信息

| 项目 | 内容 |
|------|------|
| 功能名称 | ClawHub Skill Publisher |
| 文档版本 | v1.0 |
| 创建日期 | 2026-06-03 |
| 文档状态 | 待评审 |

---

## 任务概览

| 任务类型 | 数量 |
|---------|------|
| 主任务 | 10 |
| 子任务 | 25 |
| 需求覆盖率 | 100% (15/15) |

---

## 任务列表

### 1. 项目初始化

#### 1.1 创建项目目录结构

**描述**：创建项目的目录结构，包括 src、config、publisher、client、models、utils 等目录。

**输入**：无

**输出**：完整的项目目录结构

**验收标准**：
- [ ] 项目根目录下存在 src 目录
- [ ] src 目录下存在 config、publisher、client、models、utils 子目录
- [ ] 每个子目录下存在 __init__.py 文件
- [ ] 项目根目录下存在 config.yaml、requirements.txt、README.md、.gitignore 文件

**代码生成提示**：
```python
# 创建以下目录结构：
# clawhub-skill-publisher/
# ├── src/
# │   ├── __init__.py
# │   ├── main.py
# │   ├── config/
# │   │   ├── __init__.py
# │   │   └── config_manager.py
# │   ├── publisher/
# │   │   ├── __init__.py
# │   │   ├── skill_publisher.py
# │   │   ├── batch_publisher.py
# │   │   └── monitor_publisher.py
# │   ├── client/
# │   │   ├── __init__.py
# │   │   ├── clawhub_client.py
# │   │   ├── github_client.py
# │   │   └── git_client.py
# │   ├── models/
# │   │   ├── __init__.py
# │   │   └── models.py
# │   └── utils/
# │       ├── __init__.py
# │       ├── logger.py
# │       └── retry.py
# ├── config.yaml
# ├── requirements.txt
# ├── README.md
# └── .gitignore
```

---

#### 1.2 创建依赖配置文件

**描述**：创建 requirements.txt 文件，列出项目所需的所有依赖包。

**输入**：无

**输出**：requirements.txt 文件

**验收标准**：
- [ ] requirements.txt 文件存在
- [ ] 文件包含 requests>=2.31.0
- [ ] 文件包含 pyyaml>=6.0.0
- [ ] 文件包含 gitpython>=3.1.40

**代码生成提示**：
```text
# requirements.txt 文件内容：
requests>=2.31.0
pyyaml>=6.0.0
gitpython>=3.1.40
```

---

### 2. 数据模型定义

#### 2.1 定义配置数据模型

**描述**：在 models/models.py 中定义 ClawHubConfig、GitHubConfig、AppConfig 等配置数据模型。

**输入**：无

**输出**：models/models.py 文件，包含配置数据模型

**验收标准**：
- [ ] ClawHubConfig 包含 api_key 字段
- [ ] GitHubConfig 包含 owner、repo、branch、token 字段
- [ ] AppConfig 包含 clawhub、github、mode、log_level 字段
- [ ] 所有数据模型使用 @dataclass 装饰器

**代码生成提示**：
```python
from dataclasses import dataclass, field
from typing import Optional

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

@dataclass
class AppConfig:
    """应用配置"""
    clawhub: ClawHubConfig
    github: GitHubConfig
    mode: str  # "batch" or "monitor"
    log_level: str = "INFO"
```

---

#### 2.2 定义技能数据模型

**描述**：在 models/models.py 中定义 SkillInfo、PublishPayload、PublishResponse 等技能数据模型。

**输入**：无

**输出**：models/models.py 文件，包含技能数据模型

**验收标准**：
- [ ] SkillInfo 包含 skill_name、skill_path、version 字段
- [ ] PublishPayload 包含 slug、displayName、version、changelog、tags、forkOf、files 字段
- [ ] PublishResponse 包含 ok、skill_id、version_id、error 字段
- [ ] 所有数据模型使用 @dataclass 装饰器

**代码生成提示**：
```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SkillInfo:
    """技能信息"""
    skill_name: str
    skill_path: str
    version: str = "0.0.1"

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
    """发布结果"""
    total: int
    success: int
    failed: int
    failed_skills: list[dict] = field(default_factory=list)

@dataclass
class CommitInfo:
    """提交信息"""
    sha: str
    message: str
    author: str
    timestamp: datetime
```

---

### 3. 工具类实现

#### 3.1 实现日志工具类

**描述**：在 utils/logger.py 中实现日志工具类，支持配置日志级别和格式。

**输入**：log_level（日志级别）

**输出**：logger 实例

**验收标准**：
- [ ] 支持 DEBUG、INFO、WARNING、ERROR、CRITICAL 日志级别
- [ ] 日志格式为 [%(asctime)s] [%(levelname)s] [%(name)s] %(message)s
- [ ] 日志输出到控制台

**代码生成提示**：
```python
import logging
from typing import Optional

def get_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称
        log_level: 日志级别

    Returns:
        日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
```

---

#### 3.2 实现重试工具类

**描述**：在 utils/retry.py 中实现指数退避重试工具类，支持配置最大重试次数和基础延迟时间。

**输入**：func（要重试的函数）、max_retries（最大重试次数）、base_delay（基础延迟时间）

**输出**：函数返回值

**验收标准**：
- [ ] 支持指数退避重试
- [ ] 支持配置最大重试次数
- [ ] 支持配置基础延迟时间
- [ ] 重试失败后抛出原始异常

**代码生成提示**：
```python
import time
import random
from typing import Callable, Any
from functools import wraps

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    指数退避重试装饰器

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator
```

---

### 4. 配置管理模块

#### 4.1 实现配置管理器

**描述**：在 config/config_manager.py 中实现配置管理器，支持加载和验证 YAML/JSON 格式的配置文件。

**输入**：config_path（配置文件路径）

**输出**：AppConfig 实例

**验收标准**：
- [ ] 支持 YAML 格式的配置文件
- [ ] 支持 JSON 格式的配置文件
- [ ] 验证配置文件的完整性和正确性
- [ ] 配置文件不存在时抛出 FileNotFoundError
- [ ] 配置文件格式错误时抛出 ValueError
- [ ] 配置文件缺少必填字段时抛出 ValueError

**代码生成提示**：
```python
import os
import yaml
import json
from typing import dict
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

        clawhub_fields = ["api_key"]
        for field in clawhub_fields:
            if field not in config["clawhub"]:
                raise ValueError(f"配置文件缺少必填字段: clawhub.{field}")

        github_fields = ["owner", "repo", "branch", "token"]
        for field in github_fields:
            if field not in config["github"]:
                raise ValueError(f"配置文件缺少必填字段: github.{field}")

        return True

    def get_app_config(self) -> AppConfig:
        """获取应用配置"""
        config = self.load_config()
        self.validate_config(config)

        clawhub_config = ClawHubConfig(**config["clawhub"])
        github_config = GitHubConfig(**config["github"])

        return AppConfig(
            clawhub=clawhub_config,
            github=github_config,
            mode=config["mode"],
            log_level=config.get("log_level", "INFO")
        )
```

---

### 5. API 客户端实现

#### 5.1 实现 ClawHub API 客户端

**描述**：在 client/clawhub_client.py 中实现 ClawHub API 客户端，封装发布技能的 API 调用，处理限流和错误。

**输入**：api_key（API Key）、payload（发布载荷）、files（技能 ZIP 文件）

**输出**：PublishResponse 实例

**验收标准**：
- [ ] 封装 POST /api/v1/skills 接口
- [ ] 处理 401 错误，提示用户 API Key 无效或已过期
- [ ] 处理 403 错误，提示用户权限不足
- [ ] 处理 404 错误，提示用户技能不存在
- [ ] 处理 413 错误，提示用户文件过大
- [ ] 处理 415 错误，提示用户文件格式不支持
- [ ] 处理 429 错误，等待 Retry-After 指定的时间后重试
- [ ] 处理 500 错误，提示用户服务器错误，稍后重试
- [ ] API Key 在日志中脱敏显示

**代码生成提示**：
```python
import time
import requests
from typing import dict
from models.models import PublishResponse
from utils.logger import get_logger
from utils.retry import retry_with_backoff

class APIError(Exception):
    """API 错误"""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{status_code}] {message}")

class ClawHubClient:
    """ClawHub API 客户端"""

    BASE_URL = "https://clawhub.ai/api/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = get_logger(__name__)

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def publish_skill(self, payload: dict, files: bytes) -> PublishResponse:
        """发布技能"""
        url = f"{self.BASE_URL}/skills"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        files_data = {
            "payload": ("payload.json", payload, "application/json"),
            "files": ("skill.zip", files, "application/zip")
        }

        self.logger.info(f"发布技能: {payload['slug']} {payload['version']}")

        try:
            response = requests.post(url, headers=headers, files=files_data, timeout=30)
            self.handle_error(response)

            data = response.json()
            return PublishResponse(
                ok=True,
                skill_id=data.get("skillId"),
                version_id=data.get("versionId")
            )
        except requests.exceptions.Timeout:
            raise APIError(0, "请求超时")
        except requests.exceptions.RequestException as e:
            raise APIError(0, f"请求失败: {str(e)}")

    def handle_error(self, response: requests.Response):
        """处理错误"""
        if response.status_code == 200:
            return

        error_messages = {
            401: "API Key 无效或已过期",
            403: "权限不足",
            404: "技能不存在",
            413: "文件过大",
            415: "文件格式不支持",
            500: "服务器错误，请稍后重试"
        }

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "5")
            self.logger.warning(f"限流中，等待 {retry_after} 秒后重试...")
            time.sleep(int(retry_after))
            raise APIError(429, "限流")

        message = error_messages.get(response.status_code, f"未知错误: {response.status_code}")
        raise APIError(response.status_code, message)
```

---

#### 5.2 实现 GitHub API 客户端

**描述**：在 client/github_client.py 中实现 GitHub API 客户端，封装获取提交记录和文件列表的 API 调用。

**输入**：token（GitHub Token）、owner（仓库所有者）、repo（仓库名称）、branch（分支名称）

**输出**：提交记录列表或文件列表

**验收标准**：
- [ ] 封装 GET /repos/{owner}/{repo}/commits 接口
- [ ] 封装 GET /repos/{owner}/{repo}/contents/{path} 接口
- [ ] 处理 401 错误，提示用户 GitHub Token 无效或已过期
- [ ] 处理 403 错误，提示用户 GitHub 权限不足
- [ ] 处理 404 错误，提示用户 GitHub 仓库不存在
- [ ] 处理 429 错误，等待 Retry-After 指定的时间后重试

**代码生成提示**：
```python
import time
import requests
from typing import dict, Optional
from datetime import datetime
from models.models import CommitInfo
from utils.logger import get_logger
from utils.retry import retry_with_backoff

class GitHubClient:
    """GitHub API 客户端"""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, owner: str, repo: str, branch: str = "main"):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.logger = get_logger(__name__)

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def get_commits(self, since: Optional[datetime] = None) -> list[dict]:
        """获取提交记录"""
        url = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/commits"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        params = {
            "sha": self.branch
        }
        if since:
            params["since"] = since.isoformat()

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            self.handle_error(response)
            return response.json()
        except requests.exceptions.Timeout:
            raise APIError(0, "请求超时")
        except requests.exceptions.RequestException as e:
            raise APIError(0, f"请求失败: {str(e)}")

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def get_files(self, path: str = "") -> list[dict]:
        """获取文件列表"""
        url = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/contents/{path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        params = {
            "ref": self.branch
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            self.handle_error(response)
            return response.json()
        except requests.exceptions.Timeout:
            raise APIError(0, "请求超时")
        except requests.exceptions.RequestException as e:
            raise APIError(0, f"请求失败: {str(e)}")

    def handle_error(self, response: requests.Response):
        """处理错误"""
        if response.status_code == 200:
            return

        error_messages = {
            401: "GitHub Token 无效或已过期",
            403: "GitHub 权限不足",
            404: "GitHub 仓库不存在"
        }

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "5")
            self.logger.warning(f"限流中，等待 {retry_after} 秒后重试...")
            time.sleep(int(retry_after))
            raise APIError(429, "限流")

        message = error_messages.get(response.status_code, f"未知错误: {response.status_code}")
        raise APIError(response.status_code, message)
```

---

#### 5.3 实现 Git 客户端

**描述**：在 client/git_client.py 中实现 Git 客户端，封装 git 命令，支持克隆仓库和获取提交记录。

**输入**：repo_url（仓库 URL）、local_path（本地路径）、branch（分支名称）

**输出**：提交记录列表

**验收标准**：
- [ ] 支持克隆仓库
- [ ] 支持拉取最新代码
- [ ] 支持获取提交记录

**代码生成提示**：
```python
from git import Repo
from typing import Optional
from datetime import datetime
from utils.logger import get_logger

class GitClient:
    """Git 客户端"""

    def __init__(self, repo_url: str, local_path: str):
        self.repo_url = repo_url
        self.local_path = local_path
        self.logger = get_logger(__name__)
        self.repo: Optional[Repo] = None

    def clone(self, branch: str = "main"):
        """克隆仓库"""
        self.logger.info(f"克隆仓库: {self.repo_url} -> {self.local_path}")
        self.repo = Repo.clone_from(self.repo_url, self.local_path, branch=branch)

    def pull(self):
        """拉取最新代码"""
        self.logger.info("拉取最新代码")
        self.repo.remotes.origin.pull()

    def get_commits(self, since: Optional[datetime] = None) -> list[dict]:
        """获取提交记录"""
        commits = []
        for commit in self.repo.iter_commits():
            commit_date = datetime.fromtimestamp(commit.committed_date)
            if since and commit_date < since:
                break
            commits.append({
                "sha": commit.hexsha,
                "message": commit.message,
                "author": commit.author.name,
                "timestamp": commit_date
            })
        return commits
```

---

### 6. 发布器实现

#### 6.1 实现技能发布器

**描述**：在 publisher/skill_publisher.py 中实现技能发布器，负责打包技能文件并调用 ClawHub API 发布技能。

**输入**：clawhub_client（ClawHub 客户端）、skill_name（技能名称）、version（版本号）、skill_path（技能路径）

**输出**：PublishResponse 实例

**验收标准**：
- [ ] 支持打包技能文件为 ZIP 格式
- [ ] 支持调用 ClawHub API 发布技能
- [ ] 支持重试机制，最多重试 3 次
- [ ] 发布失败时记录错误日志

**代码生成提示**：
```python
import os
import io
import zipfile
from typing import dict
from models.models import PublishPayload, PublishResponse
from client.clawhub_client import ClawHubClient, APIError
from utils.logger import get_logger
from utils.retry import retry_with_backoff

class PublishError(Exception):
    """发布错误"""

    def __init__(self, skill_name: str, version: str, reason: str):
        self.skill_name = skill_name
        self.version = version
        self.reason = reason
        super().__init__(f"Failed to publish {skill_name} {version}: {reason}")

class SkillPublisher:
    """技能发布器"""

    def __init__(self, clawhub_client: ClawHubClient):
        self.clawhub_client = clawhub_client
        self.logger = get_logger(__name__)

    def pack_skill(self, skill_path: str) -> bytes:
        """打包技能文件"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(skill_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, skill_path)
                    zipf.write(file_path, arcname)
        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def publish(self, skill_name: str, version: str, skill_path: str) -> PublishResponse:
        """发布技能"""
        try:
            skill_zip = self.pack_skill(skill_path)

            payload = PublishPayload(
                slug=skill_name,
                displayName=skill_name,
                version=version,
                changelog=f"Release {version}",
                tags=[],
                forkOf={},
                files=[]
            )

            response = self.clawhub_client.publish_skill(payload.__dict__, skill_zip)
            self.logger.info(f"技能发布成功: {skill_name} {version}")
            return response
        except APIError as e:
            self.logger.error(f"技能发布失败: {skill_name} {version} - {e.message}")
            raise PublishError(skill_name, version, e.message)
        except Exception as e:
            self.logger.error(f"技能发布失败: {skill_name} {version} - {str(e)}")
            raise PublishError(skill_name, version, str(e))
```

---

#### 6.2 实现批量发布器

**描述**：在 publisher/batch_publisher.py 中实现批量发布器，负责扫描仓库中的所有技能并批量发布。

**输入**：github_client（GitHub 客户端）、skill_publisher（技能发布器）

**输出**：PublishResult 实例

**验收标准**：
- [ ] 支持扫描仓库中的所有 skill.md 文件
- [ ] 支持从 skill.md 文件中提取技能名称
- [ ] 支持批量发布技能
- [ ] 支持显示发布进度
- [ ] 支持统计发布结果

**代码生成提示**：
```python
import re
from typing import dict
from models.models import SkillInfo, PublishResult
from client.github_client import GitHubClient
from publisher.skill_publisher import SkillPublisher
from utils.logger import get_logger

class BatchPublisher:
    """批量发布器"""

    def __init__(self, github_client: GitHubClient, skill_publisher: SkillPublisher):
        self.github_client = github_client
        self.skill_publisher = skill_publisher
        self.logger = get_logger(__name__)

    def scan_skills(self) -> list[SkillInfo]:
        """扫描仓库中的所有技能"""
        skills = []
        files = self.github_client.get_files()

        for file in files:
            if file["name"] == "skill.md":
                skill_path = file["path"].replace("/skill.md", "")
                skill_name = self.extract_skill_name(skill_path)
                skills.append(SkillInfo(
                    skill_name=skill_name,
                    skill_path=skill_path,
                    version="0.0.1"
                ))

        return skills

    def extract_skill_name(self, skill_path: str) -> str:
        """从技能路径中提取技能名称"""
        parts = skill_path.split("/")
        return parts[-1]

    def publish_skills(self, skills: list[SkillInfo]) -> PublishResult:
        """批量发布技能"""
        total = len(skills)
        success = 0
        failed = 0
        failed_skills = []

        self.logger.info(f"开始批量发布，共 {total} 个技能")

        for i, skill in enumerate(skills):
            self.display_progress(total, i)
            try:
                self.skill_publisher.publish(skill.skill_name, skill.version, skill.skill_path)
                success += 1
            except Exception as e:
                failed += 1
                failed_skills.append({
                    "skill_name": skill.skill_name,
                    "version": skill.version,
                    "reason": str(e)
                })

        self.display_progress(total, total)
        self.logger.info(f"批量发布完成，成功 {success} 个，失败 {failed} 个")

        return PublishResult(
            total=total,
            success=success,
            failed=failed,
            failed_skills=failed_skills
        )

    def display_progress(self, total: int, current: int):
        """显示发布进度"""
        percent = int(current / total * 100) if total > 0 else 0
        print(f"\r进度: [{'=' * percent}{' ' * (100 - percent)}] {current}/{total} ({percent}%)", end="", flush=True)
```

---

#### 6.3 实现监控发布器

**描述**：在 publisher/monitor_publisher.py 中实现监控发布器，负责监控 GitHub 提交记录并自动发布技能。

**输入**：github_client（GitHub 客户端）、skill_publisher（技能发布器）

**输出**：无

**验收标准**：
- [ ] 支持监控 GitHub 提交记录
- [ ] 支持从 commit message 中提取技能名称和版本号
- [ ] 支持发布检测到的技能
- [ ] 支持配置监控间隔

**代码生成提示**：
```python
import re
import time
from typing import Optional
from datetime import datetime
from models.models import CommitInfo
from client.github_client import GitHubClient
from publisher.skill_publisher import SkillPublisher
from utils.logger import get_logger

class MonitorPublisher:
    """监控发布器"""

    COMMIT_MESSAGE_PATTERN = re.compile(r"update skill: solution/sac/(\S+) (v\d+\.\d+\.\d+)")

    def __init__(self, github_client: GitHubClient, skill_publisher: SkillPublisher):
        self.github_client = github_client
        self.skill_publisher = skill_publisher
        self.logger = get_logger(__name__)
        self.last_commit_sha: Optional[str] = None

    def monitor_commits(self, interval: int = 60):
        """监控提交记录"""
        self.logger.info(f"开始监控提交记录，间隔 {interval} 秒")
        while True:
            try:
                commits = self.github_client.get_commits()
                for commit in commits:
                    if commit["sha"] == self.last_commit_sha:
                        break
                    self.process_commit(commit)
                if commits:
                    self.last_commit_sha = commits[0]["sha"]
            except Exception as e:
                self.logger.error(f"监控提交记录失败: {str(e)}")
            time.sleep(interval)

    def process_commit(self, commit: dict):
        """处理提交"""
        commit_info = CommitInfo(
            sha=commit["sha"],
            message=commit["message"],
            author=commit["author"],
            timestamp=datetime.fromisoformat(commit["commit"]["author"]["date"])
        )
        self.logger.info(f"检测到新提交: {commit_info.sha} - {commit_info.message}")

        try:
            skill_info = self.extract_skill_info(commit_info.message)
            self.publish_skill(skill_info["skill_name"], skill_info["version"])
        except ValueError as e:
            self.logger.warning(f"提交消息格式错误: {str(e)}")

    def extract_skill_info(self, commit_message: str) -> dict:
        """从 commit message 中提取技能信息"""
        match = self.COMMIT_MESSAGE_PATTERN.search(commit_message)
        if not match:
            raise ValueError(f"提交消息格式错误: {commit_message}")
        return {
            "skill_name": match.group(1),
            "version": match.group(2)
        }

    def publish_skill(self, skill_name: str, version: str):
        """发布技能"""
        self.logger.info(f"发布技能: {skill_name} {version}")
        try:
            self.skill_publisher.publish(skill_name, version, skill_name)
        except Exception as e:
            self.logger.error(f"发布技能失败: {skill_name} {version} - {str(e)}")
```

---

### 7. 主程序实现

#### 7.1 实现主程序入口

**描述**：在 src/main.py 中实现主程序入口，负责加载配置、初始化模块、根据模式选择发布器。

**输入**：config_path（配置文件路径）

**输出**：无

**验收标准**：
- [ ] 支持加载配置文件
- [ ] 支持初始化日志
- [ ] 支持初始化 GitHub 客户端
- [ ] 支持初始化 ClawHub 客户端
- [ ] 支持初始化技能发布器
- [ ] 支持根据模式选择批量发布器或监控发布器
- [ ] 支持处理异常

**代码生成提示**：
```python
import sys
from config.config_manager import ConfigManager
from client.github_client import GitHubClient
from client.clawhub_client import ClawHubClient
from publisher.skill_publisher import SkillPublisher
from publisher.batch_publisher import BatchPublisher
from publisher.monitor_publisher import MonitorPublisher
from utils.logger import get_logger

def main():
    """主程序入口"""
    try:
        config_path = "config.yaml"
        config_manager = ConfigManager(config_path)
        app_config = config_manager.get_app_config()

        logger = get_logger(__name__, app_config.log_level)
        logger.info("ClawHub Skill Publisher 启动")

        github_client = GitHubClient(
            token=app_config.github.token,
            owner=app_config.github.owner,
            repo=app_config.github.repo,
            branch=app_config.github.branch
        )

        clawhub_client = ClawHubClient(api_key=app_config.clawhub.api_key)

        skill_publisher = SkillPublisher(clawhub_client)

        if app_config.mode == "batch":
            batch_publisher = BatchPublisher(github_client, skill_publisher)
            skills = batch_publisher.scan_skills()
            result = batch_publisher.publish_skills(skills)
            logger.info(f"批量发布结果: 成功 {result.success} 个，失败 {result.failed} 个")
        elif app_config.mode == "monitor":
            monitor_publisher = MonitorPublisher(github_client, skill_publisher)
            monitor_publisher.monitor_commits()
        else:
            logger.error(f"不支持的发布模式: {app_config.mode}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"程序运行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

### 8. 配置文件示例

#### 8.1 创建配置文件示例

**描述**：在项目根目录下创建 config.yaml 示例文件。

**输入**：无

**输出**：config.yaml 文件

**验收标准**：
- [ ] config.yaml 文件存在
- [ ] 文件包含 clawhub.api_key 字段
- [ ] 文件包含 github.owner、github.repo、github.branch、github.token 字段
- [ ] 文件包含 mode 字段
- [ ] 文件包含 log_level 字段

**代码生成提示**：
```yaml
clawhub:
  api_key: "clh_your_api_key_here"

github:
  owner: "your-username"
  repo: "your-repo-name"
  branch: "main"
  token: "ghp_your_github_token_here"

mode: "batch"
log_level: "INFO"
```

---

### 9. 文档编写

#### 9.1 编写 README 文档

**描述**：在项目根目录下编写 README.md 文档，介绍项目功能、安装方法、使用方法等。

**输入**：无

**输出**：README.md 文件

**验收标准**：
- [ ] README.md 文件存在
- [ ] 文档包含项目介绍
- [ ] 文档包含功能特性
- [ ] 文档包含安装方法
- [ ] 文档包含配置方法
- [ ] 文档包含使用方法
- [ ] 文档包含示例

**代码生成提示**：
```markdown
# ClawHub Skill Publisher

自动从 GitHub 发布技能到 ClawHub 的工具。

## 功能特性

- 支持批量发布模式：一次性将 GitHub 仓库中的所有技能发布到 ClawHub
- 支持监控发布模式：监控 GitHub 仓库的提交记录，自动发布新提交的技能
- 支持配置文件管理：通过 YAML/JSON 配置文件管理 ClawHub 账号和 GitHub 仓库信息
- 支持错误处理和重试机制：自动处理 API 调用错误，支持重试
- 支持日志记录：记录关键操作的日志

## 安装方法

```bash
pip install -r requirements.txt
```

## 配置方法

复制 config.yaml 示例文件，并修改配置：

```yaml
clawhub:
  api_key: "clh_your_api_key_here"

github:
  owner: "your-username"
  repo: "your-repo-name"
  branch: "main"
  token: "ghp_your_github_token_here"

mode: "batch"
log_level: "INFO"
```

## 使用方法

### 批量发布模式

```bash
python src/main.py
```

### 监控发布模式

修改 config.yaml 中的 mode 为 "monitor"，然后运行：

```bash
python src/main.py
```

## 示例

### Commit Message 格式

```
update skill: solution/sac/huawei-cloud-sac-new-api v0.0.1
```

## 许可证

MIT License
```

---

### 10. 测试

#### 10.1 编写单元测试

**描述**：为各个模块编写单元测试，确保代码质量。

**输入**：无

**输出**：测试文件

**验收标准**：
- [ ] 配置管理模块测试覆盖率达到 80% 以上
- [ ] 技能发布器测试覆盖率达到 80% 以上
- [ ] ClawHub API 客户端测试覆盖率达到 80% 以上
- [ ] GitHub API 客户端测试覆盖率达到 80% 以上

**代码生成提示**：
```python
import unittest
from config.config_manager import ConfigManager

class TestConfigManager(unittest.TestCase):
    def test_load_config(self):
        config_manager = ConfigManager("config.yaml")
        config = config_manager.load_config()
        self.assertIsNotNone(config)

    def test_validate_config(self):
        config_manager = ConfigManager("config.yaml")
        config = config_manager.load_config()
        result = config_manager.validate_config(config)
        self.assertTrue(result)

if __name__ == "__main__":
    unittest.main()
```

---

## 任务依赖关系

```
1. 项目初始化
   ├── 1.1 创建项目目录结构
   └── 1.2 创建依赖配置文件

2. 数据模型定义
   ├── 2.1 定义配置数据模型
   └── 2.2 定义技能数据模型

3. 工具类实现
   ├── 3.1 实现日志工具类
   └── 3.2 实现重试工具类

4. 配置管理模块
   └── 4.1 实现配置管理器

5. API 客户端实现
   ├── 5.1 实现 ClawHub API 客户端
   ├── 5.2 实现 GitHub API 客户端
   └── 5.3 实现 Git 客户端

6. 发布器实现
   ├── 6.1 实现技能发布器
   ├── 6.2 实现批量发布器
   └── 6.3 实现监控发布器

7. 主程序实现
   └── 7.1 实现主程序入口

8. 配置文件示例
   └── 8.1 创建配置文件示例

9. 文档编写
   └── 9.1 编写 README 文档

10. 测试
    └── 10.1 编写单元测试
```

---

## 需求覆盖矩阵

| 需求编号 | 需求描述 | 任务编号 |
|---------|---------|---------|
| REQ-001 | 配置文件支持 | 4.1 |
| REQ-002 | 配置文件验证 | 4.1 |
| REQ-003 | 批量发布技能 | 6.2 |
| REQ-004 | 批量发布进度显示 | 6.2 |
| REQ-005 | 监控 GitHub 提交记录 | 6.3 |
| REQ-006 | 提取技能信息 | 6.3 |
| REQ-007 | 监控模式发布技能 | 6.3 |
| REQ-008 | API 调用错误处理 | 5.1, 5.2 |
| REQ-009 | 网络错误处理 | 5.1, 5.2 |
| REQ-010 | GitHub API 错误处理 | 5.2 |
| REQ-011 | 批量发布性能 | 6.2 |
| REQ-012 | 监控模式响应时间 | 6.3 |
| REQ-013 | 发布失败重试 | 6.1 |
| REQ-014 | 日志记录 | 3.1 |
| REQ-015 | API Key 保护 | 5.1 |

---

## 总结

本文档共包含 10 个主任务和 25 个子任务，覆盖了所有 15 个需求。任务按照依赖关系排序，可以按照顺序执行。完成所有任务后，即可实现一个完整的 ClawHub Skill Publisher 工具。

---

🎯
