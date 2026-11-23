"""任务注册表：进度合并与状态查询。"""

from __future__ import annotations

import asyncio

import pytest

from app.core.exceptions import NotFoundException
from app.modules.registration.docx_translator.jobs import TranslationJobRegistry


async def _wait_done(registry: TranslationJobRegistry, job_id: str) -> None:
    for _ in range(200):
        state = await registry.state(job_id)
        if state.status != "running":
            return
        await asyncio.sleep(0.01)
    raise AssertionError("job did not finish")


async def test_registry_tracks_progress_and_result() -> None:
    registry = TranslationJobRegistry()

    async def runner(job_id: str) -> dict[str, object]:
        registry.update(job_id, current_file="a.docx")
        registry.update(job_id, files_done=1)
        return {
            "files": [
                {
                    "filename": "a.docx",
                    "success": True,
                    "outputs": [{"kind": "bilingual", "filename": "a_bi.docx", "file_index": 0}],
                    "translated_units": 3,
                    "total_units": 3,
                    "success_rate": 100.0,
                    "warnings": [],
                    "error": None,
                }
            ]
        }

    job_id = await registry.start("test-job", 1, runner)
    await _wait_done(registry, job_id)

    state = await registry.state(job_id)
    assert state.status == "done"
    assert state.files_done == 1
    assert state.files[0].success is True
    assert state.files[0].outputs[0].file_index == 0
    assert await registry.result(job_id) is not None


async def test_registry_marks_failed() -> None:
    registry = TranslationJobRegistry()

    async def runner(_job_id: str) -> dict[str, object] | None:
        raise RuntimeError("boom")

    job_id = await registry.start("test-job", 1, runner)
    await _wait_done(registry, job_id)
    state = await registry.state(job_id)
    assert state.status == "failed"
    assert state.error == "boom"


async def test_registry_unknown_job_raises_not_found() -> None:
    registry = TranslationJobRegistry()
    with pytest.raises(NotFoundException):
        await registry.state("missing")
