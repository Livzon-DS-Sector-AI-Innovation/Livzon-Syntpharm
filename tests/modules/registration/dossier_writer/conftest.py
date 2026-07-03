"""Dossier writer module test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_dossier_data():
    return {
        "product_name": "阿莫西林",
        "sterile_type": "无菌",
        "manufacturer": "某制药有限公司",
    }
