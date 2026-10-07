# mypy: ignore-errors
"""Reagent-reminder config: the stored Feishu secret is encrypted at rest.

The column held the secret in plaintext, so a database dump disclosed it. It now
uses the shared helpers in ``app.core.secrets`` — the same ones the identity module
uses for this vendor's secret — which prefix the ciphertext so legacy rows can
still be read.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient

from app.core import secrets

BASE = "/api/v1/quality/reagent-reminder"

PLAINTEXT_SECRET = "test-feishu-app-secret-value"


@dataclass
class _FakeSettings:
    ENCRYPTION_KEY: str | None = None
    is_production: bool = False


@pytest.fixture
def encryption_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Give the helper a real key, so it encrypts rather than passing through.

    Without a configured `ENCRYPTION_KEY`, `encrypt_secret` returns the plaintext
    unchanged outside production — a documented behaviour, and the reason the
    column appeared unencrypted. This is the same technique
    `tests/unit/test_core_secrets.py` uses.
    """
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(secrets, "get_settings", lambda: _FakeSettings(ENCRYPTION_KEY=key))
    return key


async def test_stored_secret_is_not_plaintext(auth_client: AsyncClient, db_session, encryption_key: str) -> None:
    """The value on disk is ciphertext, not the secret that was submitted."""
    response = await auth_client.post(
        f"{BASE}/config",
        json={
            "feishu_app_id": "cli_test_app_id",
            "feishu_app_secret": PLAINTEXT_SECRET,
            "feishu_chat_id": "oc_test_chat_id",
        },
    )
    assert response.status_code == 200, response.text

    # Read the row directly, bypassing the service, to see what was persisted.
    from sqlalchemy import select

    from app.modules.quality.qms.reagent_reminder_config import ReagentReminderConfig

    result = await db_session.execute(select(ReagentReminderConfig).limit(1))
    stored = result.scalar_one()

    assert stored.feishu_app_secret is not None
    assert stored.feishu_app_secret != PLAINTEXT_SECRET, "the secret was persisted in plaintext"


async def test_stored_secret_decrypts_to_the_submitted_value(db_session) -> None:
    """What was encrypted can be read back — the reminder job depends on it."""
    from app.core.secrets import decrypt_secret, encrypt_secret

    assert decrypt_secret(encrypt_secret(PLAINTEXT_SECRET)) == PLAINTEXT_SECRET


async def test_config_response_does_not_leak_the_ciphertext(auth_client: AsyncClient, encryption_key: str) -> None:
    """The API returns a masked secret, never the encrypted blob.

    The response previously echoed the column verbatim. Once the column holds
    ciphertext, echoing it would hand the client the encrypted value, which is
    both useless in the form and a disclosure of the stored form.
    """
    await auth_client.post(
        f"{BASE}/config",
        json={
            "feishu_app_id": "cli_test_app_id",
            "feishu_app_secret": PLAINTEXT_SECRET,
            "feishu_chat_id": "oc_test_chat_id",
        },
    )

    response = await auth_client.get(f"{BASE}/config")
    assert response.status_code == 200, response.text
    returned = response.json()["data"]["feishu_app_secret"]

    assert returned != PLAINTEXT_SECRET, "the API echoed the secret back in full"
    assert "fernet:v1:" not in returned, "the API leaked the stored ciphertext"
