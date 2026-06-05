import subprocess
import sys
from models.models import PublishResponse
from utils.logger import get_logger



class CLIError(Exception):
    """CLI 错误"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ClawHubClient:
    """ClawHub CLI 客户端"""

    def __init__(self):
        self.cli_name = "clawhub"
        self.logger = get_logger(__name__)

    def check_cli_installed(self) -> bool:
        """检查 CLI 是否已安装"""
        try:
            result = subprocess.run(
                [self.cli_name, "-V"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                shell=True
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                self.logger.info(f"ClawHub CLI 已安装: {version}")
                return True
            else:
                self.logger.error("ClawHub CLI 未安装")
                return False
        except FileNotFoundError:
            self.logger.error("ClawHub CLI 未找到")
            return False
        except Exception as e:
            self.logger.error(f"检查 CLI 失败: {str(e)}")
            return False

    def check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            result = subprocess.run(
                [self.cli_name, "whoami"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                shell=True
            )
            if result.returncode == 0:
                username = result.stdout.strip().replace("√ ", "")
                self.logger.info(f"已登录: {username}")
                return True
            else:
                self.logger.error("未登录，请先运行: clawhub login")
                return False
        except Exception as e:
            self.logger.error(f"检查登录状态失败: {str(e)}")
            return False


    def publish_skill(
        self,
        skill_path: str,
        slug: str,
        display_name: str,
        version: str,
        changelog: str = "",
        owner: str = ""
    ) -> PublishResponse:
        """发布技能"""
        self.logger.info(f"========== 开始发布技能 ==========")
        self.logger.info(f"技能名称 (slug): {slug}")
        self.logger.info(f"显示名称 (display_name): {display_name}")
        self.logger.info(f"版本号 (version): {version}")
        self.logger.info(f"更新日志 (changelog): {changelog}")
        self.logger.info(f"发布者 (owner): {owner if owner else '默认'}")
        self.logger.info(f"技能路径 (skill_path): {skill_path}")

        # 检查版本号是否包含 v
        if 'v' in version.lower():
            self.logger.error(f"=========================================")
            self.logger.error(f"❌ 版本号格式错误！")
            self.logger.error(f"版本号包含非法字符 'v': {version}")
            self.logger.error(f"版本号应该是纯数字格式，如: 0.0.1, 1.0.0, 2.3.4")
            self.logger.error(f"ClawHub CLI 会自动添加 'v' 前缀，所以这里不应该包含 'v'")
            self.logger.error(f"=========================================")
            raise CLIError(f"版本号包含非法字符 'v': {version}。版本号应该是纯数字格式，如: 0.0.1, 1.0.0。ClawHub CLI 会自动添加 'v' 前缀，所以这里不应该包含 'v'")

        # 构建命令
        cmd = [
            self.cli_name, "publish",
            skill_path,
            "--slug", slug,
            "--name", display_name,
            "--version", version
        ]

        if changelog:
            cmd.extend(["--changelog", changelog])

        if owner:
            cmd.extend(["--owner", owner])

        self.logger.info(f"========== 执行 ClawHub CLI 命令 ==========")
        self.logger.info(f"完整命令: {' '.join(cmd)}")
        self.logger.info(f"=========================================")

        try:
            # 修复 Windows 控制台编码问题
            if sys.platform == "win32":
                subprocess.run("", shell=True)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                shell=True
            )

            self.logger.info(f"========== ClawHub CLI 命令执行结果 ==========")
            self.logger.info(f"返回码 (returncode): {result.returncode}")
            self.logger.info(f"标准输出 (stdout): {result.stdout if result.stdout else '(空)'}")
            self.logger.info(f"标准错误 (stderr): {result.stderr if result.stderr else '(空)'}")
            self.logger.info(f"=========================================")

            # 检查返回码
            if result.returncode == 0:
                self.logger.info(f"✓ 技能发布成功: {slug} {version}")
                # 尝试从输出中提取访问链接
                output = result.stdout
                if "https://clawhub.ai/skills/" in output:
                    skill_url = output.split("https://clawhub.ai/skills/")[1].split()[0]
                    skill_id = skill_url
                    version_id = f"{slug}@{version}"
                    return PublishResponse(
                        ok=True,
                        skill_id=skill_id,
                        version_id=version_id
                    )
                return PublishResponse(ok=True)
            else:
                error_msg = result.stderr or result.stdout
                self.logger.error(f"发布失败: {error_msg}")
                raise CLIError(f"发布失败: {error_msg}")

        except subprocess.TimeoutExpired:
            raise CLIError("发布超时")
        except Exception as e:
            raise CLIError(f"发布失败: {str(e)}")
