import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai.diff_processor import DiffProcessor, DiffConfig


class TestDiffProcessor:
    def setup_method(self):
        self.config = DiffConfig(
            max_diff_size=1000,
            max_file_diff_lines=10,
            exclude_binary=True,
        )
        self.processor = DiffProcessor(self.config)

    def test_process_empty_diff(self):
        assert self.processor.process("") == ""
        assert self.processor.process(None) is None

    def test_remove_binary_diffs(self):
        diff = (
            "diff --git a/src/main.py b/src/main.py\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "+import os\n"
            "diff --git a/image.png b/image.png\n"
            "Binary files differ\n"
            "diff --git a/readme.md b/readme.md\n"
            "--- a/readme.md\n"
            "+++ b/readme.md\n"
            "+new line\n"
        )
        result = self.processor.remove_binary_diffs(diff)
        assert "image.png" not in result
        assert "import os" in result
        assert "new line" in result

    def test_remove_binary_diffs_multiple_types(self):
        diff = (
            "diff --git a/file.py b/file.py\n"
            "+code\n"
            "diff --git a/icon.ico b/icon.ico\n"
            "Binary files differ\n"
            "diff --git a/font.woff b/font.woff\n"
            "Binary files differ\n"
            "diff --git a/lib.dll b/lib.dll\n"
            "Binary files differ\n"
            "diff --git a/data.pdf b/data.pdf\n"
            "Binary files differ\n"
        )
        result = self.processor.remove_binary_diffs(diff)
        assert "file.py" in result
        assert "icon.ico" not in result
        assert "font.woff" not in result
        assert "lib.dll" not in result
        assert "data.pdf" not in result

    def test_truncate_long_diffs(self):
        header = "diff --git a/big.py b/big.py\n"
        lines = [f"+line {i}" for i in range(20)]
        diff = header + "\n".join(lines)

        result = self.processor.truncate_long_diffs(diff)
        assert "截断" in result
        assert "原始 21 行" in result

    def test_truncate_long_diffs_under_limit(self):
        diff = "diff --git a/small.py b/small.py\n+line 1\n+line 2\n"
        result = self.processor.truncate_long_diffs(diff)
        assert result == diff

    def test_redact_sensitive_info(self):
        diff = (
            "api_key = sk-1234567890abcdef1234567890abcdef1234567890abcdef1234\n"
            'token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn\n'
            'password = "mysecretpassword123"\n'
            "normal code here\n"
        )
        result = self.processor.redact_sensitive_info(diff)
        assert "[REDACTED]" in result
        assert "normal code here" in result

    def test_truncate_by_size(self):
        large_diff = "x" * 2000
        result = self.processor.truncate_by_size(large_diff)
        assert len(result) < 2000
        assert "截断" in result

    def test_truncate_by_size_under_limit(self):
        small_diff = "x" * 100
        result = self.processor.truncate_by_size(small_diff)
        assert result == small_diff

    def test_process_full_pipeline(self):
        diff = (
            "diff --git a/src/main.py b/src/main.py\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "+import os\n"
            "diff --git a/image.png b/image.png\n"
            "Binary files differ\n"
        )
        result = self.processor.process(diff)
        assert "import os" in result
        assert "image.png" not in result

    def test_process_pure_binary_diff(self):
        diff = (
            "diff --git a/icon.png b/icon.png\n"
            "Binary files differ\n"
        )
        result = self.processor.process(diff)
        assert "icon.png" not in result

    def test_exclude_binary_disabled(self):
        config = DiffConfig(exclude_binary=False, max_diff_size=10000, max_file_diff_lines=100)
        processor = DiffProcessor(config)
        diff = (
            "diff --git a/image.png b/image.png\n"
            "Binary files differ\n"
        )
        result = processor.process(diff)
        assert "image.png" in result