"""Shared test fixtures."""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get the project root directory by finding pyproject.toml."""
    current = Path(__file__).resolve()
    # Go up from tests/conftest.py to find pyproject.toml
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            # Verify this is the correct root by checking for app directory
            assert (parent / "app").exists(), f"定位到错误的仓库根: {parent}"
            return parent
    raise RuntimeError("未找到仓库根（pyproject.toml）")
