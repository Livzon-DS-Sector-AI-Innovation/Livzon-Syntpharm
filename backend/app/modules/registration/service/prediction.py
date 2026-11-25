"""审评进度双轨预测引擎。

- 规则预测：从最近一个实际完成节点起，按工作日逐节点累计推算。
  未发生任何节点时从受理日起算；跳过节点不占工作日。
- 统计修正：基于库内历史品种各节点「实际耗时 / 配置工作日」的比率
  中位数，对规则预测做缩放，并给出 P25~P75 区间。
  历史样本不足（< MIN_SAMPLES）时退化为纯规则预测，区间为 None。
- 当前阶段定位：手动优先 + 自动兜底。已填 actual_date 的节点按真实数据
  作为锚点；未填的节点用「今天」与 estimated_date 比对自动定位当前节点，
  预测日期已过但未填实际日期的节点标记为 overdue（逾期待确认）。
"""

import statistics
import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.registration.models.drug import Drug, DrugNode, Holiday
from app.modules.registration.models.review import ReviewNode
from app.modules.registration.schemas.drug import (
    DrugPredictionResponse,
    NodePrediction,
    NodeStageSummary,
)
from app.modules.registration.service.workday import add_workdays, workdays_between

MIN_SAMPLES = 2  # 历史统计修正的最小样本数


async def load_calendar(db: AsyncSession) -> tuple[set[date], set[date]]:
    """加载节假日与补班日集合。"""
    result = await db.execute(select(Holiday).where(Holiday.is_deleted == False))  # noqa: E712
    holidays: set[date] = set()
    makeups: set[date] = set()
    for row in result.scalars().all():
        if row.type == "makeup":
            makeups.add(row.date)
        else:
            holidays.add(row.date)
    return holidays, makeups


async def _historical_ratios(db: AsyncSession, exclude_drug_id: uuid.UUID) -> dict[int, list[float]]:
    """统计各节点历史「实际工作日耗时 / 配置工作日」比率。

    仅采用同品种内「前一完成节点 → 本节点」的连续完成样本，
    跳过节点不参与。
    """
    result = await db.execute(
        select(DrugNode, Drug.acceptance_date)
        .join(Drug, Drug.id == DrugNode.drug_id)
        .where(
            Drug.is_deleted == False,  # noqa: E712
            DrugNode.is_deleted == False,  # noqa: E712
            Drug.id != exclude_drug_id,
            DrugNode.actual_date.isnot(None),
            DrugNode.skipped == False,  # noqa: E712
        )
    )
    rows = result.all()
    by_drug: dict[uuid.UUID, dict[int, date]] = {}
    acceptance: dict[uuid.UUID, date] = {}
    for node, acc_date in rows:
        by_drug.setdefault(node.drug_id, {})[node.node_index] = node.actual_date
        acceptance[node.drug_id] = acc_date

    holidays, makeups = await load_calendar(db)
    ratios: dict[int, list[float]] = {}
    for drug_id, nodes in by_drug.items():
        for idx, actual in nodes.items():
            config = ReviewNode.get_by_index(idx)
            if not config or config["days"] <= 0:
                continue
            # 基准：节点1 从受理日起，其余从前一完成节点起（中间跳过节点不产生基准偏移）
            if idx == 1:
                base = acceptance[drug_id]
            else:
                prev_completed = max(
                    (i for i in nodes if i < idx),
                    default=None,
                )
                if prev_completed is None:
                    continue
                base = nodes[prev_completed]
            actual_wd = workdays_between(base, actual, holidays, makeups)
            if actual_wd <= 0:
                continue
            ratios.setdefault(idx, []).append(actual_wd / config["days"])
    return ratios


def locate_stage(
    acceptance_date: date,
    node_records: dict[int, DrugNode],
    configs: list[dict[str, Any]],
    holidays: set[date],
    makeups: set[date],
    today: date,
    ratios: dict[int, list[float]] | None = None,
) -> tuple[list[NodePrediction], NodeStageSummary, date | None]:
    """手动优先 + 自动兜底定位当前阶段。

    规则：
    1. 已填 actual_date 的节点 = completed，作为后续推算锚点（后延）。
    2. 已跳过节点 = skipped，不占工作日、不计入分母。
    3. 未完成节点从最近真实完成节点（或受理日）按工作日逐节点推算 estimated_date；
       第一个 estimated_date > today 的节点 = 当前节点 in_progress；
       其前面 estimated_date <= today 但未填实际日期的节点 = overdue（逾期待确认）。
    4. 所有未完成节点 estimated_date 均已过时，最后一个节点为当前节点（超预测）。

    返回 (节点预测列表, 阶段摘要, 当前节点推算起点)。
    """
    ratios = ratios or {}

    # 第一遍：计算每个节点的实际/预计日期，未完成节点先标 pending
    rows: list[dict[str, Any]] = []
    cumulative_base = acceptance_date
    for cfg in configs:
        idx: int = cfg["index"]
        name: str = cfg["name"]
        cfg_days: int = cfg["days"]
        rec = node_records.get(idx)

        if rec and rec.skipped:
            rows.append(
                {
                    "idx": idx,
                    "name": name,
                    "status": "skipped",
                    "actual": None,
                    "estimated": None,
                    "delta": None,
                    "base": None,
                }
            )
            continue

        if rec and rec.actual_date is not None:
            estimated = add_workdays(cumulative_base, cfg_days, holidays, makeups)
            delta = (rec.actual_date - estimated).days
            rows.append(
                {
                    "idx": idx,
                    "name": name,
                    "status": "completed",
                    "actual": rec.actual_date,
                    "estimated": estimated,
                    "delta": delta,
                    "base": cumulative_base,
                }
            )
            cumulative_base = rec.actual_date
            continue

        base = cumulative_base
        estimated = add_workdays(base, cfg_days, holidays, makeups)
        rows.append(
            {
                "idx": idx,
                "name": name,
                "status": "pending",
                "actual": None,
                "estimated": estimated,
                "delta": None,
                "base": base,
            }
        )
        cumulative_base = estimated

    # 判断是否已获批：最后一个节点已完成。此时品种已终结，不应再定位「进行中」当前节点，
    # 前面未填日期的节点只按「预测是否已过」标记 overdue/pending，避免已获批后仍闪动待填。
    last_index = configs[-1]["index"] if configs else None
    approved = any(r["idx"] == last_index and r["status"] == "completed" for r in rows)

    # 第二遍：定位 current / overdue / pending
    pending_rows = [r for r in rows if r["status"] == "pending"]
    current_idx: int | None = None
    if not approved and pending_rows:
        nxt = next((r for r in pending_rows if r["estimated"] is not None and r["estimated"] > today), None)
        current_idx = nxt["idx"] if nxt is not None else pending_rows[-1]["idx"]

    current_base: date | None = None
    for r in rows:
        if r["status"] != "pending":
            continue
        if not approved and r["idx"] == current_idx:
            r["status"] = "in_progress"
            current_base = r["base"]
        elif r["estimated"] is not None and r["estimated"] <= today:
            r["status"] = "overdue"

    # 第三遍：构造 NodePrediction，未完成节点补充历史统计区间
    nodes_out: list[NodePrediction] = []
    for r in rows:
        estimated_range: tuple[date, date] | None = None
        if r["status"] in ("pending", "in_progress", "overdue") and r["base"] is not None:
            cfg_days = next(c["days"] for c in configs if c["index"] == r["idx"])
            samples = ratios.get(r["idx"], [])
            if len(samples) >= MIN_SAMPLES:
                p25 = statistics.quantiles(samples, n=4)[0]
                p75 = statistics.quantiles(samples, n=4)[2]
                low = add_workdays(r["base"], max(1, round(cfg_days * p25)), holidays, makeups)
                high = add_workdays(r["base"], round(cfg_days * p75), holidays, makeups)
                if low > high:
                    low, high = high, low
                estimated_range = (low, high)

        nodes_out.append(
            NodePrediction(
                node_index=r["idx"],
                node_name=r["name"],
                status=r["status"],
                actual_date=r["actual"],
                estimated_date=r["estimated"],
                estimated_range=estimated_range,
                delta_days=r["delta"],
            )
        )

    # 阶段摘要
    skipped_count = sum(1 for r in rows if r["status"] == "skipped")
    completed_count = sum(1 for r in rows if r["status"] == "completed")
    total = len(configs) - skipped_count
    current_name = next((c["name"] for c in configs if c["index"] == current_idx), None)
    overdue_indexes = [r["idx"] for r in rows if r["status"] == "overdue"]

    summary = NodeStageSummary(
        current_node_index=current_idx,
        current_node_name=current_name,
        overdue_indexes=overdue_indexes,
        completed_nodes=completed_count,
        total_nodes=total,
        approved=approved,
    )
    return nodes_out, summary, current_base


def locate_stage_light(
    acceptance_date: date,
    node_records: dict[int, DrugNode],
    configs: list[dict[str, Any]],
    holidays: set[date],
    makeups: set[date],
    today: date,
) -> tuple[list[NodePrediction], NodeStageSummary, date | None]:
    """轻量定位（不含历史统计区间），用于列表批量场景。"""
    return locate_stage(acceptance_date, node_records, configs, holidays, makeups, today)


async def predict_drug(db: AsyncSession, drug: Drug) -> DrugPredictionResponse:
    """生成药品的审评进度预测。"""
    holidays, makeups = await load_calendar(db)
    ratios = await _historical_ratios(db, drug.id)
    configs = ReviewNode.get_all()
    node_records = {n.node_index: n for n in drug.nodes}
    today = date.today()

    nodes_out, summary, current_base = locate_stage(
        drug.acceptance_date,
        node_records,
        configs,
        holidays,
        makeups,
        today,
        ratios,
    )

    days_in_current: int | None = None
    if current_base is not None:
        days_in_current = (today - current_base).days

    estimated_approval: date | None = None
    last_index = configs[-1]["index"] if configs else None
    for n in nodes_out:
        if n.node_index == last_index:
            estimated_approval = n.actual_date or n.estimated_date

    return DrugPredictionResponse(
        drug_id=drug.id,
        total_nodes=summary.total_nodes,
        completed_nodes=summary.completed_nodes,
        current_node_index=summary.current_node_index,
        days_in_current_node=days_in_current,
        estimated_approval_date=estimated_approval,
        nodes=nodes_out,
    )
