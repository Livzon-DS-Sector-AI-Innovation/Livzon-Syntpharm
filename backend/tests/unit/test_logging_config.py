"""Tests for the structured logging configuration."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core.logging_config import get_logging_config, request_id_var, setup_logging
from app.shared.module_registry import BUSINESS_MODULES


@pytest.fixture
def restore_logging() -> Iterator[None]:
    """Restore global logging state after a test configures logging."""
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    original_loggers = set(logging.root.manager.loggerDict)
    request_id_token = request_id_var.set(request_id_var.get())

    yield

    request_id_var.reset(request_id_token)
    root.handlers[:] = original_handlers
    root.setLevel(original_level)
    for name in list(logging.root.manager.loggerDict):
        if name not in original_loggers:
            del logging.root.manager.loggerDict[name]


def test_short_module_names_prefer_the_specific_prefix() -> None:
    """The audit logger reports as "audit", not the broader "platform"."""
    from app.core.logging_config import _short_module_name

    assert _short_module_name("app.modules.registration.dossier_writer.asset_text_extractor") == "registration"
    assert _short_module_name("app.platform.audit.middleware") == "audit"
    assert _short_module_name("app.platform.identity.models") == "platform"


def test_every_business_module_gets_a_logger_configuration() -> None:
    """The module map is derived from the registry, not a hard-coded subset."""
    config = get_logging_config()

    for module in BUSINESS_MODULES:
        assert f"app.modules.{module.code}" in config["loggers"], module.code


def test_production_configures_one_file_handler_per_business_module() -> None:
    """Deployment writes per-module JSON log files."""
    config = get_logging_config(is_production=True, log_dir="logs")

    for module in BUSINESS_MODULES:
        handler = f"file_{module.code}"
        assert handler in config["handlers"], module.code
        assert handler in config["loggers"][f"app.modules.{module.code}"]["handlers"], module.code


def test_development_uses_the_console_only() -> None:
    """Local development keeps logs on the terminal."""
    config = get_logging_config(is_production=False)

    assert "file_registration" not in config["handlers"]
    assert config["loggers"]["app.modules.registration"]["handlers"] == ["console"]


def test_module_file_carries_the_request_id(tmp_path: Path, restore_logging: None) -> None:
    """A configured module log file holds the message and the request id."""
    setup_logging(is_production=True, log_dir=str(tmp_path), log_level="INFO")

    request_id_var.set("req-1234567890")
    logging.getLogger("app.modules.registration.dossier_writer.asset_text_extractor").error("boom")

    for handler in logging.getLogger("app.modules.registration").handlers:
        handler.flush()

    log_file = tmp_path / "registration.log"
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "boom" in content
    assert "req-1234567890" in content
