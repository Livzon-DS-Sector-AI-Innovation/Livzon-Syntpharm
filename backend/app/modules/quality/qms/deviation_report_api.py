"""偏差报告 API"""

import logging
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.responses import FileResponse

from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.exceptions import AppException, NotFoundException
from app.modules.quality.qms.deviation_report_schemas import OptimizeTextRequest, SaveHtmlRequest
from app.modules.quality.qms.deviation_schemas import DeviationApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deviation-report", tags=["偏差报告"])

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# 本文件位于 backend/app/modules/quality/qms/，parents[4] 才是 backend/
_UPLOAD_DIR = Path(__file__).resolve().parents[4] / "uploads" / "deviation_reports"

# 优化类型 → 提示词模板
_OPTIMIZE_PROMPTS: dict[str, str] = {
    "polish": """请对以下文本进行专业润色，保持原意，使语言更加流畅、专业、规范。

原文：
{text}

要求：
1. 保持原文的核心意思不变
2. 修正语法错误和表达不当之处
3. 使语言更加流畅、专业
4. 保持原有的格式和结构
5. 直接返回润色后的文本，不要添加任何解释说明

润色结果：""",
    "summarize": """请对以下文本进行简要总结。

原文：
{text}

要求：
1. 提取核心要点
2. 语言简洁明了
3. 直接返回总结内容，不要添加任何解释说明

总结结果：""",
    "expand": """请对以下文本进行适当扩展和详细说明。

原文：
{text}

要求：
1. 在保持原意的基础上进行扩展
2. 增加必要的细节和说明
3. 使内容更加完整和详尽
4. 直接返回扩展后的文本，不要添加任何解释说明

扩展结果：""",
    "simplify": """请对以下文本进行简化，使其更加简洁易懂。

原文：
{text}

要求：
1. 去除冗余表达
2. 使用简洁清晰的语言
3. 保持核心意思不变
4. 直接返回简化后的文本，不要添加任何解释说明

简化结果：""",
}

_OPTIMIZE_RESULT_PREFIXES = ("润色结果：", "总结结果：", "扩展结果：", "简化结果：")


def _upload_dir() -> Path:
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return _UPLOAD_DIR


def _resolve_uploaded_file(file_id: str) -> Path:
    """解析上传目录内的文件，拒绝任何目录穿越写法。"""
    if not file_id or Path(file_id).name != file_id:
        raise AppException(status_code=400, message="文件标识不合法")
    path = _upload_dir() / file_id
    if not path.is_file():
        raise NotFoundException(resource="原始文件")
    return path


# ============ Word 模板上传 API ============


@router.post("/upload", summary="上传并解析Word模板", response_model=DeviationApiResponse)
async def upload_report(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:deviation:update")),
    file: UploadFile = File(...),
) -> DeviationApiResponse:
    """上传Word文档并解析为HTML格式"""
    import mammoth  # type: ignore[import-untyped]

    if not file.filename or not file.filename.lower().endswith((".docx", ".doc")):
        raise AppException(status_code=400, message="仅支持 .docx 或 .doc 格式的Word文件")

    uploads_dir = _upload_dir()
    file_ext = Path(file.filename).suffix.lower()
    saved_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = uploads_dir / saved_filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        with open(file_path, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file)
            html_content = result.value
        warnings = [msg.message for msg in result.messages]
    except Exception:
        logger.exception("偏差报告解析失败: file_id=%s", saved_filename)
        file_path.unlink(missing_ok=True)
        raise AppException(status_code=500, message="文档解析失败，请确认文件是有效的 Word 文档") from None

    return DeviationApiResponse(
        message="文档解析成功",
        data={
            "file_id": saved_filename,
            "file_name": file.filename,
            "html_content": html_content,
            "file_path": f"/api/v1/quality/deviation-report/download?file_id={saved_filename}",
            "warnings": warnings,
        },
    )


@router.post("/save", summary="保存HTML内容为Word")
async def save_report(
    payload: SaveHtmlRequest,
    background_tasks: BackgroundTasks,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:deviation:update")),
) -> FileResponse:
    """将HTML内容保存为Word文档"""
    from bs4 import BeautifulSoup
    from docx import Document

    original_path = _resolve_uploaded_file(payload.file_id)

    doc = Document(str(original_path))
    soup = BeautifulSoup(payload.html_content, "html.parser")

    # 清除所有现有段落（保留样式）
    for para in doc.paragraphs:
        para.clear()  # type: ignore[no-untyped-call]

    for element in soup.children:
        tag = getattr(element, "name", None)
        if tag == "p":
            para = doc.add_paragraph()
            for child in getattr(element, "children", []):
                child_tag = getattr(child, "name", None)
                if child_tag:
                    if child_tag in ("b", "strong"):
                        run = para.add_run(child.get_text())
                        run.bold = True
                    elif child_tag == "i":
                        run = para.add_run(child.get_text())
                        run.italic = True
                    else:
                        para.add_run(child.get_text())
                else:
                    para.add_run(str(child))
        elif tag == "table":
            # 表格保持原样，跳过重建
            continue
        elif hasattr(element, "get_text") and element.get_text().strip():
            para = doc.add_paragraph()
            para.add_run(element.get_text())

    output_path = Path(tempfile.gettempdir()) / f"saved_report_{uuid.uuid4().hex}.docx"
    doc.save(str(output_path))

    # 响应发送完成后清理临时文件，避免 /tmp 持续增长
    background_tasks.add_task(output_path.unlink, missing_ok=True)

    return FileResponse(
        path=str(output_path),
        filename=f"偏差报告_{uuid.uuid4().hex[:8]}.docx",
        media_type=DOCX_MEDIA_TYPE,
    )


@router.get("/download", summary="下载原始Word文档")
async def download_report(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:deviation:read")),
    file_id: str = "",
) -> FileResponse:
    """下载原始Word文档"""
    file_path = _resolve_uploaded_file(file_id)
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=DOCX_MEDIA_TYPE,
    )


# ============ AI 优化接口 ============


@router.post("/ai/optimize", summary="AI优化文本", response_model=DeviationApiResponse)
async def optimize_text(
    payload: OptimizeTextRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:deviation:update")),
) -> DeviationApiResponse:
    """使用AI优化选中的文本"""
    from app.modules.quality.ai.minimax_util import get_vision_util

    template = _OPTIMIZE_PROMPTS.get(payload.optimize_type, _OPTIMIZE_PROMPTS["polish"])
    prompt = template.format(text=payload.text)

    try:
        vision_util = get_vision_util()
        result = await vision_util.recognize_text(prompt=prompt, max_tokens=4096)
    except Exception:
        logger.exception("偏差报告 AI 优化失败: optimize_type=%s", payload.optimize_type)
        raise AppException(status_code=500, message="AI 优化失败，请稍后重试") from None

    optimized = result.strip()
    for prefix in _OPTIMIZE_RESULT_PREFIXES:
        if optimized.startswith(prefix):
            optimized = optimized[len(prefix) :].lstrip()
            break

    return DeviationApiResponse(message="优化成功", data={"optimized_text": optimized})
