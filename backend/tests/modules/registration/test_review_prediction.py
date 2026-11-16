# mypy: ignore-errors
"""workday 工作日推算与 prediction 双轨预测引擎单元测试。"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.modules.registration.service.prediction import predict_drug
from app.modules.registration.service.workday import add_workdays, is_workday, workdays_between

# 2026-01-01 是周四；2026-01-02/03 为元旦假期，2026-01-04（周日）补班
HOLIDAYS = {date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)}
MAKEUPS = {date(2026, 1, 4)}


class TestWorkday:
    def test_is_workday_normal(self):
        assert is_workday(date(2026, 1, 5), HOLIDAYS, MAKEUPS) is True  # 周一

    def test_is_workday_weekend(self):
        assert is_workday(date(2026, 1, 10), HOLIDAYS, MAKEUPS) is False  # 周六

    def test_is_workday_holiday(self):
        assert is_workday(date(2026, 1, 1), HOLIDAYS, MAKEUPS) is False

    def test_is_workday_makeup_overrides_weekend(self):
        assert is_workday(date(2026, 1, 4), HOLIDAYS, MAKEUPS) is True  # 周日补班

    def test_add_workdays_skips_holidays(self):
        # 1/1（四）起 +1 工作日：1/2、1/3 假期、1/4 补班 → 1/4
        assert add_workdays(date(2026, 1, 1), 1, HOLIDAYS, MAKEUPS) == date(2026, 1, 4)

    def test_add_workdays_zero(self):
        assert add_workdays(date(2026, 1, 5), 0, HOLIDAYS, MAKEUPS) == date(2026, 1, 5)

    def test_workdays_between(self):
        # 1/5（一）→ 1/9（五）= 4 个工作日
        assert workdays_between(date(2026, 1, 5), date(2026, 1, 9), HOLIDAYS, MAKEUPS) == 4


def _make_drug(node_records: dict[int, tuple[date | None, bool]]):
    """构造 Drug mock：node_records = {index: (actual_date, skipped)}"""
    drug = MagicMock()
    drug.id = "00000000-0000-0000-0000-000000000001"
    drug.acceptance_date = date(2026, 1, 5)  # 周一
    nodes = []
    for idx, (actual, skipped) in node_records.items():
        n = MagicMock()
        n.node_index = idx
        n.actual_date = actual
        n.skipped = skipped
        nodes.append(n)
    drug.nodes = nodes
    return drug


@pytest.fixture
def mock_db():
    """mock DB：无节假日、无历史样本"""
    db = MagicMock()

    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    empty_result.all.return_value = []

    async def _execute(*args, **kwargs):
        return empty_result

    db.execute = _execute
    return db


class TestPrediction:
    @pytest.mark.asyncio
    async def test_no_nodes_predicts_from_acceptance(self, mock_db):
        drug = _make_drug({})
        result = await predict_drug(mock_db, drug)
        assert result.total_nodes == 10
        assert result.completed_nodes == 0
        assert result.current_node_index == 1
        # 节点1 配置 40 工作日，从受理日（周一，无节假日）起算 → 周一+40wd = 第8周周五
        assert result.nodes[0].estimated_date == add_workdays(drug.acceptance_date, 40, set(), set())
        assert result.estimated_approval_date is not None

    @pytest.mark.asyncio
    async def test_completed_node_shifts_anchor(self, mock_db):
        # 节点1 实际完成 2026-02-02（周一）
        drug = _make_drug({1: (date(2026, 2, 2), False)})
        result = await predict_drug(mock_db, drug)
        assert result.completed_nodes == 1
        assert result.current_node_index == 2
        # 节点2 预计从实际完成日起算，而非受理日
        assert result.nodes[1].estimated_date == add_workdays(date(2026, 2, 2), 20, set(), set())

    @pytest.mark.asyncio
    async def test_skipped_node_excluded_from_total_and_workdays(self, mock_db):
        drug = _make_drug({1: (date(2026, 2, 2), False), 2: (None, True)})
        result = await predict_drug(mock_db, drug)
        assert result.total_nodes == 9
        assert result.nodes[1].status == "skipped"
        assert result.nodes[1].estimated_date is None
        # 节点3 预测不累计节点2的 20 个工作日
        assert result.nodes[2].estimated_date == add_workdays(date(2026, 2, 2), 5, set(), set())

    @pytest.mark.asyncio
    async def test_delta_days_positive_when_late(self, mock_db):
        # 节点1 预计 = 受理日+40wd = 2026-03-02；实际 2026-03-09 → 延迟 7 天
        drug = _make_drug({1: (date(2026, 3, 9), False)})
        result = await predict_drug(mock_db, drug)
        node1 = result.nodes[0]
        assert node1.status == "completed"
        assert node1.delta_days is not None and node1.delta_days > 0

    @pytest.mark.asyncio
    async def test_all_completed_no_current(self, mock_db):
        nodes = {i: (date(2026, 2, 2), False) for i in range(1, 11)}
        drug = _make_drug(nodes)
        result = await predict_drug(mock_db, drug)
        assert result.current_node_index is None
        assert result.completed_nodes == 10
        assert result.estimated_approval_date == date(2026, 2, 2)
