# mypy: ignore-errors
"""Instrument reminder config: the stored Feishu secret is encrypted at rest.

The second of two columns holding this vendor's secret in plaintext. The reagent
one was fixed first; this mirrors it, using the same shared helpers in
``app.core.secrets``.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient

from app.core import secrets

BASE = "/api/v1/quality/instrument/reminder-config"

PLAINTEXT_SECRET = "instrument-feishu-app-secret"


@dataclass
class _FakeSettings:
    ENCRYPTION_KEY: str | None = None
    is_production: bool = False


@pytest.fixture
def encryption_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Give the helper a real key, so it encrypts rather than passing through.

    Without one, `encrypt_secret` returns the plaintext unchanged outside
    production — which would make these assertions pass for the wrong reason.
    Same technique as `tests/unit/test_core_secrets.py`.
    """
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(secrets, "get_settings", lambda: _FakeSettings(ENCRYPTION_KEY=key))
    return key


def _payload() -> dict:
    return {
        "name": "仪器校准提醒测试",
        "feishu_app_id": "cli_instrument_app",
        "feishu_app_secret": PLAINTEXT_SECRET,
        "chat_id": "oc_instrument_chat",
    }


async def test_stored_secret_is_not_plaintext(auth_client: AsyncClient, db_session, encryption_key: str) -> None:
    """The value on disk is ciphertext, not the secret that was submitted."""
    response = await auth_client.post(BASE, json=_payload())
    assert response.status_code in (200, 201), response.text

    from sqlalchemy import select

    from app.modules.quality.qms.instrument_models import CalibrationReminderConfig

    result = await db_session.execute(select(CalibrationReminderConfig).limit(1))
    stored = result.scalar_one()

    assert stored.feishu_app_secret is not None
    assert stored.feishu_app_secret != PLAINTEXT_SECRET, "the secret was persisted in plaintext"


async def test_config_response_does_not_leak_the_ciphertext(auth_client: AsyncClient, encryption_key: str) -> None:
    """The API returns a masked secret, never the encrypted blob."""
    await auth_client.post(BASE, json=_payload())

    response = await auth_client.get(BASE)
    assert response.status_code == 200, response.text
    items = response.json()["data"]["items"]
    assert items, "no config returned"

    returned = items[0]["feishu_app_secret"]
    assert returned != PLAINTEXT_SECRET, "the API echoed the secret in full"
    assert "fernet:v1:" not in returned, "the API leaked the stored ciphertext"
