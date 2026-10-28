"""Tests for the safety file proxy path resolution.

``_resolve_local_path`` 必须把可读范围限制在上传根目录内，
否则 ``/api/v1/safety/files/{file_path:path}`` 可被用来读取任意文件。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.modules.safety.api.files import _resolve_local_path


@pytest.fixture()
def uploads_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """准备一个临时上传根目录，并把配置指向它。"""
    uploads = tmp_path / "uploads"
    (uploads / "safety" / "hazard").mkdir(parents=True)
    (uploads / "safety" / "hazard" / "a.jpg").write_bytes(b"x")

    settings = get_settings()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(uploads), raising=False)
    monkeypatch.setattr(settings, "LEGACY_UPLOAD_DIR", "", raising=False)
    return uploads


def test_serves_file_inside_uploads(uploads_dir: Path) -> None:
    assert _resolve_local_path("safety/hazard/a.jpg") == str(uploads_dir / "safety" / "hazard" / "a.jpg")


def test_serves_legacy_uploads_prefix(uploads_dir: Path) -> None:
    assert _resolve_local_path("uploads/safety/hazard/a.jpg") == str(uploads_dir / "safety" / "hazard" / "a.jpg")


def test_rejects_parent_traversal(uploads_dir: Path, tmp_path: Path) -> None:
    (tmp_path / "secret.env").write_bytes(b"SECRET=1")
    assert _resolve_local_path("safety/hazard/../../secret.env") is None
    assert _resolve_local_path("../secret.env") is None


def test_rejects_file_at_cwd(uploads_dir: Path) -> None:
    """``.env`` 之类 cwd 下的文件不能被代理读到。"""
    assert _resolve_local_path(".env") is None


def test_rejects_absolute_path_outside_uploads(uploads_dir: Path) -> None:
    assert _resolve_local_path("/etc/passwd") is None


def test_rejects_symlink_escape(uploads_dir: Path) -> None:
    link = uploads_dir / "safety" / "evil"
    try:
        os.symlink("/etc", link)
    except (OSError, NotImplementedError):
        pytest.skip("当前环境不支持创建符号链接")
    assert _resolve_local_path("safety/evil/hostname") is None


def test_rejects_empty_and_null_byte(uploads_dir: Path) -> None:
    assert _resolve_local_path("") is None
    assert _resolve_local_path("safety/hazard/a.jpg\x00.png") is None
