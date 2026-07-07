"""AI platform API routes."""

import json
import logging
import openai
import re
from collections.abc import AsyncGenerator
from io import BytesIO
from typing import Any
from urllib.parse import quote

from docx import Document as DocxDocument
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success_response
from app.modules.administration.models import VehicleRequest
from app.modules.administration.public_api import (
    count_vehicle_requests,
    search_vehicle_requests,
    search_vehicles,
)
from app.modules.hr.public_api import (
    count_employees,
    list_employees_by_department,
    search_employees_by_name,
    search_employees_fuzzy,
)
from app.platform.ai.deps import get_ai_chat_service
from app.platform.ai.exam_generator import (
    build_generate_prompt,
    generate_exam_docx,
)
from app.platform.ai.schemas import (
    ChatRequest,
    ChoiceOption,
    ChoiceQuestion,
    ExamExportRequest,
    ExamGenerateResponse,
    TrueFalseQuestion,
)
from app.platform.ai.service import AiChatService

router = APIRouter()
logger = logging.getLogger(__name__)


def _extract_names(text: str) -> list[str]:
    """Extract possible Chinese person names from text (2-4 chars)."""
    return re.findall(r"[一-龥]{2,4}", text)


def _detect_query_intent(text: str) -> tuple[str, dict] | None:
    """Detect user intent for HR database queries."""
    # 1. 某部门有哪些人 / 某部门的人 / 某部门名单
    m = re.search(
        r"([一-龥\w\-]{2,20}(?:部门|车间|科室|组|部|中心))"
        r".*?(?:有哪些人|的人|名单|员工|成员)",
        text,
    )
    if m:
        return ("list_department", {"department": m.group(1)})

    # 2. 某人（是/在）哪个部门
    m = re.search(
        r"([一-龥]{2,4})(?:是|在).*?(?:哪个部门|什么部门|所属部门)",
        text,
    )
    if m:
        return ("employee_department", {"name": m.group(1)})

    # 3. 某部门有多少（人/员工）
    m = re.search(
        r"([一-龥\w\-]{2,20}(?:部门|车间|科室|组|部|中心))"
        r".*?(?:有多少|共多少|人数|几人)",
        text,
    )
    if m:
        return ("count_department", {"department": m.group(1)})

    # 4. 总共有多少（人/员工）
    if re.search(
        r"(?:总共|一共|全厂|公司|整体).*?(?:有多少|共多少|人数|几人)",
        text,
    ):
        return ("count_total", {})

    return None


async def _build_db_context(
    session: AsyncSession, text: str
) -> str:
    """Query HR database based on user intent and return formatted context."""
    parts: list[str] = []

    # Intent-based queries
    intent = _detect_query_intent(text)
    if intent:
        action, params = intent
        if action == "list_department":
            dept = params["department"]
            employees, total = await list_employees_by_department(session, dept)
            if employees:
                parts.append(f"【数据库查询结果】{dept}共有{total}名员工：")
                for emp in employees:
                    parts.append(
                        f"- {emp['name']}（工号:{emp['employee_number']}）"
                        f"，职位:{emp['position']}"
                        f"，状态:{emp['status']}"
                    )
            else:
                parts.append(f"【数据库查询结果】未找到{dept}的员工记录。")

        elif action == "employee_department":
            name = params["name"]
            employees = await search_employees_by_name(session, name)
            if employees:
                parts.append(f"【数据库查询结果】姓名包含'{name}'的员工：")
                for emp in employees:
                    parts.append(
                        f"- {emp['name']}（工号:{emp['employee_number']}）"
                        f"，部门:{emp['department']}"
                        f"，职位:{emp['position']}"
                        f"，状态:{emp['status']}"
                    )
            else:
                # 精确查询不到时，做模糊查询
                fuzzy = await search_employees_fuzzy(session, name)
                if fuzzy:
                    parts.append(
                        f"【数据库查询结果】未找到姓名包含'{name}'的员工。"
                        f"以下是名字中包含'{name}'中某个字的员工（可能为相似姓名）："
                    )
                    for emp in fuzzy[:10]:
                        parts.append(
                            f"- {emp['name']}（工号:{emp['employee_number']}）"
                            f"，部门:{emp['department']}"
                            f"，职位:{emp['position']}"
                            f"，状态:{emp['status']}"
                        )
                else:
                    parts.append(
                        f"【数据库查询结果】未找到姓名包含'{name}'或相关字的员工。"
                    )

        elif action == "count_department":
            dept = params["department"]
            total = await count_employees(session, department=dept)
            parts.append(f"【数据库查询结果】{dept}共有{total}名员工。")

        elif action == "count_total":
            total = await count_employees(session)
            parts.append(f"【数据库查询结果】全厂共有{total}名员工。")

    # Fallback: keyword-based name search if no intent matched
    if not intent:
        names = _extract_names(text)
        seen: set[str] = set()
        for name in names[:3]:
            if name in seen:
                continue
            seen.add(name)
            employees = await search_employees_by_name(session, name)
            if employees:
                parts.append(
                    f"【数据库查询结果】姓名包含'{name}'的员工："
                )
                for emp in employees:
                    parts.append(
                        f"- {emp['name']}（工号:{emp['employee_number']}）"
                        f"，部门:{emp['department']}"
                        f"，职位:{emp['position']}"
                        f"，状态:{emp['status']}"
                    )
            else:
                fuzzy = await search_employees_fuzzy(session, name)
                if fuzzy:
                    parts.append(
                        f"【数据库查询结果】未找到姓名包含'{name}'的员工。"
                        f"以下是名字中包含'{name}'中某个字的员工（可能为相似姓名）："
                    )
                    for emp in fuzzy[:10]:
                        parts.append(
                            f"- {emp['name']}（工号:{emp['employee_number']}）"
                            f"，部门:{emp['department']}"
                            f"，职位:{emp['position']}"
                            f"，状态:{emp['status']}"
                        )
                else:
                    parts.append(
                        f"【数据库查询结果】未找到姓名包含'{name}'或相关字的员工。"
                    )

    return "\n".join(parts)


def _extract_months(text: str) -> list[int] | None:
    """Extract month numbers from text for vehicle request queries.

    Supports patterns like:
    - 5月, 6月 (single)
    - 5-6月, 5~6月 (range)
    - 5月和6月, 5月、6月, 5月，6月 (multiple)
    - 5-6月份 (with 份 suffix)
    """
    # 1. Range pattern: 5-6月, 5~6月, 5到6月
    range_match = re.search(r"(\d{1,2})[-~到](\d{1,2})月(?:份)?", text)
    if range_match:
        start, end = int(range_match.group(1)), int(range_match.group(2))
        if 1 <= start <= 12 and 1 <= end <= 12:
            if start <= end:
                return list(range(start, end + 1))
            else:
                return list(range(end, start + 1))

    # 2. Multiple months pattern: 5月和6月, 5月、6月, 5月，6月
    # Find all "X月" occurrences and deduplicate
    month_matches = re.findall(r"(\d{1,2})月(?:份)?", text)
    if month_matches:
        months = sorted(set(int(m) for m in month_matches if 1 <= int(m) <= 12))
        return months

    return None


async def _build_vehicle_db_context(
    session: AsyncSession, text: str
) -> str:
    """Query vehicle/administration database based on user intent."""
    parts: list[str] = []

    # 1. 按月份统计（支持单个月、多个月、范围）
    months = _extract_months(text)
    if months and re.search(r"(?:用车申请|申请).*?(?:多少|数量|总数|几个)", text):
        total_count = 0
        month_counts: list[tuple[int, int]] = []
        for month in months:
            count_stmt = (
                select(func.count())
                .select_from(VehicleRequest)
                .where(
                    extract("month", VehicleRequest.start_time) == month,
                    VehicleRequest.is_deleted.is_(False),
                )
            )
            count = await session.scalar(count_stmt) or 0
            month_counts.append((month, count))
            total_count += count

        if len(months) == 1:
            parts.append(f"【数据库查询结果】{months[0]}月用车申请总数：{total_count}条。")
        else:
            month_details = "，".join(f"{m}月{c}条" for m, c in month_counts)
            parts.append(
                f"【数据库查询结果】{month_details}，合计：{total_count}条。"
            )
    else:
        # 2. 统计用车申请数量（按状态）
        status_count_keywords = [
            ("待审批", r"待审批.*?(?:多少|数量|几个)"),
            ("已通过", r"已通过.*?(?:多少|数量|几个)"),
            ("已拒绝", r"已拒绝.*?(?:多少|数量|几个)"),
            ("已完成", r"已完成.*?(?:多少|数量|几个)"),
        ]
        for status, pattern in status_count_keywords:
            if re.search(pattern, text):
                total = await count_vehicle_requests(session, status=status)
                parts.append(f"【数据库查询结果】状态为'{status}'的用车申请共有{total}条。")
                break
        else:
            # 总数量
            if re.search(r"(?:总共|一共|全部).*?(?:用车申请|申请).*?(?:多少|数量|几个)", text):
                total = await count_vehicle_requests(session)
                parts.append(f"【数据库查询结果】用车申请总数量：{total}条。")

    # 2. 按申请人查询（只匹配纯中文人名，避免误匹配月份数字）
    applicant_match = re.search(r"([一-龥]{2,10})(?:的用车申请|申请了车|申请用车)", text)
    if applicant_match:
        name = applicant_match.group(1)
        requests, total = await search_vehicle_requests(
            session, keyword=name, page=1, page_size=20
        )
        if requests:
            parts.append(f"【数据库查询结果】申请人包含'{name}'的用车申请共{total}条：")
            for r in requests:
                parts.append(
                    f"- 申请人:{r['applicant_name']}（{r['applicant_department']}）"
                    f"，事由:{r['purpose'][:40]}"
                    f"，目的地:{r['destination'] or '无'}"
                    f"，时间:{r['start_time']} 至 {r['end_time']}"
                    f"，状态:{r['status']}"
                )
        else:
            parts.append(f"【数据库查询结果】未找到申请人包含'{name}'的用车申请。")

    # 3. 按状态查询列表
    status_list_keywords = [
        ("待审批", r"(?:待审批|未审批|未处理).*?(?:申请|列表|记录)"),
        ("已通过", r"(?:已通过|已批准).*?(?:申请|列表|记录)"),
        ("已完成", r"(?:已完成|已结束).*?(?:申请|列表|记录)"),
    ]
    for status, pattern in status_list_keywords:
        if re.search(pattern, text):
            requests, total = await search_vehicle_requests(
                session, status=status, page=1, page_size=20
            )
            if requests:
                parts.append(f"【数据库查询结果】状态为'{status}'的用车申请共{total}条：")
                for r in requests:
                    parts.append(
                        f"- 申请人:{r['applicant_name']}（{r['applicant_department']}）"
                        f"，事由:{r['purpose'][:40]}"
                        f"，目的地:{r['destination'] or '无'}"
                        f"，时间:{r['start_time']} 至 {r['end_time']}"
                    )
            else:
                parts.append(f"【数据库查询结果】暂无状态为'{status}'的用车申请。")
            break

    # 4. 车辆信息查询
    if re.search(r"(?:车辆|车|车牌).*?(?:信息|列表|多少|状态)", text):
        vehicles, total = await search_vehicles(session, page=1, page_size=50)
        if vehicles:
            parts.append(f"【数据库查询结果】车辆总数：{total}辆")
            for v in vehicles:
                parts.append(
                    f"- 车牌:{v['plate_number']}，品牌:{v['brand'] or '无'}"
                    f"，状态:{v['status']}，归属:{v['owner_department'] or '无'}"
                )
        else:
            parts.append("【数据库查询结果】暂无车辆信息。")

    return "\n".join(parts)


def _convert_message_with_attachments(msg: dict[str, Any]) -> dict[str, Any]:
    """Convert a message dict with attachments to multimodal format.

    Moonshot / OpenAI compatible format:
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "..."},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
      ]
    }
    """
    role = msg.get("role", "user")
    content = msg.get("content", "")
    attachments: list[dict[str, str]] = msg.get("attachments") or []

    if not attachments:
        return {"role": role, "content": content}

    # Build multimodal content array
    content_parts: list[dict[str, Any]] = [{"type": "text", "text": content}]
    for att in attachments:
        mime = att.get("mime_type", "image/png")
        data = att.get("data", "")
        content_parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{data}"},
            }
        )

    return {"role": role, "content": content_parts}


@router.post("/chat/stream", summary="AI 流式对话")
async def chat_stream(
    request: ChatRequest,
    service: AiChatService | None = Depends(get_ai_chat_service),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Receive a chat request and stream the AI response via SSE."""

    page = request.page_context.page if request.page_context else None
    is_vehicle_page = page and "用车" in page
    is_regulation_page = page and ("制度" in page or "regulation" in page.lower())

    # 1. Build base system prompt
    # 制度页面使用前端传来的 system prompt（包含制度内容），后端不覆盖
    if is_regulation_page:
        system_prompt = None
    elif is_vehicle_page:
        system_prompt = AiChatService.build_vehicle_system_prompt(page=page)
    else:
        system_prompt = AiChatService.build_system_prompt(page=page)

    # 2. Query database based on user intent
    db_context = ""
    if request.messages and request.messages[-1].role == "user":
        user_text = request.messages[-1].content
        if is_vehicle_page:
            db_context = await _build_vehicle_db_context(session, user_text)
        elif not is_regulation_page:
            db_context = await _build_db_context(session, user_text)

    # 3. Build messages list and convert attachments
    raw_messages = [m.model_dump() for m in request.messages]
    messages: list[dict[str, Any]] = []
    for raw in raw_messages:
        converted = _convert_message_with_attachments(raw)
        messages.append(converted)

    # Inject DB context directly into the last user message
    if db_context and messages and messages[-1]["role"] == "user":
        original = messages[-1]["content"]
        # If content is a list (multimodal), inject text into the first text part
        if isinstance(original, list):
            for part in original:
                if part.get("type") == "text":
                    part["text"] = (
                        f"【数据库查询结果，请严格基于以下事实回答，禁止编造】\n"
                        f"{db_context}\n\n"
                        f"【用户原始问题】\n{part['text']}"
                    )
                    break
        else:
            messages[-1]["content"] = (
                f"【数据库查询结果，请严格基于以下事实回答，禁止编造】\n"
                f"{db_context}\n\n"
                f"【用户原始问题】\n{original}"
            )

    # 4. Append page context as the last user message hint if provided
    if request.page_context and request.page_context.data_summary:
        summary_text = json.dumps(
            request.page_context.data_summary, ensure_ascii=False
        )
        if messages and messages[-1]["role"] == "user":
            original = messages[-1]["content"]
            if isinstance(original, list):
                for part in original:
                    if part.get("type") == "text":
                        part["text"] = (
                            f"[当前页面数据概览]\n{summary_text}\n\n"
                            f"[用户问题]\n{part['text']}"
                        )
                        break
            else:
                messages[-1]["content"] = (
                    f"[当前页面数据概览]\n{summary_text}\n\n"
                    f"[用户问题]\n{original}"
                )

    async def event_generator() -> AsyncGenerator[str, None]:
        if service is None:
            payload = json.dumps(
                {"content": "\n\n[提示] Moonshot API Key 未配置，请在后端 .env 文件中设置 MOONSHOT_API_KEY"},
                ensure_ascii=False,
            )
            yield f"data: {payload}\n\n"
            done_payload = json.dumps({"done": True}, ensure_ascii=False)
            yield f"data: {done_payload}\n\n"
            return

        try:
            async for token in service.stream_chat(messages, system_prompt):
                payload = json.dumps({"content": token}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
        except Exception as exc:
            payload = json.dumps(
                {"content": f"\n\n[错误] 服务异常: {exc}"}, ensure_ascii=False
            )
            yield f"data: {payload}\n\n"
        done_payload = json.dumps({"done": True}, ensure_ascii=False)
        yield f"data: {done_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


# ─── AI 出题相关接口 ───

_SUPPORTED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}


def _extract_text_from_file(file_bytes: bytes, file_type: str) -> str:
    """从上传文件中提取纯文本内容."""
    if file_type == "docx":
        buffer = BytesIO(file_bytes)
        doc = DocxDocument(buffer)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    if file_type == "txt":
        # 尝试多种编码
        for encoding in ("utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030"):
            try:
                return file_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("无法识别文本文件编码")
    raise ValueError(f"不支持的文件类型: {file_type}")


async def _call_moonshot_for_exam(
    client: openai.AsyncOpenAI,
    file_content: str,
    model: str = "kimi-k2.5",
) -> ExamGenerateResponse:
    """调用 AI API 根据文件内容生成题目."""
    prompt = build_generate_prompt(file_content)

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一个专业的培训考核出题专家，只输出JSON格式内容。"},
            {"role": "user", "content": prompt},
        ],
        temperature=1,
        max_tokens=4096,
    )

    content = response.choices[0].message.content or ""
    logger.info("Moonshot raw response length: %d", len(content))

    # 尝试从响应中提取 JSON
    json_str = ""

    # 1. 尝试提取 markdown json 代码块
    json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # 2. 尝试提取普通代码块
        json_match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 3. 尝试找第一个 { 到最后一个 }
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_str = content[start : end + 1]
            else:
                json_str = content

    # 清理可能的 BOM 和非法字符
    json_str = json_str.strip().lstrip("﻿")

    logger.info("Extracted JSON string length: %d", len(json_str))

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse failed: %s", exc)
        logger.error("Raw content preview: %s", content[:500])
        logger.error("Extracted JSON preview: %s", json_str[:500])
        raise

    choice_questions = [
        ChoiceQuestion(
            number=q["number"],
            question=q["question"],
            options=[
                ChoiceOption(label=o["label"], text=o["text"])
                for o in q.get("options", [])
            ],
            answer=q.get("answer"),
        )
        for q in data.get("choice_questions", [])
    ]

    true_false_questions = [
        TrueFalseQuestion(
            number=q["number"],
            question=q["question"],
            answer=q.get("answer"),
        )
        for q in data.get("true_false_questions", [])
    ]

    return ExamGenerateResponse(
        choice_questions=choice_questions,
        true_false_questions=true_false_questions,
    )


@router.post("/exam/generate", summary="AI 出题：上传文件生成试卷题目")
async def generate_exam_questions(
    file: UploadFile = File(..., description="上传的文件（支持 .docx, .txt）"),
    service: AiChatService = Depends(get_ai_chat_service),
):
    """上传培训文件，AI 自动识别内容并生成选择题和判断题."""
    if not file.content_type or file.content_type not in _SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file.content_type}，仅支持 docx 和 txt",
        )

    file_type = _SUPPORTED_MIME_TYPES[file.content_type]
    file_bytes = await file.read()

    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")

    try:
        file_content = _extract_text_from_file(file_bytes, file_type)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {exc}") from exc

    if len(file_content.strip()) < 50:
        raise HTTPException(status_code=400, detail="文件内容过短，无法生成题目")

    try:
        result = await _call_moonshot_for_exam(service.client, file_content, service.model)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500, detail=f"AI 返回格式解析失败: {exc}"
        ) from exc
    except Exception as exc:
        logger.exception("AI 出题失败")
        raise HTTPException(status_code=500, detail=f"AI 出题失败: {exc}") from exc

    return success_response(
        data=result.model_dump(mode="json"),
        message="试卷题目生成成功",
    )


@router.post("/exam/export", summary="导出试卷 Word 文档")
async def export_exam(
    request: ExamExportRequest,
):
    """根据试卷数据生成并下载 Word 文档."""
    try:
        buffer = generate_exam_docx(request)
    except Exception as exc:
        logger.exception("试卷导出失败")
        raise HTTPException(status_code=500, detail=f"试卷导出失败: {exc}") from exc

    def _iterfile():
        buffer.seek(0)
        yield buffer.read()

    safe_title = re.sub(r'[\\/:*?"<>|]', "_", request.title) or "试卷"
    filename = f"{safe_title}.docx"
    # RFC 5987 encoding for non-ASCII filenames in Content-Disposition
    encoded_filename = quote(filename, safe="")

    return StreamingResponse(
        _iterfile(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"
        },
    )
