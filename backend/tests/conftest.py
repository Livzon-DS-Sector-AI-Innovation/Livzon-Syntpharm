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
            return parent
    raise RuntimeError("Could not find project root (pyproject.toml)")
