# mypy: ignore-errors
"""超管保底守卫：停用 / 删除前至少保留 2 名生效超管（TC-007）。"""

import uuid
from typing import Any

import pytest

from app.core.exceptions import ForbiddenException
from app.platform.permission import public_api


def _patch_super_ids(monkeypatch: pytest.MonkeyPatch, super_ids: list[uuid.UUID]) -> None:
    async def fake_list(db: Any) -> list[uuid.UUID]:
        return super_ids

    monkeypatch.setattr(public_api, "list_superuser_user_ids", fake_list)


async def test_disable_rejects_when_only_two_superadmins(monkeypatch: pytest.MonkeyPatch) -> None:
    super_ids = [uuid.uuid4(), uuid.uuid4()]
    _patch_super_ids(monkeypatch, super_ids)

    with pytest.raises(ForbiddenException, match="至少保留 2 名"):
        await public_api.assert_superadmin_disable_allowed(object(), super_ids[0])


async def test_disable_allows_when_three_superadmins(monkeypatch: pytest.MonkeyPatch) -> None:
    super_ids = [uuid.uuid4() for _ in range(3)]
    _patch_super_ids(monkeypatch, super_ids)

    await public_api.assert_superadmin_disable_allowed(object(), super_ids[0])


async def test_disable_allows_non_superadmin_target(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_super_ids(monkeypatch, [uuid.uuid4(), uuid.uuid4()])

    await public_api.assert_superadmin_disable_allowed(object(), uuid.uuid4())


async def test_removal_rejects_when_only_two_superadmins(monkeypatch: pytest.MonkeyPatch) -> None:
    super_ids = [uuid.uuid4(), uuid.uuid4()]
    _patch_super_ids(monkeypatch, super_ids)

    with pytest.raises(ForbiddenException, match="至少保留 2 名"):
        await public_api.assert_superadmin_removal_allowed(object(), super_ids[0])
