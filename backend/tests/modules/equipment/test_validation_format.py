"""验证 validation.py 文件格式符合规范。

这是一个回归测试，确保文件格式问题不会再次出现。
"""

import subprocess
from pathlib import Path


def test_validation_py_ruff_format() -> None:
    """验证 validation.py 通过 ruff format 检查。

    这个测试确保文件格式符合项目规范，防止 CI 中的 ruff format check 失败。
    """
    validation_file = Path(__file__).parents[4] / "app" / "modules" / "equipment" / "service" / "validation.py"

    assert validation_file.exists(), f"Validation file not found: {validation_file}"

    # 运行 ruff format --check 验证格式
    result = subprocess.run(
        ["uv", "run", "ruff", "format", "--check", str(validation_file)],
        cwd=Path(__file__).parent.parent.parent.parent,
        capture_output=True,
        text=True,
    )

    # ruff format --check 返回 0 表示格式正确，1 表示需要格式化
    assert result.returncode == 0, f"validation.py 格式不符合规范:\nstdout: {result.stdout}\nstderr: {result.stderr}"


def test_validation_py_no_trailing_whitespace() -> None:
    """验证 validation.py 没有 trailing whitespace。"""
    validation_file = Path(__file__).parents[4] / "app" / "modules" / "equipment" / "service" / "validation.py"

    with open(validation_file, encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines, 1):
        # 检查是否有 trailing whitespace（不包括空行）
        if line.rstrip("\n") != line.rstrip():
            raise AssertionError(f"Line {i} has trailing whitespace: {repr(line)}")


def test_validation_py_ends_with_single_newline() -> None:
    """验证 validation.py 以单个换行符结尾。"""
    validation_file = Path(__file__).parents[4] / "app" / "modules" / "equipment" / "service" / "validation.py"

    with open(validation_file, "rb") as f:
        content = f.read()

    # 文件应该以单个 \n 结尾
    assert content.endswith(b"\n"), "File should end with a newline"
    assert not content.endswith(b"\n\n"), "File should not end with multiple newlines"
