"""Quality module test fixtures."""

from __future__ import annotations

import uuid

import pytest


@pytest.fixture
def sample_deviation_data():
    uid = uuid.uuid4().hex[:8]
    return {
        "deviation_code": f"DEV-{uid}",
        "title": "工艺参数偏差",
        "description": "反应温度超出规定范围",
        "status": "draft",
    }


@pytest.fixture
def sample_capa_data():
    uid = uuid.uuid4().hex[:8]
    return {
        "capa_code": f"CAPA-{uid}",
        "title": "纠正措施：温度控制",
        "non_conformity_description": "实施温度监控改进措施",
        "category": "corrective",
        "status": "draft",
    }
