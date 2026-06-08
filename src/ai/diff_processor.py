import re
from dataclasses import dataclass, field
from utils.logger import get_logger


@dataclass
class DiffConfig:
    max_diff_size: int = 512000
    max_file_diff_lines: int = 500
    exclude_binary: bool = True
    sensitive_patterns: list[str] = field(default_factory=lambda: [
        r'(?:api[_-]?key|token|secret|password|credential|apikey)\s*[:=]\s*["\']?[\w\-]{8,}',
    ])


class DiffProcessor:
    def __init__(self, diff_config: DiffConfig = None):
        self.config = diff_config or DiffConfig()
        self.logger = get_logger(__name__)

    def process(self, diff: str) -> str:
        if not diff:
            return diff
        result = diff
        if self.config.exclude_binary:
            result = self.remove_binary_diffs(result)
        result = self.truncate_long_diffs(result)
        result = self.redact_sensitive_info(result)
        result = self.truncate_by_size(result)
        return result

    def remove_binary_diffs(self, diff: str) -> str:
        binary_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.woff', '.woff2', '.ttf', '.eot',
            '.pyc', '.pyo', '.so', '.dll', '.exe', '.bin',
            '.mp3', '.mp4', '.wav', '.avi', '.mov',
        }
        lines = diff.split('\n')
        filtered_lines = []
        skip = False
        for line in lines:
            if line.startswith('diff --git'):
                skip = False
                for ext in binary_extensions:
                    if ext in line.lower():
                        skip = True
                        break
            if not skip:
                filtered_lines.append(line)
        removed_count = len(lines) - len(filtered_lines)
        if removed_count > 0:
            self.logger.debug(f"移除了 {removed_count} 行二进制文件 diff")
        return '\n'.join(filtered_lines)

    def truncate_long_diffs(self, diff: str) -> str:
        lines = diff.split('\n')
        result_lines = []
        current_file_lines = []
        truncated_count = 0

        for line in lines:
            if line.startswith('diff --git'):
                if len(current_file_lines) > self.config.max_file_diff_lines:
                    kept = current_file_lines[:self.config.max_file_diff_lines]
                    kept.append(f"... [截断: 原始 {len(current_file_lines)} 行，保留 {self.config.max_file_diff_lines} 行]")
                    result_lines.extend(kept)
                    truncated_count += 1
                else:
                    result_lines.extend(current_file_lines)
                current_file_lines = [line]
            else:
                current_file_lines.append(line)

        if len(current_file_lines) > self.config.max_file_diff_lines:
            kept = current_file_lines[:self.config.max_file_diff_lines]
            kept.append(f"... [截断: 原始 {len(current_file_lines)} 行，保留 {self.config.max_file_diff_lines} 行]")
            result_lines.extend(kept)
            truncated_count += 1
        else:
            result_lines.extend(current_file_lines)

        if truncated_count > 0:
            self.logger.debug(f"截断了 {truncated_count} 个过长文件 diff")
        return '\n'.join(result_lines)

    def redact_sensitive_info(self, diff: str) -> str:
        result = diff
        for pattern in self.config.sensitive_patterns:
            result = re.sub(pattern, '[REDACTED]', result, flags=re.IGNORECASE)
        return result

    def truncate_by_size(self, diff: str) -> str:
        diff_bytes = diff.encode('utf-8')
        if len(diff_bytes) <= self.config.max_diff_size:
            return diff
        truncated = diff_bytes[:self.config.max_diff_size].decode('utf-8', errors='replace')
        self.logger.warning(f"diff 数据超过最大大小 {self.config.max_diff_size} 字节，已截断")
        return truncated + "\n... [diff 已截断]"