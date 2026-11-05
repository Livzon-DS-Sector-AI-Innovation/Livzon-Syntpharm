"""doc_gen 生成质量回归评测（golden set / 指标快照）。

用途：模型、提示词或流程改动后判断「生成质量是否退化」。**不重跑任务**，
直接对已完成任务的 job.stats 做指标聚合（填充率、需人工核对率、缺口补回数、
阶段耗时），与基线快照对比并输出差异——改提示词/换模型前先打基线，改完再对比。

用法::

    # 打基线
    uv run python scripts/test/doc_gen_eval.py --template tech_research_report --limit 10 \
        --save /tmp/docgen_baseline.json

    # 改动后对比（存在超容差差异时退出码为 1）
    uv run python scripts/test/doc_gen_eval.py --template tech_research_report --limit 10 \
        --baseline /tmp/docgen_baseline.json

前提：能连到目标库（沿用 .env / 环境变量配置），且所选任务已是 ``completed`` 终态。
样本量建议 ≥10：单任务抖动大，指标只在大样本上才可比。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# 允许脚本直接运行：把 backend 根目录加入 sys.path（脚本位于 backend/scripts/test/）
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_RATE_KEYS = ("fill_rate", "needs_verify_rate", "pending_rate", "conflict_rate")
_EXTRA_KEYS = ("refs_rescued", "probe_recovered", "table_rows_unverified", "gap_recovered")


def _ratio(part: int, total: int) -> float:
    return round(part / total, 4) if total else 0.0


def summarize_jobs(rows: list[Any]) -> dict[str, Any]:
    """把任务行聚合成可比对的指标快照（纯函数，便于单测与复用）。"""
    totals = {"jobs": len(rows), "slots": 0, "ok": 0, "needs_verify": 0, "pending": 0, "conflict": 0, "manual": 0}
    extras = {key: 0 for key in _EXTRA_KEYS}
    timings: dict[str, list[float]] = {}
    for row in rows:
        stats = row.stats or {}
        totals["slots"] += int(stats.get("total_slots") or 0)
        totals["ok"] += int(stats.get("substantive") or 0)
        totals["needs_verify"] += int(stats.get("needs_verify") or 0)
        totals["pending"] += int(stats.get("pending") or 0)
        totals["conflict"] += int(stats.get("conflicts") or 0)
        totals["manual"] += int(stats.get("manual") or 0)
        for key in _EXTRA_KEYS:
            extras[key] += int(stats.get(key) or 0)
        for name, seconds in (stats.get("timings") or {}).items():
            try:
                timings.setdefault(str(name), []).append(float(seconds))
            except (TypeError, ValueError):
                continue
    slots = totals["slots"]
    return {
        "jobs": totals["jobs"],
        "slots": slots,
        "fill_rate": _ratio(totals["ok"], slots),
        "needs_verify_rate": _ratio(totals["needs_verify"], slots),
        "pending_rate": _ratio(totals["pending"], slots),
        "conflict_rate": _ratio(totals["conflict"], slots),
        "manual_count": totals["manual"],
        **extras,
        "timings_avg": {name: round(sum(values) / len(values), 1) for name, values in sorted(timings.items())},
    }


def diff_snapshots(baseline: dict[str, Any], current: dict[str, Any], *, tolerance: float) -> list[str]:
    """对比两个快照，返回超过容差的差异描述（纯函数）。"""
    issues: list[str] = []
    for key in _RATE_KEYS:
        before = float(baseline.get(key) or 0.0)
        after = float(current.get(key) or 0.0)
        if abs(after - before) > tolerance:
            issues.append(f"{key}: {before:.3f} → {after:.3f}（变化 {after - before:+.3f}）")
    return issues


async def _load_jobs(template_code: str, limit: int) -> list[Any]:
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.modules.research.doc_gen.models import DocGenJob

    async with async_session_factory() as session:
        rows = (
            (
                await session.execute(
                    select(DocGenJob)
                    .where(
                        DocGenJob.template_code == template_code,
                        DocGenJob.is_deleted.is_(False),
                        DocGenJob.status == "completed",
                    )
                    .order_by(DocGenJob.created_at.desc())
                    .limit(max(1, limit))
                )
            )
            .scalars()
            .all()
        )
    return list(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="doc_gen 生成质量回归评测（指标快照与基线对比）")
    parser.add_argument("--template", required=True, help="模板 code，如 tech_research_report")
    parser.add_argument("--limit", type=int, default=10, help="取最近多少个已完成任务（建议 ≥10）")
    parser.add_argument("--baseline", help="基线 JSON 路径；给出则做对比")
    parser.add_argument("--save", help="把本次快照写到该路径（打基线时用）")
    parser.add_argument("--tolerance", type=float, default=0.05, help="指标容差（超过即报告差异）")
    args = parser.parse_args()

    rows = asyncio.run(_load_jobs(args.template, args.limit))
    snapshot = summarize_jobs(rows)
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))

    if args.save:
        Path(args.save).write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n快照已写入 {args.save}")

    if args.baseline:
        baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        issues = diff_snapshots(baseline, snapshot, tolerance=args.tolerance)
        if issues:
            print("\n与基线存在差异（超过容差）：")
            for item in issues:
                print(f"- {item}")
            return 1
        print("\n与基线一致（在容差内）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
