"""审评进度双轨预测引擎。

- 规则预测：从最近一个实际完成节点起，按工作日逐节点累计推算。
  未发生任何节点时从受理日起算；跳过节点不占工作日。
- 统计修正：基于库内历史品种各节点「实际耗时 / 配置工作日」的比率
  中位数，对规则预测做缩放，并给出 P25~P75 区间。
  历史样本不足（< MIN_SAMPLES）时退化为纯规则预测，区间为 None。
"""

import statistics
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.registration.models.drug import Drug, DrugNode, Holiday
from app.modules.registration.models.review import ReviewNode
from app.modules.registration.schemas.drug import DrugPredictionResponse, NodePrediction
from app.modules.registration.service.workday import add_workdays, workdays_between

MIN_SAMPLES = 2  # 历史统计修正的最小样本数


async def _load_calendar(db: AsyncSession) -> tuple[set[date], set[date]]:
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

    holidays, makeups = await _load_calendar(db)
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


async def predict_drug(db: AsyncSession, drug: Drug) -> DrugPredictionResponse:
    """生成药品的审评进度预测。"""
    holidays, makeups = await _load_calendar(db)
    ratios = await _historical_ratios(db, drug.id)
    configs = ReviewNode.get_all()

    node_records = {n.node_index: n for n in drug.nodes}
    today = date.today()

    # 最近一个实际完成节点（预测锚点）
    completed_indexes = sorted(
        idx for idx, n in node_records.items() if n.actual_date is not None
    )
    anchor_idx = completed_indexes[-1] if completed_indexes else None
    anchor_date = node_records[anchor_idx].actual_date if anchor_idx else drug.acceptance_date

    nodes_out: list[NodePrediction] = []
    cumulative_base = drug.acceptance_date  # 规则链从受理日起算；已完成节点用实际日期推进

    # 当前节点 = 第一个未完成且未跳过的节点
    current_node_index: int | None = None

    for cfg in configs:
        idx = cfg["index"]
        rec = node_records.get(idx)
        cfg_days: int = cfg["days"]

        if rec and rec.skipped:
            nodes_out.append(
                NodePrediction(
                    node_index=idx,
                    node_name=cfg["name"],
                    status="skipped",
                    actual_date=None,
                    estimated_date=None,
                    estimated_range=None,
                    delta_days=None,
                )
            )
            continue

        if rec and rec.actual_date is not None:
            # 已完成：累计基准移到实际日期，并计算与规则预计的偏差
            estimated = add_workdays(cumulative_base, cfg_days, holidays, makeups)
            delta = (rec.actual_date - estimated).days
            nodes_out.append(
                NodePrediction(
                    node_index=idx,
                    node_name=cfg["name"],
                    status="completed",
                    actual_date=rec.actual_date,
                    estimated_date=estimated,
                    estimated_range=None,
                    delta_days=delta,
                )
            )
            cumulative_base = rec.actual_date
            continue

        # 未发生节点：规则预测 + 统计修正
        if current_node_index is None:
            current_node_index = idx

        estimated = add_workdays(cumulative_base, cfg_days, holidays, makeups)

        estimated_range: tuple[date, date] | None = None
        samples = ratios.get(idx, [])
        if len(samples) >= MIN_SAMPLES:
            # 用历史比率 P25/P75 缩放配置工作日，推算区间
            p25 = statistics.quantiles(samples, n=4)[0]
            p75 = statistics.quantiles(samples, n=4)[2]
            low = add_workdays(cumulative_base, max(1, round(cfg_days * p25)), holidays, makeups)
            high = add_workdays(cumulative_base, round(cfg_days * p75), holidays, makeups)
            if low > high:
                low, high = high, low
            estimated_range = (low, high)

        status = "in_progress" if idx == current_node_index else "pending"
        nodes_out.append(
            NodePrediction(
                node_index=idx,
                node_name=cfg["name"],
                status=status,
                actual_date=None,
                estimated_date=estimated,
                estimated_range=estimated_range,
                delta_days=None,
            )
        )
        cumulative_base = estimated

    skipped_count = sum(1 for n in node_records.values() if n.skipped)
    total_nodes = len(configs) - skipped_count
    completed_count = len(completed_indexes)

    days_in_current: int | None = None
    if current_node_index is not None:
        days_in_current = (today - anchor_date).days

    estimated_approval: date | None = None
    for n in nodes_out:
        if n.node_index == configs[-1]["index"]:
            estimated_approval = n.actual_date or n.estimated_date

    return DrugPredictionResponse(
        drug_id=drug.id,
        total_nodes=total_nodes,
        completed_nodes=completed_count,
        current_node_index=current_node_index,
        days_in_current_node=days_in_current,
        estimated_approval_date=estimated_approval,
        nodes=nodes_out,
    )
