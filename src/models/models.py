from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class ClawHubConfig:
    """ClawHub 配置"""
    # CLI 模式下不需要 API Key，使用 OAuth 认证
    # 发布者句柄（可选）：指定skill发布到哪个组织或用户下
    # 例如: "your-org-handle" 或 "your-username"
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
