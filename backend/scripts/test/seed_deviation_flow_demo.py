"""偏差流程演示数据：补齐部门联系人 + 为 8 个待办节点各造一条台账。

背景：节点负责人由 ``quality.department_contacts`` 按**部门名精确匹配**解析，本地库里联系人只有
一条 ``101``（无任何人员），而台账部门是 ``101车间`` 等真实车间名，导致所有节点都显示
「未配置处理人」。本脚本：:

1. 把错名的 ``101`` 行改名成 ``101车间``（仅当该行人员字段全空时）；
2. 给台账出现过（以及造数要用）的部门补演示处理人——只补空缺字段，不覆盖已人工维护的值；
3. 为 AI 分析 / 偏差调查 / 部门负责人审核 / 跨部门负责人审核 / 所属QA审核 / QA负责人审核 /
   质量负责人审核 / 输入最终编号 各造一条 ``DEMO-`` 前缀台账，便于逐节点核对负责人。

处理人是**占位**：``identity.users`` 没有职务字段，平台也没有「部门负责人」角色可反查，
因此按部门挑一人填。真实上线前请业务在「部门联系人配置」页面按职务改。

用法::

    python scripts/test/seed_deviation_flow_demo.py --apply
    python scripts/test/seed_deviation_flow_demo.py --cleanup
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import select  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402
from app.modules.quality.qms.deviation_department_models import DepartmentContact  # noqa: E402
from app.modules.quality.qms.deviation_flow import STATUS_TO_STEP, build_flow_context, step_payloads  # noqa: E402
from app.modules.quality.qms.deviation_ledger_constants import LedgerStatus  # noqa: E402
from app.modules.quality.qms.deviation_ledger_models import DeviationLedger  # noqa: E402
from app.platform.identity.models import User  # noqa: E402

#: 历史上错建的部门名（无人员，直接用真实车间名替代）
LEGACY_DEPARTMENT = "101"
QA_DEPARTMENT = "质量保证部"

#: 每个部门都挂同一组 QA：qa_review 取本部门 qa_staff_ids[0]，
#: qa_head_review 取质量保证部 qa_staff_ids[1]，quality_head_review 取质量保证部 quality_head_id
QA_STAFF = ("何姗", "刘清清")

#: 演示联系人：部门 -> 部门负责人 / 质量负责人
CONTACT_SEED: dict[str, dict[str, str | None]] = {
    "101车间": {"dept_head": "刘小军", "quality_head": None},
    "102车间": {"dept_head": "何华松", "quality_head": None},
    "106车间": {"dept_head": "刘程稀", "quality_head": None},
    "302车间": {"dept_head": "何栢琅", "quality_head": None},
    "溶剂回收车间": {"dept_head": "刘中秋", "quality_head": None},
    "质量控制部": {"dept_head": "倪梓杏", "quality_head": None},
    QA_DEPARTMENT: {"dept_head": "宋世丘", "quality_head": "赵建汉"},
}

DEMO_PREFIX = "DEMO-"


async def _user_id(db: Any, department: str, name: str) -> uuid.UUID:
    """按 (部门, 姓名) 取用户 id，取不到直接报错（避免静默造出无处理人的数据）。"""
    user_id = await db.scalar(
        select(User.id).where(
            User.department == department,
            User.name == name,
            User.is_deleted.is_(False),
        )
    )
    if user_id is None:
        raise RuntimeError(f"用户不存在：{department} / {name}")
    return user_id


def _append(tokens: list[str] | None, token: str) -> list[str]:
    result = list(tokens or [])
    if token and token not in result:
        result.append(token)
    return result


async def seed_contacts(db: Any) -> dict[str, int]:
    """补联系人配置，返回统计。"""
    stats = {"dropped": 0, "created": 0, "filled": 0}
    cache: dict[str, DepartmentContact] = {}

    async def ensure(department: str) -> DepartmentContact:
        contact = cache.get(department)
        if contact is None:
            contact = (
                await db.execute(
                    select(DepartmentContact).where(
                        DepartmentContact.department == department,
                        DepartmentContact.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if contact is None:
                contact = DepartmentContact(
                    department=department,
                    qa_staff_ids=[],
                    gmp_staff_ids=[],
                    additional_contacts=[],
                )
                db.add(contact)
                stats["created"] += 1
            cache[department] = contact
        return contact

    # 1) 处理历史误建的 "101" 行：部门名不是任何真实部门，人员指向 QA 测试账号，直接软删（可恢复）
    legacy = (
        await db.execute(
            select(DepartmentContact).where(
                DepartmentContact.department == LEGACY_DEPARTMENT,
                DepartmentContact.is_deleted.is_(False),
            )
        )
    ).scalar_one_or_none()
    if legacy is not None:
        legacy.is_deleted = True
        stats["dropped"] += 1

    # 2) 逐部门补人员（只补空缺）
    for department, config in CONTACT_SEED.items():
        contact = await ensure(department)
        head_name = config.get("dept_head")
        if head_name and contact.dept_head_id is None:
            contact.dept_head_id = await _user_id(db, department, head_name)
            stats["filled"] += 1
        quality_name = config.get("quality_head")
        if quality_name and contact.quality_head_id is None:
            contact.quality_head_id = await _user_id(db, department, quality_name)
            stats["filled"] += 1
        if not contact.qa_staff_ids:
            qa_ids = [str(await _user_id(db, QA_DEPARTMENT, name)) for name in QA_STAFF]
            contact.qa_staff_ids = qa_ids
            stats["filled"] += 1
        if contact.gmp_staff_ids is None:
            contact.gmp_staff_ids = []
        if contact.additional_contacts is None:
            contact.additional_contacts = []

    return stats


def _demo_rows(ids: dict[str, uuid.UUID], now: datetime) -> list[dict[str, Any]]:
    """8 个待办节点各一条演示台账。"""

    def opinion(step: str, name: str, content: str, hours: int) -> dict[str, Any]:
        return {
            "step": step,
            "result": "approved",
            "author_id": str(ids[name]),
            "author_name": name,
            "content": content,
            "create_time": (now - timedelta(hours=hours)).isoformat(),
        }

    common: dict[str, Any] = {
        "affected_items": "演示物料（阿莫西林原料药）",
        "discovery_location": "演示车间操作间",
        "discoverer_id": ids["刘小军"],
        "reporter_id": ids["刘小军"],
        "created_by": ids["刘小军"],
        "updated_by": ids["刘小军"],
    }

    rows: list[dict[str, Any]] = [
        {
            "code": f"{DEMO_PREFIX}01",
            "title": "[演示] AI 智能分析环节",
            "department": "101车间",
            "discovery_date": now.date() - timedelta(days=0),
            "batch_number": "DEMO-AI-001",
            "description": "演示数据：验证 AI 智能分析环节的负责人展示（该环节不锁定处理人）。",
            "status": LedgerStatus.PENDING_AI_ANALYSIS.value,
            "status_updated_at": now - timedelta(hours=2),
            "review_opinions": [],
            "investigation_records": [],
        },
        {
            "code": f"{DEMO_PREFIX}02",
            "title": "[演示] 偏差调查环节",
            "department": "102车间",
            "discovery_date": now.date() - timedelta(days=1),
            "batch_number": "DEMO-INV-002",
            "description": "演示数据：验证偏差调查环节负责人取自台账调查人。",
            "status": LedgerStatus.PENDING_INVESTIGATION.value,
            "status_updated_at": now - timedelta(hours=26),
            "handler_ids": [ids["何华松"]],
            "review_opinions": [opinion("ai_analysis", "刘小军", "AI 分析已确认", 30)],
            "investigation_records": [],
        },
        {
            "code": f"{DEMO_PREFIX}03",
            "title": "[演示] 部门负责人审核环节",
            "department": "106车间",
            "discovery_date": now.date() - timedelta(days=12),
            "batch_number": "DEMO-DH-003",
            "description": "演示数据：验证部门负责人审核环节负责人取自本部门联系人；该条故意造超期。",
            "status": LedgerStatus.PENDING_DEPT_HEAD_REVIEW.value,
            "status_updated_at": now - timedelta(days=10),
            "reason_category": "人员",
            "deviation_level": "minor",
            "handler_ids": [ids["刘程稀"]],
            "review_opinions": [
                opinion("ai_analysis", "刘小军", "AI 分析已确认", 300),
                opinion("investigation", "刘程稀", "调查完成，转入部门负责人审核", 240),
            ],
            "investigation_records": [
                {
                    "content": "演示调查记录：现场复核批记录，操作参数超出工艺规程允许范围。",
                    "author_id": str(ids["刘程稀"]),
                    "author_name": "刘程稀",
                    "create_time": (now - timedelta(days=11)).isoformat(),
                }
            ],
            "report_content": "演示调查报告正文：直接原因、根本原因与纠正措施见下。",
        },
        {
            "code": f"{DEMO_PREFIX}04",
            "title": "[演示] 跨部门负责人审核环节",
            "department": "302车间",
            "discovery_date": now.date() - timedelta(days=2),
            "batch_number": "DEMO-CD-004",
            "description": "演示数据：验证跨部门负责人审核环节负责人取自跨部门联系人。",
            "status": LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW.value,
            "status_updated_at": now - timedelta(hours=8),
            "reason_category": "设施设备",
            "deviation_level": "moderate",
            "needs_cross_dept_review": True,
            "cross_dept_reviewers": [
                {"department": "101车间", "investigators": [str(ids["刘小军"])]},
            ],
            "handler_ids": [ids["何栢琅"]],
            "review_opinions": [
                opinion("ai_analysis", "刘小军", "AI 分析已确认", 40),
                opinion("investigation", "何栢琅", "调查完成", 20),
                opinion("dept_head_review", "何栢琅", "本部门审核通过", 12),
            ],
            "investigation_records": [],
        },
        {
            "code": f"{DEMO_PREFIX}05",
            "title": "[演示] 所属 QA 审核环节",
            "department": "质量控制部",
            "discovery_date": now.date() - timedelta(days=3),
            "batch_number": "DEMO-QA-005",
            "description": "演示数据：验证所属 QA 审核环节负责人取自部门联系人的 QA 人员第一位。",
            "status": LedgerStatus.PENDING_QA_REVIEW.value,
            "status_updated_at": now - timedelta(hours=5),
            "reason_category": "文件",
            "deviation_level": "minor",
            "handler_ids": [ids["倪梓杏"]],
            "review_opinions": [
                opinion("ai_analysis", "刘小军", "AI 分析已确认", 60),
                opinion("investigation", "倪梓杏", "调查完成", 30),
                opinion("dept_head_review", "倪梓杏", "部门审核通过", 10),
            ],
            "investigation_records": [],
        },
        {
            "code": f"{DEMO_PREFIX}06",
            "title": "[演示] QA 负责人审核环节",
            "department": "101车间",
            "discovery_date": now.date() - timedelta(days=4),
            "batch_number": "DEMO-QH-006",
            "description": "演示数据：验证 QA 负责人审核环节负责人取自质量保证部 QA 人员第二位。",
            "status": LedgerStatus.PENDING_QA_HEAD_REVIEW.value,
            "status_updated_at": now - timedelta(hours=3),
            "reason_category": "环境",
            "deviation_level": "moderate",
            "handler_ids": [ids["刘小军"]],
            "review_opinions": [
                opinion("ai_analysis", "刘小军", "AI 分析已确认", 80),
                opinion("investigation", "刘小军", "调查完成", 50),
                opinion("dept_head_review", "刘小军", "部门审核通过", 20),
                opinion("qa_review", "何姗", "QA 审核通过", 6),
            ],
            "investigation_records": [],
        },
        {
            "code": f"{DEMO_PREFIX}07",
            "title": "[演示] 质量负责人审核环节",
            "department": "302车间",
            "discovery_date": now.date() - timedelta(days=5),
            "batch_number": "DEMO-QM-007",
            "description": "演示数据：验证质量负责人审核环节负责人取自质量保证部质量负责人。",
            "status": LedgerStatus.PENDING_QUALITY_HEAD_REVIEW.value,
            "status_updated_at": now - timedelta(hours=4),
            "reason_category": "产品物料",
            "deviation_level": "major",
            "handler_ids": [ids["何栢琅"]],
            "review_opinions": [
                opinion("ai_analysis", "刘小军", "AI 分析已确认", 100),
                opinion("investigation", "何栢琅", "调查完成", 70),
                opinion("dept_head_review", "何栢琅", "部门审核通过", 30),
                opinion("qa_review", "何姗", "QA 审核通过", 12),
                opinion("qa_head_review", "刘清清", "QA 负责人审核通过", 6),
            ],
            "investigation_records": [],
        },
        {
            "code": f"{DEMO_PREFIX}08",
            "title": "[演示] 输入最终编号环节",
            "department": "106车间",
            "discovery_date": now.date() - timedelta(days=6),
            "batch_number": "DEMO-FC-008",
            "description": "演示数据：验证输入最终编号环节负责人取所属 QA。",
            "status": LedgerStatus.PENDING_FINAL_CODE.value,
            "status_updated_at": now - timedelta(hours=30),
            "reason_category": "其它",
            "deviation_level": "minor",
            "handler_ids": [ids["刘程稀"]],
            "review_opinions": [
                opinion("ai_analysis", "刘小军", "AI 分析已确认", 120),
                opinion("investigation", "刘程稀", "调查完成", 80),
                opinion("dept_head_review", "刘程稀", "部门审核通过", 40),
                opinion("qa_review", "何姗", "QA 审核通过", 20),
                opinion("qa_head_review", "刘清清", "QA 负责人审核通过", 12),
                opinion("quality_head_review", "赵建汉", "质量负责人审核通过", 6),
            ],
            "investigation_records": [],
        },
    ]

    return [
        {
            **common,
            **row,
            "discovery_time": "09:30",
            "final_code": None,
            "attachments": [],
            "report_versions": [],
        }
        for row in rows
    ]


async def seed_demo_ledgers(db: Any) -> dict[str, int]:
    """按 code 幂等写入 8 条演示台账。"""
    ids: dict[str, uuid.UUID] = {
        "刘小军": await _user_id(db, "101车间", "刘小军"),
        "何华松": await _user_id(db, "102车间", "何华松"),
        "刘程稀": await _user_id(db, "106车间", "刘程稀"),
        "何栢琅": await _user_id(db, "302车间", "何栢琅"),
        "倪梓杏": await _user_id(db, "质量控制部", "倪梓杏"),
        "何姗": await _user_id(db, QA_DEPARTMENT, "何姗"),
        "刘清清": await _user_id(db, QA_DEPARTMENT, "刘清清"),
        "赵建汉": await _user_id(db, QA_DEPARTMENT, "赵建汉"),
        "宋世丘": await _user_id(db, QA_DEPARTMENT, "宋世丘"),
    }

    stats = {"created": 0, "updated": 0}
    for row in _demo_rows(ids, datetime.now(UTC)):
        existing = (
            await db.execute(select(DeviationLedger).where(DeviationLedger.code == row["code"]))
        ).scalar_one_or_none()
        if existing is None:
            db.add(DeviationLedger(**row))
            stats["created"] += 1
        else:
            for key, value in row.items():
                setattr(existing, key, value)
            existing.is_deleted = False
            stats["updated"] += 1
    return stats


async def cleanup(db: Any) -> int:
    rows = (
        (await db.execute(select(DeviationLedger).where(DeviationLedger.code.like(f"{DEMO_PREFIX}%")))).scalars().all()
    )
    for row in rows:
        row.is_deleted = True
    return len(rows)


async def report(db: Any) -> None:
    """回读：打印每个待办节点解析到的负责人，作为脚本自检。"""
    rows = (
        (
            await db.execute(
                select(DeviationLedger)
                .where(DeviationLedger.code.like(f"{DEMO_PREFIX}%"), DeviationLedger.is_deleted.is_(False))
                .order_by(DeviationLedger.code)
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        context = await build_flow_context(db, row)
        payloads = {item["step"]: item for item in step_payloads(context, row)}
        step = STATUS_TO_STEP.get(row.status or "")
        current = payloads.get(step or "") or {}
        names = [handler["name"] for handler in current.get("handlers", [])]
        print(f"{row.code} {row.department:<8} {row.status:<32} 当前环节负责人：{'、'.join(names) or '（无）'}")


async def main() -> None:
    mode = "apply" if "--apply" in sys.argv else "cleanup" if "--cleanup" in sys.argv else "dry-run"
    async with async_session_factory() as db:
        if mode == "cleanup":
            count = await cleanup(db)
            await db.commit()
            print(f"已软删除演示台账 {count} 条")
            return
        contact_stats = await seed_contacts(db)
        ledger_stats = await seed_demo_ledgers(db)
        suffix = "" if mode == "apply" else "（dry-run，未提交）"
        print(
            f"部门联系人：清理误建 {contact_stats['dropped']} 条，新建 {contact_stats['created']} 条，"
            f"补字段 {contact_stats['filled']} 处{suffix}"
        )
        print(f"演示台账：新增 {ledger_stats['created']} 条，更新 {ledger_stats['updated']} 条{suffix}")
        # 先回读（同一 session 内 flush 后可见），再决定提交或回滚
        await report(db)
        if mode == "apply":
            await db.commit()
        else:
            await db.rollback()


if __name__ == "__main__":
    asyncio.run(main())
