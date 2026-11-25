# mypy: ignore-errors
"""workday 工作日推算、locate_stage 自动定位与 prediction 双轨预测引擎单元测试。"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.modules.registration.models.review import ReviewNode
from app.modules.registration.service.prediction import locate_stage, predict_drug
from app.modules.registration.service.workday import add_workdays, is_workday, workdays_between

# 2026-01-01 是周四；2026-01-02/03 为元旦假期，2026-01-04（周日）补班
HOLIDAYS = {date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)}
MAKEUPS = {date(2026, 1, 4)}

CONFIGS = ReviewNode.get_all()


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


def _node_records(spec: dict[int, tuple[date | None, bool]]) -> dict[int, MagicMock]:
    """构造 node_records = {index: node}，node 有 node_index/actual_date/skipped"""
    records: dict[int, MagicMock] = {}
    for idx, (actual, skipped) in spec.items():
        n = MagicMock()
        n.node_index = idx
        n.actual_date = actual
        n.skipped = skipped
        records[idx] = n
    return records


class TestLocateStage:
    def test_no_nodes_current_is_first_future_node(self):
        # 受理日 2026-01-05，today 2026-01-20 早于节点1预计 → 节点1 为当前
        nodes, summary, base = locate_stage(
            date(2026, 1, 5),
            {},
            CONFIGS,
            set(),
            set(),
            date(2026, 1, 20),
        )
        assert summary.current_node_index == 1
        assert nodes[0].status == "in_progress"
        assert all(n.status == "pending" for n in nodes[1:])
        assert summary.overdue_indexes == []
        assert base == date(2026, 1, 5)  # 当前节点推算起点 = 受理日

    def test_overdue_before_current(self):
        # 受理日 2026-01-05，today 2026-06-01，节点1~若干已过预测
        nodes, summary, _ = locate_stage(
            date(2026, 1, 5),
            {},
            CONFIGS,
            set(),
            set(),
            date(2026, 6, 1),
        )
        cur = summary.current_node_index
        assert cur is not None and cur > 1
        # 当前节点之前的未完成节点全部 overdue，当前 in_progress，之后 pending
        for n in nodes:
            if n.node_index < cur:
                assert n.status == "overdue"
            elif n.node_index == cur:
                assert n.status == "in_progress"
            else:
                assert n.status == "pending"
        assert summary.overdue_indexes == [i for i in range(1, cur)]

    def test_all_predicted_passed_last_is_current(self):
        # today 远晚于全部预测 → 最后一个节点为当前（超预测），其余 overdue
        nodes, summary, _ = locate_stage(
            date(2026, 1, 5),
            {},
            CONFIGS,
            set(),
            set(),
            date(2028, 1, 1),
        )
        assert summary.current_node_index == 10
        assert all(n.status == "overdue" for n in nodes[:9])
        assert nodes[9].status == "in_progress"

    def test_completed_shifts_anchor_and_location(self):
        # 节点1 实际 2026-02-02，节点2 应从其起算（后延）而非受理日
        records = _node_records({1: (date(2026, 2, 2), False)})
        nodes, summary, _ = locate_stage(
            date(2026, 1, 5),
            records,
            CONFIGS,
            set(),
            set(),
            date(2026, 2, 10),
        )
        assert nodes[1].estimated_date == add_workdays(date(2026, 2, 2), 20, set(), set())
        assert summary.current_node_index == 2
        assert nodes[0].status == "completed"
        assert nodes[1].status == "in_progress"

    def test_skipped_not_in_total_and_not_overdue(self):
        # 节点2 跳过：不计入分母，不产生逾期
        records = _node_records({1: (date(2026, 2, 2), False), 2: (None, True)})
        _, summary, _ = locate_stage(
            date(2026, 1, 5),
            records,
            CONFIGS,
            set(),
            set(),
            date(2026, 6, 1),
        )
        assert summary.total_nodes == 9
        assert 2 not in summary.overdue_indexes

    def test_approved_when_all_completed(self):
        records = _node_records({i: (date(2026, 2, 2), False) for i in range(1, 11)})
        _, summary, _ = locate_stage(
            date(2026, 1, 5),
            records,
            CONFIGS,
            set(),
            set(),
            date(2026, 3, 1),
        )
        assert summary.approved is True
        assert summary.completed_nodes == 10
        assert summary.current_node_index is None

    def test_approved_last_only_no_in_progress(self):
        # 只填最后节点（已获批），前面节点未填：不应再有「进行中」当前节点，避免闪动待填
        records = _node_records({10: (date(2027, 6, 15), False)})
        nodes, summary, _ = locate_stage(
            date(2026, 1, 5),
            records,
            CONFIGS,
            set(),
            set(),
            date(2028, 1, 1),
        )
        assert summary.approved is True
        assert summary.current_node_index is None
        assert nodes[9].status == "completed"
        # 前面 9 个节点预测均已过 → 全部 overdue，不应有 in_progress
        assert all(n.status == "overdue" for n in nodes[:9])
        assert all(n.status != "in_progress" for n in nodes)


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
    async def test_no_nodes_predicts_from_acceptance(self, mock_db):
        drug = _make_drug({})
        result = await predict_drug(mock_db, drug)
        assert result.total_nodes == 10
        assert result.completed_nodes == 0
        # 节点1 配置 40 工作日，从受理日（周一，无节假日）起算
        assert result.nodes[0].estimated_date == add_workdays(drug.acceptance_date, 40, set(), set())
        assert result.estimated_approval_date is not None

    async def test_completed_node_shifts_anchor(self, mock_db):
        # 节点1 实际完成 2026-02-02（周一）
        drug = _make_drug({1: (date(2026, 2, 2), False)})
        result = await predict_drug(mock_db, drug)
        assert result.completed_nodes == 1
        # 节点2 预计从实际完成日起算，而非受理日（后延）
        assert result.nodes[1].estimated_date == add_workdays(date(2026, 2, 2), 20, set(), set())

    async def test_skipped_node_excluded_from_total_and_workdays(self, mock_db):
        drug = _make_drug({1: (date(2026, 2, 2), False), 2: (None, True)})
        result = await predict_drug(mock_db, drug)
        assert result.total_nodes == 9
        assert result.nodes[1].status == "skipped"
        assert result.nodes[1].estimated_date is None
        # 节点3 预测不累计节点2的 20 个工作日
        assert result.nodes[2].estimated_date == add_workdays(date(2026, 2, 2), 5, set(), set())

    async def test_delta_days_positive_when_late(self, mock_db):
        # 节点1 预计 = 受理日+40wd；实际晚于预计 → 延迟
        drug = _make_drug({1: (date(2026, 3, 9), False)})
        result = await predict_drug(mock_db, drug)
        node1 = result.nodes[0]
        assert node1.status == "completed"
        assert node1.delta_days is not None and node1.delta_days > 0

    async def test_all_completed_no_current(self, mock_db):
        nodes = {i: (date(2026, 2, 2), False) for i in range(1, 11)}
        drug = _make_drug(nodes)
        result = await predict_drug(mock_db, drug)
        assert result.current_node_index is None
        assert result.completed_nodes == 10
        assert result.estimated_approval_date == date(2026, 2, 2)
