#!/usr/bin/env python3
"""偏差台账流程 API 端到端审核测试（无跨部门 / 有跨部门 / 关键分支）。

设计要点：

- 以各环节**真实处理人**身份调 ``/api/v1/quality/deviation/ledger/*``，因此能同时验证
  权限校验、状态机、处理人解析与跨部门逐行审核，而不是只验证 service 层。
- 处理人来自 ``quality.department_contacts``。脚本临时建一个测试部门
  ``E2E偏差测试部门``（四个角色分别指向不同用户），跑完删除，避免污染真实部门配置。
- 本地库默认没有任何用户持有 ``quality:deviation:*``，脚本临时建角色并授权，跑完回收。
- 不触发飞书通知：``core.module_settings`` 的 ``quality-deviation/NOTIFY`` 保持为空。
- 不调用 AI 分析异步任务：``submit_investigation`` 会隐式确认 AI 分析环节。

用法（仓库根目录）::

    docker cp backend/scripts/test/deviation_flow_e2e.py \\
        erp-backend:/app/scripts/test/deviation_flow_e2e.py
    docker exec erp-backend .venv/bin/python scripts/test/deviation_flow_e2e.py \\
        --base-url http://localhost:8000 --scenario all

    # 保留本次台账，便于人工登录复核
    docker exec erp-backend .venv/bin/python scripts/test/deviation_flow_e2e.py --keep

    # 跑完把报告拷回宿主
    docker cp erp-backend:/app/scripts/test/reports/. backend/scripts/test/reports/
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import httpx  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402
from app.modules.quality.qms.deviation_department_models import DepartmentContact  # noqa: E402
from app.modules.quality.qms.deviation_ledger_models import DeviationLedger  # noqa: E402
from app.platform.identity.models import User  # noqa: E402
from app.platform.identity.service import generate_jwt  # noqa: E402
from app.platform.permission.cache import evict_user_permission_cache  # noqa: E402
from app.platform.permission.models import Role, RolePermission, UserRoleGrant  # noqa: E402

API_PREFIX = "/api/v1/quality/deviation/ledger"

#: 测试专用部门（脚本创建，脚本删除）
TEST_DEPARTMENT = "E2E偏差测试部门"
#: 跨部门场景的两行：101车间（行内调查人 + 行内负责人）、102车间（仅负责人）
CROSS_ROW_WITH_INVESTIGATION = "101车间"
CROSS_ROW_HEAD_ONLY = "102车间"
#: 角色/人员配置参考部门
REFERENCE_DEPARTMENT = "101车间"
QA_DEPARTMENT = "质量保证部"

ROLE_CODE = "e2e-deviation-flow-audit"
ROLE_NAME = "E2E 偏差流程审核测试（临时）"
PERMISSION_CODES: tuple[str, ...] = (
    "quality:deviation:read",
    "quality:deviation:create",
    "quality:deviation:submit",
    "quality:deviation:update",
    "quality:deviation:approve",
)

REPORT_DIR = Path(__file__).resolve().parent / "reports"


class AbortScenarioError(RuntimeError):
    """主链路断言失败时中止当前场景，避免后续用例连环失败。"""


@dataclass
class Actor:
    key: str
    role: str
    id: uuid.UUID
    name: str
    department: str | None
    token: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "role": self.role,
            "name": self.name,
            "department": self.department,
            "user_id": str(self.id),
        }


@dataclass
class CaseResult:
    case_id: str
    scenario: str
    step: str
    actor: str
    action: str
    expected: dict[str, Any]
    actual: dict[str, Any]
    passed: bool
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "scenario": self.scenario,
            "step": self.step,
            "actor": self.actor,
            "action": self.action,
            "expected": self.expected,
            "actual": self.actual,
            "passed": self.passed,
            "evidence": self.evidence,
        }


class Recorder:
    """用例记录与断言。"""

    def __init__(self) -> None:
        self.cases: list[CaseResult] = []
        self.notes: list[str] = []

    def check(
        self,
        *,
        case_id: str,
        scenario: str,
        step: str,
        actor: Actor | None,
        action: str,
        expected: dict[str, Any],
        actual: dict[str, Any],
        evidence: dict[str, Any] | None = None,
    ) -> bool:
        passed = all(actual.get(key) == value for key, value in expected.items())
        self.cases.append(
            CaseResult(
                case_id=case_id,
                scenario=scenario,
                step=step,
                actor=(actor.name if actor else "system"),
                action=action,
                expected=expected,
                actual=actual,
                passed=passed,
                evidence=evidence or {},
            )
        )
        mark = "PASS" if passed else "FAIL"
        print(f"[{case_id}] {mark} {step} / {action} / {actor.name if actor else '-'}")
        if not passed:
            print(f"    expected={expected}")
            print(f"    actual  ={actual}")
        return passed

    def require(self, case_id: str, passed: bool, detail: str) -> None:
        if not passed:
            raise AbortScenarioError(f"{case_id} 断言失败：{detail}")

    @property
    def failed(self) -> list[CaseResult]:
        return [case for case in self.cases if not case.passed]


class Api:
    """极简 API 客户端：每次请求带指定用户 JWT。"""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def call(
        self,
        actor: Actor,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        url = f"{self.base_url}{API_PREFIX}{path}"
        headers = {"Authorization": f"Bearer {actor.token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, json=payload, headers=headers)
        try:
            body: dict[str, Any] = response.json()
        except ValueError:
            body = {"raw": response.text[:500]}
        return response.status_code, body


def _detail(body: dict[str, Any]) -> dict[str, Any]:
    data = body.get("data")
    return data if isinstance(data, dict) else {}


def _step_handlers(detail: dict[str, Any], step: str) -> list[str]:
    for item in detail.get("steps") or []:
        if item.get("step") == step:
            return [str(person.get("name") or "") for person in item.get("handlers") or []]
    return []


def _step_payload(detail: dict[str, Any], step: str) -> dict[str, Any]:
    for item in detail.get("steps") or []:
        if item.get("step") == step:
            return item
    return {}


def _sub_item(detail: dict[str, Any], department: str) -> dict[str, Any]:
    for item in _step_payload(detail, "cross_dept_head_review").get("sub_items") or []:
        if item.get("department") == department:
            return item
    return {}


def _message(body: dict[str, Any]) -> str:
    return str(body.get("message") or "")


def _opinion_count(detail: dict[str, Any]) -> int:
    return len(detail.get("review_opinions") or [])


def _core_state(detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": detail.get("status"),
        "current_step": detail.get("current_step"),
        "opinions": _opinion_count(detail),
    }


class FlowAudit:
    """流程编排与断言。"""

    def __init__(self, api: Api, recorder: Recorder, actors: dict[str, Actor]) -> None:
        self.api = api
        self.recorder = recorder
        self.actors = actors
        self.ledger_ids: list[uuid.UUID] = []

    # ── 场景 A：无跨部门 ────────────────────────────────────────────────
    async def run_no_cross_dept(self) -> dict[str, Any]:
        scenario = "no_cross_dept"
        reporter = self.actors["reporter"]
        dept_head = self.actors["dept_head"]
        qa = self.actors["qa"]
        qa_head = self.actors["qa_head"]
        quality_head = self.actors["quality_head"]
        outsider = self.actors["row_head_b"]

        # A-01 创建
        status, body = await self.api.call(
            reporter,
            "POST",
            "",
            {
                "title": "E2E 无跨部门偏差流程审核测试",
                "department": TEST_DEPARTMENT,
                "discovery_date": date.today().isoformat(),
                "discovery_time": "09:30",
                "discovery_location": "E2E 测试车间",
                "affected_items": "E2E 测试物料",
                "batch_number": "E2E-BATCH-001",
                "handler_ids": [str(reporter.id)],
                "description": "用于验证无跨部门偏差主链路是否跑通，跑完自动清理。",
            },
        )
        detail = _detail(body)
        ledger_id = detail.get("id")
        passed = self.recorder.check(
            case_id="A-01",
            scenario=scenario,
            step="create",
            actor=reporter,
            action="新建偏差（无跨部门）",
            expected={
                "http": 200,
                "status": "pending_ai_analysis",
                "current_step": "ai_analysis",
                "investigation.handlers": [reporter.name],
            },
            actual={
                "http": status,
                "status": detail.get("status"),
                "current_step": detail.get("current_step"),
                "investigation.handlers": _step_handlers(detail, "investigation"),
            },
            evidence={"code": detail.get("code"), "message": _message(body)},
        )
        self.recorder.require("A-01", passed and bool(ledger_id), "创建失败，无法继续场景 A")
        self.ledger_ids.append(uuid.UUID(str(ledger_id)))

        # A-02 越权：非调查人提交调查
        status, body = await self.api.call(outsider, "POST", f"/{ledger_id}/investigation", self._investigation())
        self.recorder.check(
            case_id="A-02",
            scenario=scenario,
            step="investigation",
            actor=outsider,
            action="越权提交调查（非调查人）",
            expected={"http": 403, "message_contains": "无权操作"},
            actual={"http": status, "message_contains": _message(body)},
            evidence={"message": _message(body)},
        )

        # A-03 调查人提交调查（隐式确认 AI 分析）
        status, body = await self.api.call(reporter, "POST", f"/{ledger_id}/investigation", self._investigation())
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="A-03",
            scenario=scenario,
            step="investigation",
            actor=reporter,
            action="提交调查（含 AI 分析隐式确认）",
            expected={
                "http": 200,
                "status": "pending_dept_head_review",
                "current_step": "dept_head_review",
                "records": 1,
                "opinions": 2,
                "dept_head.handlers": [dept_head.name],
            },
            actual={
                "http": status,
                "status": detail.get("status"),
                "current_step": detail.get("current_step"),
                "records": len(detail.get("investigation_records") or []),
                "opinions": _opinion_count(detail),
                "dept_head.handlers": _step_handlers(detail, "dept_head_review"),
            },
            evidence={"previous_status": "pending_ai_analysis", "next_status": detail.get("status")},
        )
        self.recorder.require("A-03", passed, "调查提交后未进入部门负责人审核")

        # A-04 越权：所属 QA 抢部门负责人审核
        status, body = await self.api.call(
            qa, "POST", f"/{ledger_id}/review", {"result": "approved", "content": "越权尝试"}
        )
        self.recorder.check(
            case_id="A-04",
            scenario=scenario,
            step="dept_head_review",
            actor=qa,
            action="越权审核（非部门负责人）",
            expected={"http": 403, "message_contains": "无权操作"},
            actual={"http": status, "message_contains": _message(body)},
            evidence={"message": _message(body)},
        )

        # A-05 部门负责人通过 → 进入所属 QA 审核
        status, body = await self.api.call(
            dept_head, "POST", f"/{ledger_id}/review", {"result": "approved", "content": "部门负责人审核通过"}
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="A-05",
            scenario=scenario,
            step="dept_head_review",
            actor=dept_head,
            action="部门负责人审核通过",
            expected={
                "http": 200,
                "status": "pending_qa_review",
                "current_step": "qa_review",
                "qa.handlers": [qa.name],
            },
            actual={
                "http": status,
                "status": detail.get("status"),
                "current_step": detail.get("current_step"),
                "qa.handlers": _step_handlers(detail, "qa_review"),
            },
            evidence={"previous_status": "pending_dept_head_review", "next_status": detail.get("status")},
        )
        self.recorder.require("A-05", passed, "部门负责人通过后未进入所属 QA 审核")

        # A-06 必填校验：QA 审核缺原因分类
        status, body = await self.api.call(
            qa, "POST", f"/{ledger_id}/review", {"result": "approved", "content": "缺少原因分类"}
        )
        self.recorder.check(
            case_id="A-06",
            scenario=scenario,
            step="qa_review",
            actor=qa,
            action="QA 审核未填原因分类",
            expected={"http": 400, "message_contains": "请先选择原因分类"},
            actual={"http": status, "message_contains": _message(body)},
            evidence={"message": _message(body)},
        )

        # A-07 QA 通过（带原因分类）
        status, body = await self.api.call(
            qa,
            "POST",
            f"/{ledger_id}/review",
            {"result": "approved", "content": "QA 审核通过", "reason_category": "人员"},
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="A-07",
            scenario=scenario,
            step="qa_review",
            actor=qa,
            action="QA 审核通过并填写原因分类",
            expected={
                "http": 200,
                "status": "pending_qa_head_review",
                "current_step": "qa_head_review",
                "reason_category": "人员",
                "qa_head.handlers": [qa_head.name],
            },
            actual={
                "http": status,
                "status": detail.get("status"),
                "current_step": detail.get("current_step"),
                "reason_category": detail.get("reason_category"),
                "qa_head.handlers": _step_handlers(detail, "qa_head_review"),
            },
            evidence={"previous_status": "pending_qa_review", "next_status": detail.get("status")},
        )
        self.recorder.require("A-07", passed, "QA 审核通过后未进入 QA 负责人审核")

        # A-08 必填校验：QA 负责人缺偏差分级
        status, body = await self.api.call(
            qa_head, "POST", f"/{ledger_id}/review", {"result": "approved", "content": "缺少偏差分级"}
        )
        self.recorder.check(
            case_id="A-08",
            scenario=scenario,
            step="qa_head_review",
            actor=qa_head,
            action="QA 负责人审核未填偏差分级",
            expected={"http": 400, "message_contains": "请先完成偏差分级"},
            actual={"http": status, "message_contains": _message(body)},
            evidence={"message": _message(body)},
        )

        # A-09 QA 负责人通过（带偏差分级）
        status, body = await self.api.call(
            qa_head,
            "POST",
            f"/{ledger_id}/review",
            {"result": "approved", "content": "QA 负责人审核通过", "deviation_level": "minor"},
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="A-09",
            scenario=scenario,
            step="qa_head_review",
            actor=qa_head,
            action="QA 负责人审核通过并填写偏差分级",
            expected={
                "http": 200,
                "status": "pending_quality_head_review",
                "current_step": "quality_head_review",
                "deviation_level": "minor",
                "quality_head.handlers": [quality_head.name],
            },
            actual={
                "http": status,
                "status": detail.get("status"),
                "current_step": detail.get("current_step"),
                "deviation_level": detail.get("deviation_level"),
                "quality_head.handlers": _step_handlers(detail, "quality_head_review"),
            },
            evidence={"previous_status": "pending_qa_head_review", "next_status": detail.get("status")},
        )
        self.recorder.require("A-09", passed, "QA 负责人通过后未进入质量负责人审核")

        # A-10 质量负责人退回
        status, body = await self.api.call(
            quality_head,
            "POST",
            f"/{ledger_id}/review",
            {"result": "rejected", "content": "E2E 分支验证：退回上一环节补充材料"},
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="A-10",
            scenario=scenario,
            step="quality_head_review",
            actor=quality_head,
            action="质量负责人审核退回",
            expected={
                "http": 200,
                "status": "returned",
                "current_step": "qa_head_review",
                "returned_step": "qa_head_review",
            },
            actual={
                "http": status,
                "status": detail.get("status"),
                "current_step": detail.get("current_step"),
                "returned_step": detail.get("returned_step"),
            },
            evidence={"previous_status": "pending_quality_head_review", "next_status": detail.get("status")},
        )
        self.recorder.require("A-10", passed, "退回失败，无法验证退回重提分支")

        # A-11 重新提交
        status, body = await self.api.call(
            reporter, "POST", f"/{ledger_id}/resubmit", {"content": "E2E 分支验证：补充材料后重新提交"}
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="A-11",
            scenario=scenario,
            step="resubmit",
            actor=reporter,
            action="退回后重新提交",
            expected={
                "http": 200,
                "status": "pending_qa_head_review",
                "current_step": "qa_head_review",
                "returned_step": None,
            },
            actual={
                "http": status,
                "status": detail.get("status"),
                "current_step": detail.get("current_step"),
                "returned_step": detail.get("returned_step"),
            },
            evidence={"previous_status": "returned", "next_status": detail.get("status")},
        )
        self.recorder.require("A-11", passed, "退回后重新提交失败")

        # A-12 QA 负责人再次通过
        status, body = await self.api.call(
            qa_head,
            "POST",
            f"/{ledger_id}/review",
            {"result": "approved", "content": "重新提交后审核通过"},
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="A-12",
            scenario=scenario,
            step="qa_head_review",
            actor=qa_head,
            action="重提后 QA 负责人再次通过",
            expected={"http": 200, "status": "pending_quality_head_review"},
            actual={"http": status, "status": detail.get("status")},
            evidence={"previous_status": "pending_qa_head_review", "next_status": detail.get("status")},
        )
        self.recorder.require("A-12", passed, "重提后 QA 负责人审核未推进")

        # A-13 质量负责人通过
        status, body = await self.api.call(
            quality_head, "POST", f"/{ledger_id}/review", {"result": "approved", "content": "质量负责人审核通过"}
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="A-13",
            scenario=scenario,
            step="quality_head_review",
            actor=quality_head,
            action="质量负责人审核通过",
            expected={
                "http": 200,
                "status": "pending_final_code",
                "current_step": "final_code_input",
                "final_code.handlers": [qa.name],
            },
            actual={
                "http": status,
                "status": detail.get("status"),
                "current_step": detail.get("current_step"),
                "final_code.handlers": _step_handlers(detail, "final_code_input"),
            },
            evidence={"previous_status": "pending_quality_head_review", "next_status": detail.get("status")},
        )
        self.recorder.require("A-13", passed, "质量负责人通过后未进入最终编号环节")

        # A-14 越权：质量负责人抢录最终编号
        status, body = await self.api.call(
            quality_head, "POST", f"/{ledger_id}/final-code", {"final_code": self._final_code("A")}
        )
        self.recorder.check(
            case_id="A-14",
            scenario=scenario,
            step="final_code_input",
            actor=quality_head,
            action="越权录入最终编号",
            expected={"http": 403, "message_contains": "无权操作"},
            actual={"http": status, "message_contains": _message(body)},
            evidence={"message": _message(body)},
        )

        # A-15 所属 QA 录入最终编号并关闭
        final_code = self._final_code("A")
        status, body = await self.api.call(
            qa, "POST", f"/{ledger_id}/final-code", {"final_code": final_code, "content": "E2E 关闭"}
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="A-15",
            scenario=scenario,
            step="final_code_input",
            actor=qa,
            action="所属 QA 录入最终编号",
            expected={"http": 200, "status": "closed", "final_code": final_code},
            actual={"http": status, "status": detail.get("status"), "final_code": detail.get("final_code")},
            evidence={"previous_status": "pending_final_code", "next_status": detail.get("status")},
        )
        self.recorder.require("A-15", passed, "录入最终编号后未关闭")

        return {"ledger_id": str(ledger_id), "final_code": final_code}

    # ── 场景 B：有跨部门 ────────────────────────────────────────────────
    async def run_cross_dept(self, closed_final_code: str | None) -> dict[str, Any]:
        scenario = "cross_dept"
        reporter = self.actors["reporter"]
        dept_head = self.actors["dept_head"]
        qa = self.actors["qa"]
        qa_head = self.actors["qa_head"]
        quality_head = self.actors["quality_head"]
        row_investigator = self.actors["row_investigator"]
        row_head_a = self.actors["row_head_a"]
        row_head_b = self.actors["row_head_b"]

        # B-01 创建（勾选跨部门，两行）
        status, body = await self.api.call(
            reporter,
            "POST",
            "",
            {
                "title": "E2E 跨部门偏差流程审核测试",
                "department": TEST_DEPARTMENT,
                "discovery_date": date.today().isoformat(),
                "discovery_time": "10:00",
                "discovery_location": "E2E 测试车间",
                "affected_items": "E2E 测试物料",
                "batch_number": "E2E-BATCH-002",
                "handler_ids": [str(reporter.id)],
                "needs_cross_dept_review": True,
                "cross_dept_reviewers": [
                    {
                        "department": CROSS_ROW_WITH_INVESTIGATION,
                        "investigator_ids": [str(row_investigator.id)],
                        "dept_head_id": str(row_head_a.id),
                    },
                    {
                        "department": CROSS_ROW_HEAD_ONLY,
                        "dept_head_id": str(row_head_b.id),
                    },
                ],
                "description": "用于验证跨部门偏差主链路（逐行调查 + 逐行审核），跑完自动清理。",
            },
        )
        detail = _detail(body)
        ledger_id = detail.get("id")
        passed = self.recorder.check(
            case_id="B-01",
            scenario=scenario,
            step="create",
            actor=reporter,
            action="新建偏差（勾选跨部门两行）",
            expected={
                "http": 200,
                "status": "pending_ai_analysis",
                "needs_cross_dept_review": True,
                "rows": 2,
                "cross_dept.applicable": True,
            },
            actual={
                "http": status,
                "status": detail.get("status"),
                "needs_cross_dept_review": detail.get("needs_cross_dept_review"),
                "rows": len(detail.get("cross_dept_reviewers") or []),
                "cross_dept.applicable": _step_payload(detail, "cross_dept_head_review").get("applicable"),
            },
            evidence={"code": detail.get("code"), "message": _message(body)},
        )
        self.recorder.require("B-01", passed and bool(ledger_id), "跨部门创建失败，无法继续场景 B")
        self.ledger_ids.append(uuid.UUID(str(ledger_id)))

        # B-02 提交调查
        status, body = await self.api.call(reporter, "POST", f"/{ledger_id}/investigation", self._investigation())
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="B-02",
            scenario=scenario,
            step="investigation",
            actor=reporter,
            action="提交主流程调查",
            expected={"http": 200, "status": "pending_dept_head_review", "current_step": "dept_head_review"},
            actual={
                "http": status,
                "status": detail.get("status"),
                "current_step": detail.get("current_step"),
            },
            evidence={"previous_status": "pending_ai_analysis", "next_status": detail.get("status")},
        )
        self.recorder.require("B-02", passed, "跨部门单提交调查失败")

        # B-03 部门负责人通过 → 跨部门逐行审核
        status, body = await self.api.call(
            dept_head, "POST", f"/{ledger_id}/review", {"result": "approved", "content": "部门负责人审核通过"}
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="B-03",
            scenario=scenario,
            step="dept_head_review",
            actor=dept_head,
            action="部门负责人审核通过（进入跨部门环节）",
            expected={
                "http": 200,
                "status": "pending_cross_dept_head_review",
                "current_step": "cross_dept_head_review",
                "row_a.investigate_state": "pending",
                "row_b.investigate_state": "pending",
            },
            actual={
                "http": status,
                "status": detail.get("status"),
                "current_step": detail.get("current_step"),
                "row_a.investigate_state": _sub_item(detail, CROSS_ROW_WITH_INVESTIGATION).get("investigate_state"),
                "row_b.investigate_state": _sub_item(detail, CROSS_ROW_HEAD_ONLY).get("investigate_state"),
            },
            evidence={"previous_status": "pending_dept_head_review", "next_status": detail.get("status")},
        )
        self.recorder.require("B-03", passed, "部门负责人通过后未进入跨部门审核环节")

        # B-04 整环节通过被拒
        status, body = await self.api.call(
            dept_head,
            "POST",
            f"/{ledger_id}/review",
            {"step": "cross_dept_head_review", "result": "approved", "content": "整环节通过尝试"},
        )
        self.recorder.check(
            case_id="B-04",
            scenario=scenario,
            step="cross_dept_head_review",
            actor=dept_head,
            action="跨部门整环节通过（应被拒绝）",
            expected={"http": 400, "message_contains": "逐行通过"},
            actual={"http": status, "message_contains": _message(body)},
            evidence={"message": _message(body)},
        )

        # B-05 行调查未提交时不可审核
        status, body = await self.api.call(
            row_head_a,
            "POST",
            f"/{ledger_id}/cross-dept-review",
            {"department": CROSS_ROW_WITH_INVESTIGATION, "opinion": "调查未提交时尝试审核"},
        )
        self.recorder.check(
            case_id="B-05",
            scenario=scenario,
            step="cross_dept_head_review",
            actor=row_head_a,
            action="行调查未提交即审核（应被拒绝）",
            expected={"http": 400, "message_contains": "调查尚未提交"},
            actual={"http": status, "message_contains": _message(body)},
            evidence={"message": _message(body)},
        )

        # B-06 行内调查人提交本部门调查
        status, body = await self.api.call(
            row_investigator,
            "POST",
            f"/{ledger_id}/cross-dept-investigation",
            {**self._investigation(), "department": CROSS_ROW_WITH_INVESTIGATION},
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="B-06",
            scenario=scenario,
            step="cross_dept_head_review",
            actor=row_investigator,
            action="行内调查人提交本部门调查",
            expected={
                "http": 200,
                "status": "pending_cross_dept_head_review",
                "row_a.investigate_state": "submitted",
                "row_a.state": "pending",
            },
            actual={
                "http": status,
                "status": detail.get("status"),
                "row_a.investigate_state": _sub_item(detail, CROSS_ROW_WITH_INVESTIGATION).get("investigate_state"),
                "row_a.state": _sub_item(detail, CROSS_ROW_WITH_INVESTIGATION).get("state"),
            },
        )
        self.recorder.require("B-06", passed, "跨部门行调查提交失败")

        # B-07 越权：另一行负责人审核本行
        status, body = await self.api.call(
            row_head_b,
            "POST",
            f"/{ledger_id}/cross-dept-review",
            {"department": CROSS_ROW_WITH_INVESTIGATION, "opinion": "越权审核尝试"},
        )
        self.recorder.check(
            case_id="B-07",
            scenario=scenario,
            step="cross_dept_head_review",
            actor=row_head_b,
            action="跨部门行越权审核（非本行负责人）",
            expected={"http": 403, "message_contains": "审核人"},
            actual={"http": status, "message_contains": _message(body)},
            evidence={"message": _message(body)},
        )

        # B-08 行 A 审核通过（未全通过，流程不前进）
        status, body = await self.api.call(
            row_head_a,
            "POST",
            f"/{ledger_id}/cross-dept-review",
            {"department": CROSS_ROW_WITH_INVESTIGATION, "opinion": "101车间审核通过"},
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="B-08",
            scenario=scenario,
            step="cross_dept_head_review",
            actor=row_head_a,
            action="行 A 审核通过（另一行未通过）",
            expected={
                "http": 200,
                "status": "pending_cross_dept_head_review",
                "row_a.state": "approved",
                "row_b.state": "pending",
            },
            actual={
                "http": status,
                "status": detail.get("status"),
                "row_a.state": _sub_item(detail, CROSS_ROW_WITH_INVESTIGATION).get("state"),
                "row_b.state": _sub_item(detail, CROSS_ROW_HEAD_ONLY).get("state"),
            },
        )
        self.recorder.require("B-08", passed, "行 A 审核未按预期停留或标记")

        # B-09 行 B 审核通过 → 全部通过，进入 QA
        status, body = await self.api.call(
            row_head_b,
            "POST",
            f"/{ledger_id}/cross-dept-review",
            {"department": CROSS_ROW_HEAD_ONLY, "opinion": "102车间审核通过"},
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="B-09",
            scenario=scenario,
            step="cross_dept_head_review",
            actor=row_head_b,
            action="行 B 审核通过（全部行通过）",
            expected={
                "http": 200,
                "status": "pending_qa_review",
                "current_step": "qa_review",
                "row_b.state": "approved",
            },
            actual={
                "http": status,
                "status": detail.get("status"),
                "current_step": detail.get("current_step"),
                "row_b.state": _sub_item(detail, CROSS_ROW_HEAD_ONLY).get("state"),
            },
            evidence={"previous_status": "pending_cross_dept_head_review", "next_status": detail.get("status")},
        )
        self.recorder.require("B-09", passed, "全部行通过后未进入所属 QA 审核")

        # B-10 QA 审核通过
        status, body = await self.api.call(
            qa,
            "POST",
            f"/{ledger_id}/review",
            {"result": "approved", "content": "QA 审核通过", "reason_category": "设施设备"},
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="B-10",
            scenario=scenario,
            step="qa_review",
            actor=qa,
            action="QA 审核通过",
            expected={"http": 200, "status": "pending_qa_head_review"},
            actual={"http": status, "status": detail.get("status")},
            evidence={"previous_status": "pending_qa_review", "next_status": detail.get("status")},
        )
        self.recorder.require("B-10", passed, "跨部门单 QA 审核未推进")

        # B-11 QA 负责人通过
        status, body = await self.api.call(
            qa_head,
            "POST",
            f"/{ledger_id}/review",
            {"result": "approved", "content": "QA 负责人审核通过", "deviation_level": "moderate"},
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="B-11",
            scenario=scenario,
            step="qa_head_review",
            actor=qa_head,
            action="QA 负责人审核通过",
            expected={"http": 200, "status": "pending_quality_head_review"},
            actual={"http": status, "status": detail.get("status")},
            evidence={"previous_status": "pending_qa_head_review", "next_status": detail.get("status")},
        )
        self.recorder.require("B-11", passed, "跨部门单 QA 负责人审核未推进")

        # B-12 质量负责人通过
        status, body = await self.api.call(
            quality_head, "POST", f"/{ledger_id}/review", {"result": "approved", "content": "质量负责人审核通过"}
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="B-12",
            scenario=scenario,
            step="quality_head_review",
            actor=quality_head,
            action="质量负责人审核通过",
            expected={"http": 200, "status": "pending_final_code"},
            actual={"http": status, "status": detail.get("status")},
            evidence={"previous_status": "pending_quality_head_review", "next_status": detail.get("status")},
        )
        self.recorder.require("B-12", passed, "跨部门单质量负责人审核未推进")

        # B-13 最终编号重复（若场景 A 已关闭）
        final_code = self._final_code("B")
        if closed_final_code:
            status, body = await self.api.call(
                qa, "POST", f"/{ledger_id}/final-code", {"final_code": closed_final_code, "content": "重复编号尝试"}
            )
            self.recorder.check(
                case_id="B-13",
                scenario=scenario,
                step="final_code_input",
                actor=qa,
                action="录入已被占用的最终编号",
                expected={"http": 400, "message_contains": "已被使用"},
                actual={"http": status, "message_contains": _message(body)},
                evidence={"message": _message(body)},
            )

        # B-14 录入唯一最终编号并关闭
        status, body = await self.api.call(
            qa, "POST", f"/{ledger_id}/final-code", {"final_code": final_code, "content": "E2E 关闭"}
        )
        detail = _detail(body)
        passed = self.recorder.check(
            case_id="B-14",
            scenario=scenario,
            step="final_code_input",
            actor=qa,
            action="所属 QA 录入最终编号",
            expected={"http": 200, "status": "closed", "final_code": final_code},
            actual={"http": status, "status": detail.get("status"), "final_code": detail.get("final_code")},
            evidence={"previous_status": "pending_final_code", "next_status": detail.get("status")},
        )
        self.recorder.require("B-14", passed, "跨部门单录入最终编号后未关闭")

        return {"ledger_id": str(ledger_id), "final_code": final_code}

    # ── 公共构造 ────────────────────────────────────────────────────────
    def _investigation(self) -> dict[str, Any]:
        return {
            "nonconformity_description": "E2E：记录不符合事项（自动测试数据）",
            "root_cause_analysis": "E2E：根本原因分析（自动测试数据）",
            "risk_assessment": "E2E：风险评估（自动测试数据）",
            "capa_proposals": [{"summary": "E2E：CAPA 改进建议（自动测试数据）", "executor": "E2E"}],
            "submit_content": "E2E 提交调查",
        }

    def _final_code(self, scenario: str) -> str:
        stamp = datetime.now(UTC).strftime("%m%d%H%M%S")
        return f"E2E-{scenario}-{stamp}"


# ── 数据准备 / 临时授权 / 清理 ──────────────────────────────────────────


@dataclass
class Prepared:
    actors: dict[str, Actor]
    contact_created: bool
    role_created: bool


def _pick_user(users: list[User], department: str, exclude: set[uuid.UUID]) -> User | None:
    candidates = sorted(
        (user for user in users if user.department == department and user.id not in exclude),
        key=lambda user: user.name,
    )
    return candidates[0] if candidates else None


async def prepare(db: Any) -> Prepared:
    rows = (await db.scalars(select(User).where(User.is_deleted.is_(False)))).all()
    users = [user for user in rows if user.status != "disabled"]
    by_id = {user.id: user for user in users}

    #: 参考部门只用来「取人」，不参与处理人解析（本地库部分历史行是软删除状态）
    contacts = {contact.department: contact for contact in (await db.scalars(select(DepartmentContact))).all()}

    reference = contacts.get(REFERENCE_DEPARTMENT)
    qa_contact = contacts.get(QA_DEPARTMENT)
    row_b_contact = contacts.get(CROSS_ROW_HEAD_ONLY)
    if reference is None or qa_contact is None or row_b_contact is None:
        raise RuntimeError(
            f"部门联系人缺少参考部门配置（{REFERENCE_DEPARTMENT} / {QA_DEPARTMENT} / {CROSS_ROW_HEAD_ONLY}），"
            "请先在「部门联系人配置」补齐"
        )

    dept_head = by_id.get(reference.dept_head_id) if reference.dept_head_id else None
    qa_reviewer = by_id.get(qa_contact.qa_reviewer_id) if qa_contact.qa_reviewer_id else None
    qa_head = by_id.get(qa_contact.qa_head_id) if qa_contact.qa_head_id else None
    quality_head = by_id.get(qa_contact.quality_head_id) if qa_contact.quality_head_id else None
    row_head_a = by_id.get(reference.dept_head_id) if reference.dept_head_id else None
    row_head_b = by_id.get(row_b_contact.dept_head_id) if row_b_contact.dept_head_id else None
    if not all([dept_head, qa_reviewer, qa_head, quality_head, row_head_a, row_head_b]):
        raise RuntimeError("参考部门联系人的角色配置不完整，无法构造真实处理人")

    reserved = {dept_head.id, qa_reviewer.id, qa_head.id, quality_head.id, row_head_b.id}
    reporter = _pick_user(users, REFERENCE_DEPARTMENT, reserved)
    if reporter is None:
        raise RuntimeError(f"{REFERENCE_DEPARTMENT} 没有可用的普通用户作为调查人")
    reserved.add(reporter.id)
    row_investigator = _pick_user(users, CROSS_ROW_WITH_INVESTIGATION, reserved)
    if row_investigator is None:
        raise RuntimeError(f"{CROSS_ROW_WITH_INVESTIGATION} 没有第二个用户作为行内调查人")

    #: 测试部门联系人：每次重建，四个角色分别指向不同用户，跑完删除
    await db.execute(delete(DepartmentContact).where(DepartmentContact.department == TEST_DEPARTMENT))
    db.add(
        DepartmentContact(
            department=TEST_DEPARTMENT,
            dept_head_id=dept_head.id,
            qa_reviewer_id=qa_reviewer.id,
            qa_head_id=qa_head.id,
            quality_head_id=quality_head.id,
            is_production_workshop=False,
        )
    )
    await db.commit()
    contact_created = True

    actors = {
        "reporter": Actor("reporter", "上报人 / 调查人", reporter.id, reporter.name, reporter.department),
        "dept_head": Actor("dept_head", "部门负责人", dept_head.id, dept_head.name, dept_head.department),
        "qa": Actor("qa", "所属 QA", qa_reviewer.id, qa_reviewer.name, qa_reviewer.department),
        "qa_head": Actor("qa_head", "QA 负责人", qa_head.id, qa_head.name, qa_head.department),
        "quality_head": Actor(
            "quality_head", "质量负责人", quality_head.id, quality_head.name, quality_head.department
        ),
        "row_investigator": Actor(
            "row_investigator",
            "跨部门行调查人",
            row_investigator.id,
            row_investigator.name,
            row_investigator.department,
        ),
        "row_head_a": Actor(
            "row_head_a",
            f"{CROSS_ROW_WITH_INVESTIGATION} 负责人",
            row_head_a.id,
            row_head_a.name,
            row_head_a.department,
        ),
        "row_head_b": Actor(
            "row_head_b",
            f"{CROSS_ROW_HEAD_ONLY} 负责人",
            row_head_b.id,
            row_head_b.name,
            row_head_b.department,
        ),
    }

    role_created = await _grant_permissions(db, list(by_id[actor.id] for actor in actors.values()))
    for actor in actors.values():
        user = by_id[actor.id]
        actor.token = generate_jwt(user)
    return Prepared(actors=actors, contact_created=contact_created, role_created=role_created)


async def _grant_permissions(db: Any, users: list[User]) -> bool:
    role = await db.scalar(select(Role).where(Role.code == ROLE_CODE, Role.is_deleted.is_(False)))
    role_created = False
    if role is None:
        role = Role(
            code=ROLE_CODE,
            name=ROLE_NAME,
            category="module",
            module_code="quality",
            description="临时角色：偏差流程 API E2E 审核测试，跑完自动删除",
            is_builtin=False,
            is_superuser=False,
            status="active",
        )
        db.add(role)
        await db.flush()
        role_created = True

    existing_codes = set(
        (await db.scalars(select(RolePermission.permission_code).where(RolePermission.role_id == role.id))).all()
    )
    for code in PERMISSION_CODES:
        if code not in existing_codes:
            db.add(RolePermission(role_id=role.id, permission_code=code))

    for user in users:
        granted = await db.scalar(
            select(UserRoleGrant.id).where(
                UserRoleGrant.user_id == user.id,
                UserRoleGrant.role_id == role.id,
                UserRoleGrant.is_deleted.is_(False),
            )
        )
        if granted is None:
            db.add(UserRoleGrant(user_id=user.id, role_id=role.id, scope_type="all", status="active"))

    await db.commit()
    for user in users:
        await evict_user_permission_cache(user.id)
    return role_created


async def cleanup(db: Any, prepared: Prepared, ledger_ids: list[uuid.UUID], keep: bool) -> dict[str, Any]:
    result: dict[str, Any] = {"kept_ledgers": [], "deleted_ledgers": 0, "role_removed": False, "contact_removed": False}
    if keep:
        result["kept_ledgers"] = [str(item) for item in ledger_ids]
        result["note"] = "已按 --keep 保留本次台账，临时权限仍会回收"
    else:
        if ledger_ids:
            await db.execute(delete(DeviationLedger).where(DeviationLedger.id.in_(ledger_ids)))
            await db.commit()
            result["deleted_ledgers"] = len(ledger_ids)

    await db.execute(delete(DepartmentContact).where(DepartmentContact.department == TEST_DEPARTMENT))
    await db.commit()
    result["contact_removed"] = True

    role = await db.scalar(select(Role).where(Role.code == ROLE_CODE))
    if role is not None:
        await db.execute(delete(UserRoleGrant).where(UserRoleGrant.role_id == role.id))
        await db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        await db.execute(delete(Role).where(Role.id == role.id))
        await db.commit()
        result["role_removed"] = True

    for actor in prepared.actors.values():
        await evict_user_permission_cache(actor.id)

    if ledger_ids:
        remaining = await db.scalar(
            select(DeviationLedger.code).where(DeviationLedger.id.in_(ledger_ids)).limit(1)
        )
        result["remaining_ledger"] = remaining
    return result


# ── 报告 ────────────────────────────────────────────────────────────────


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(value.replace("|", "\\|") for value in row) + " |")
    return "\n".join(lines)


def write_report(
    recorder: Recorder,
    actors: dict[str, Actor],
    cleanup_result: dict[str, Any],
    *,
    base_url: str,
    started_at: datetime,
    scenario_results: dict[str, Any],
    report_dir: Path,
) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = started_at.strftime("%Y%m%d-%H%M%S")
    md_path = report_dir / f"deviation-flow-e2e-{stamp}.md"
    json_path = report_dir / f"deviation-flow-e2e-{stamp}.json"

    failed = recorder.failed
    conclusion = "PASS" if not failed else "FAIL"
    actor_rows = [
        [actor.role, actor.name, actor.department or "-", str(actor.id)] for actor in actors.values()
    ]
    case_rows = [
        [
            case.case_id,
            case.scenario,
            case.step,
            case.actor,
            case.action,
            "通过" if case.passed else "**失败**",
            json.dumps(case.expected, ensure_ascii=False),
            json.dumps(case.actual, ensure_ascii=False),
        ]
        for case in recorder.cases
    ]
    trajectory_rows = []
    for case in recorder.cases:
        evidence = case.evidence
        if "next_status" not in evidence:
            continue
        trajectory_rows.append(
            [
                case.case_id,
                case.scenario,
                case.step,
                case.actor,
                case.action,
                str(evidence.get("previous_status") or "-"),
                str(evidence.get("next_status") or "-"),
                "通过" if case.passed else "**失败**",
            ]
        )

    md_lines = [
        "# 偏差管理流程 API 端到端审核测试报告",
        "",
        f"- 结论：**{conclusion}**（用例 {len(recorder.cases)} 条，失败 {len(failed)} 条）",
        f"- 执行时间：{started_at.isoformat()}",
        f"- 目标环境：{base_url}",
        f"- 测试部门：{TEST_DEPARTMENT}（脚本临时创建，跑完删除）",
        f"- 场景结果：{json.dumps(scenario_results, ensure_ascii=False)}",
        "",
        "## 参与角色（真实用户，临时授权 quality:deviation:*）",
        "",
        _markdown_table(["环节角色", "姓名", "所属部门", "用户 ID"], actor_rows),
        "",
        "## 状态轨迹",
        "",
        _markdown_table(
            ["用例", "场景", "环节", "操作人", "动作", "前状态", "后状态", "结论"], trajectory_rows
        ),
        "",
        "## 用例明细",
        "",
        _markdown_table(
            ["用例", "场景", "环节", "操作人", "动作", "结论", "期望", "实际"], case_rows
        ),
        "",
    ]
    if failed:
        md_lines.extend(
            [
                "## 失败明细",
                "",
                *[f"- {case.case_id} {case.step}：期望 {case.expected}，实际 {case.actual}" for case in failed],
                "",
            ]
        )
    if recorder.notes:
        md_lines.extend(["## 备注", "", *[f"- {note}" for note in recorder.notes], ""])
    md_lines.extend(
        [
            "## 清理结果",
            "",
            "```json",
            json.dumps(cleanup_result, ensure_ascii=False, indent=2),
            "```",
            "",
            "> 说明：临时角色与授权已回收；如使用 `--keep`，台账保留可人工复核，权限仍回收。",
            "",
        ]
    )
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    payload = {
        "meta": {
            "started_at": started_at.isoformat(),
            "base_url": base_url,
            "test_department": TEST_DEPARTMENT,
            "conclusion": conclusion,
            "case_count": len(recorder.cases),
            "failed_count": len(failed),
            "scenario_results": scenario_results,
        },
        "actors": [actor.to_dict() for actor in actors.values()],
        "cases": [case.to_dict() for case in recorder.cases],
        "notes": recorder.notes,
        "cleanup": cleanup_result,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path, json_path


# ── 入口 ────────────────────────────────────────────────────────────────


async def main_async(args: argparse.Namespace) -> int:
    started_at = datetime.now(UTC)
    recorder = Recorder()
    api = Api(args.base_url)
    scenario_results: dict[str, Any] = {}
    cleanup_result: dict[str, Any] = {}

    async with async_session_factory() as db:
        prepared = await prepare(db)
        actors = prepared.actors
        print("参与角色：")
        for actor in actors.values():
            print(f"  - {actor.role}: {actor.name}（{actor.department}）")
        audit = FlowAudit(api, recorder, actors)
        try:
            if args.scenario in ("all", "no-cross"):
                scenario_results["no_cross_dept"] = await audit.run_no_cross_dept()
            if args.scenario in ("all", "cross"):
                closed_code = (scenario_results.get("no_cross_dept") or {}).get("final_code")
                scenario_results["cross_dept"] = await audit.run_cross_dept(closed_code)
        except AbortScenarioError as exc:
            recorder.notes.append(str(exc))
            print(f"场景中止：{exc}")
        finally:
            cleanup_result = await cleanup(db, prepared, audit.ledger_ids, args.keep)

    md_path, json_path = write_report(
        recorder,
        actors,
        cleanup_result,
        base_url=args.base_url,
        started_at=started_at,
        scenario_results=scenario_results,
        report_dir=Path(args.report_dir),
    )
    print(f"\n报告：{md_path}")
    print(f"证据：{json_path}")
    outcome = "PASS" if not recorder.failed else "FAIL"
    print(f"结论：{outcome}（失败 {len(recorder.failed)} / 共 {len(recorder.cases)}）")
    return 0 if not recorder.failed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="偏差流程 API 端到端审核测试")
    parser.add_argument("--base-url", default="http://localhost:8000", help="后端地址（容器内默认 localhost:8000）")
    parser.add_argument("--scenario", choices=("all", "no-cross", "cross"), default="all", help="执行哪些场景")
    parser.add_argument("--keep", action="store_true", help="保留本次台账（临时权限仍会回收）")
    parser.add_argument("--report-dir", default=str(REPORT_DIR), help="报告输出目录")
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
