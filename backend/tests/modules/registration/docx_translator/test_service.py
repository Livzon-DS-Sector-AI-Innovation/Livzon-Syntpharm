"""服务层参数校验与结果索引（不依赖 DB/LLM）。"""

from __future__ import annotations

import pytest

from app.core.exceptions import BadRequestException
from app.modules.registration.docx_translator.service import (
    UploadedDoc,
    build_job_config,
    find_output,
    sanitize_filename,
    validate_uploads,
)


def _upload(name: str = "a.docx", size: int = 10) -> UploadedDoc:
    return UploadedDoc(filename=name, data=b"x" * size)


def test_sanitize_filename_strips_path() -> None:
    assert sanitize_filename("../../etc/报告.docx") == "报告.docx"
    assert sanitize_filename("a/b\\c.docx") == "c.docx"


def test_validate_uploads_rejects_bad_type() -> None:
    with pytest.raises(BadRequestException):
        validate_uploads([_upload("a.pdf")], 50, 10)


def test_validate_uploads_rejects_oversize_and_count() -> None:
    with pytest.raises(BadRequestException, match="MB"):
        validate_uploads([_upload("big.docx", 2 * 1024 * 1024)], 1, 10)
    with pytest.raises(BadRequestException, match="最多"):
        validate_uploads([_upload(f"{i}.docx") for i in range(3)], 50, 2)


def test_validate_uploads_accepts_doc_and_wps() -> None:
    validate_uploads([_upload("a.doc"), _upload("b.wps"), _upload("c.docx")], 50, 10)


def test_build_job_config_rejects_same_language() -> None:
    with pytest.raises(BadRequestException):
        build_job_config("zh", "zh", "bilingual", 30)


def test_build_job_config_accepts_both_mode() -> None:
    config = build_job_config("en", "zh", "both", 20)
    assert config.mode == "both"
    assert config.batch_size == 20


def test_find_output_uses_file_index() -> None:
    result = {
        "files": [
            {
                "filename": "a.docx",
                "outputs": [
                    {"kind": "bilingual", "filename": "a_bi.docx", "file_index": 0, "object_key": "k0"},
                    {"kind": "translated", "filename": "a_zh.docx", "file_index": 1, "object_key": "k1"},
                ],
            }
        ]
    }
    located = find_output(result, 1)
    assert located is not None
    assert located["object_key"] == "k1"
    assert find_output(result, 9) is None
    assert find_output(None, 0) is None


async def test_run_job_produces_two_outputs(monkeypatch, tmp_path) -> None:
    """端到端编排：LLM 与 MinIO 全 mock，验证 both 模式产出两份并登记索引。"""
    import re

    from docx import Document

    from app.core import storage
    from app.modules.registration.docx_translator import service as service_module
    from app.modules.registration.docx_translator import translator as translator_module
    from app.modules.registration.docx_translator.config import TranslateConfig
    from app.modules.registration.docx_translator.glossary import Glossary
    from app.modules.registration.docx_translator.service import run_job

    class FakeLLM:
        async def chat(self, messages, **_kwargs):
            ids = re.findall(r"\[ID:([a-zA-Z0-9_]+)\]", messages[-1]["content"])
            return "\n".join(f"[ID:{uid}] 译文{uid}" for uid in ids)

    uploaded: list[tuple[str, str, int]] = []

    def fake_upload(module: str, key: str, data: bytes, length: int, content_type: str = "") -> str:
        uploaded.append((module, key, length))
        return key

    persisted: list[dict[str, object]] = []

    async def fake_persist(**kwargs: object) -> None:
        persisted.append(kwargs)

    async def fake_sources(*_args: object, **_kwargs: object) -> list[dict[str, object]]:
        return []

    async def fake_create_task(**_kwargs: object) -> None:
        return None

    async def fake_finish_task(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(translator_module, "llm_client", FakeLLM())
    monkeypatch.setattr(storage, "is_enabled", lambda: True)
    monkeypatch.setattr(storage, "upload_object", fake_upload)
    # 落库走独立会话（真实 DB），单测里替换掉，避免写脏开发库
    monkeypatch.setattr(service_module, "persist_file_records", fake_persist)
    monkeypatch.setattr(service_module, "upload_sources", fake_sources)
    monkeypatch.setattr(service_module, "create_task", fake_create_task)
    monkeypatch.setattr(service_module, "finish_task", fake_finish_task)

    source = tmp_path / "in.docx"
    doc = Document()
    doc.add_paragraph("Batch Production Record")
    doc.add_paragraph("Specifications")
    doc.save(source)

    job_id = "job-123"
    result = await run_job(
        job_id,
        [UploadedDoc("in.docx", source.read_bytes())],
        TranslateConfig(source_lang="en", target_lang="zh", mode="both", batch_size=10),
        Glossary(),
        90.0,
    )

    file_result = result["files"][0]
    assert file_result["success"] is True
    assert [item["kind"] for item in file_result["outputs"]] == ["bilingual", "translated"]
    assert [item["file_index"] for item in file_result["outputs"]] == [0, 1]
    assert len(uploaded) == 2
    assert uploaded[0][0] == "registration"
    assert uploaded[0][1].startswith("docx_translations/")
    assert job_id in uploaded[0][1]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("98.5%", False),
        ("mg", False),  # 单位白名单直接跳过
        ("3.2.1", False),
        ("—", False),
        ("/", False),
        ("3 batches", True),
        ("批生产记录", True),
        ("Specifications", True),
        ("   ", False),
    ],
)
def test_is_translatable(text: str, expected: bool) -> None:
    from app.modules.registration.docx_translator.service import is_translatable

    assert is_translatable(text) is expected
