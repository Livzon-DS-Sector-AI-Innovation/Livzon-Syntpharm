# mypy: ignore-errors
"""导出文件下载路径解析的白名单防护单元测试。

只测纯函数 ``_resolve_export_file``：``filename`` 来自 query（外部不可信），
必须挡住 ``../``、绝对路径、子目录与软链逃逸。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.modules.registration.dossier_writer.api import _resolve_export_file


@pytest.fixture()
def outputs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """把 STORAGE_ROOT 指到 tmp_path，并返回其中的 outputs 目录。"""
    storage_root = tmp_path / "storage"
    outputs = storage_root / "products" / "p1" / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "ok.docx").write_bytes(b"docx")
    (storage_root / "secret.txt").write_bytes(b"secret")

    settings = get_settings()
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(storage_root), raising=False)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"), raising=False)
    return outputs


def test_allows_direct_child(outputs_dir: Path) -> None:
    resolved = _resolve_export_file(str(outputs_dir), "ok.docx")
    assert resolved is not None
    assert resolved.name == "ok.docx"
    assert resolved.parent == outputs_dir.resolve()


@pytest.mark.parametrize(
    "filename",
    [
        "../secret.txt",
        "../../.env",
        "/etc/passwd",
        "sub/ok.docx",
        ".",
        "..",
        "",
        "nope.docx",
        "ok.docx\x00.png",
    ],
)
def test_rejects_unsafe_filenames(outputs_dir: Path, filename: str) -> None:
    assert _resolve_export_file(str(outputs_dir), filename) is None


def test_rejects_missing_outputs_path(outputs_dir: Path) -> None:
    assert _resolve_export_file(None, "ok.docx") is None


def test_rejects_outputs_outside_whitelist(tmp_path: Path, outputs_dir: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "ok.docx").write_bytes(b"x")
    assert _resolve_export_file(str(outside), "ok.docx") is None


def test_rejects_symlink_escape(outputs_dir: Path) -> None:
    link = outputs_dir / "link.docx"
    try:
        os.symlink("/etc/passwd", link)
    except (OSError, NotImplementedError):  # pragma: no cover - 无权限建软链时跳过
        pytest.skip("当前环境不允许创建符号链接")
    assert _resolve_export_file(str(outputs_dir), "link.docx") is None
