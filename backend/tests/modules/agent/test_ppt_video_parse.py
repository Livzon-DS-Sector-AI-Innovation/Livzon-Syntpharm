"""解析进度派生规则：有任务按任务走，老项目按产物回退，其余为「未解析」。"""

import uuid
from types import SimpleNamespace

from app.modules.agent import service
from app.modules.agent.models import JOB_STATUS_CANCELED, JOB_STATUS_FAILED, JOB_STATUS_RUNNING, JOB_STATUS_SUCCEEDED


def _project(slide_count: int = 0) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), slide_count=slide_count)


def _job(status: str, progress: int = 10, error: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=status,
        stage="parse",
        progress=progress,
        error_message=error,
    )


def test_parse_state_from_running_job() -> None:
    job = _job(JOB_STATUS_RUNNING, progress=42)

    state = service.parse_state(_project(slide_count=0), job, [])  # type: ignore[arg-type]

    assert state.status == "running"
    assert state.progress == 42
    assert state.job_id == job.id
    assert state.derived_from == "job"


def test_parse_state_failed_job_keeps_error() -> None:
    job = _job(JOB_STATUS_FAILED, progress=30, error="LibreOffice 转换失败")

    state = service.parse_state(_project(), job, [])  # type: ignore[arg-type]

    assert state.status == "failed"
    assert state.error_message == "LibreOffice 转换失败"


def test_parse_state_legacy_project_falls_back_to_succeeded() -> None:
    """迁移前的老项目没有 parse 任务，但已有逐页记录 → 视为已解析。"""
    state = service.parse_state(_project(slide_count=12), None, [])  # type: ignore[arg-type]

    assert state.status == "succeeded"
    assert state.progress == 100
    assert state.derived_from == "project_fallback"


def test_parse_state_never_parsed_project_is_none() -> None:
    state = service.parse_state(_project(slide_count=0), None, [])  # type: ignore[arg-type]

    assert state.status == "none"
    assert state.derived_from == "none"


def test_parse_state_canceled_job_is_none() -> None:
    job = _job(JOB_STATUS_CANCELED)

    state = service.parse_state(_project(slide_count=0), job, [])  # type: ignore[arg-type]

    assert state.status == "none"


def test_parse_state_succeeded_job() -> None:
    job = _job(JOB_STATUS_SUCCEEDED, progress=100)

    state = service.parse_state(_project(slide_count=8), job, [])  # type: ignore[arg-type]

    assert state.status == "succeeded"
    assert state.derived_from == "job"
