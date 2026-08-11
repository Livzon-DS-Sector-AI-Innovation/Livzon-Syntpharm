"""AI Parser API endpoints for experiment record parsing."""

import logging
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.deps import RequiredUser
from app.core.response import success_response
from app.modules.research.ai_parser.schemas import (
    ExperimentParseResponse,
    ParameterParseRequest,
    ParameterParseResponse,
)
from app.modules.research.ai_parser.service import (
    parse_experiment_record,
    parse_process_parameters,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI解析"])


@router.post("/parse-experiment", summary="解析实验记录文件")
async def post(
    current_user: RequiredUser,
    file: UploadFile = File(...),
    parse_type: str = Form(..., description="解析类型: lab_confirmation 或 scale_up"),
) -> Any:
    """上传实验记录文件(PDF/Word/图片/文本),AI自动提取关键信息
    
    Args:
        file: 上传的实验记录文件
        parse_type: 解析类型
    
    Returns:
        解析结果
    """
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")

    if parse_type not in ["lab_confirmation", "scale_up"]:
        raise HTTPException(400, f"无效的解析类型: {parse_type}")

    try:
        # 读取文件内容
        content = await file.read()

        # 根据文件类型解析文本
        text_content = await _extract_text_from_file(content, file.filename)

        # 调用AI解析服务
        result = await parse_experiment_record(text_content, parse_type)

        return success_response(
            data=result.model_dump(), message="实验记录解析完成"
        )

    except ValueError as e:
        logger.warning(f"参数错误: {e}")
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"实验记录解析失败: {e}", exc_info=True)
        raise HTTPException(500, f"AI解析失败: {str(e)}")


@router.post("/parse-parameters", summary="解析工艺参数文本")
async def api_parse_parameters(
    current_user: RequiredUser,
    request: ParameterParseRequest,
) -> Any:
    """从文本中提取工艺参数
    
    Args:
        request: 包含文本内容和解析类型的请求
    
    Returns:
        解析出的工艺参数
    """
    try:
        result = await parse_process_parameters(request.content, request.parse_type)

        return success_response(
            data=result.model_dump(), message="工艺参数解析完成"
        )

    except Exception as e:
        logger.error(f"工艺参数解析失败: {e}", exc_info=True)
        raise HTTPException(500, f"AI解析失败: {str(e)}")


async def _extract_text_from_file(content: bytes, filename: str) -> str:
    """从文件中提取文本内容
    
    Args:
        content: 文件二进制内容
        filename: 文件名
    
    Returns:
        提取的文本内容
    """
    import io

    # 根据文件扩展名选择解析方式
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext in ["txt", "md"]:
        # 文本文件直接解码
        return content.decode("utf-8", errors="ignore")

    elif ext == "pdf":
        # PDF文件使用 pdfplumber
        try:
            import pdfplumber

            pdf_file = io.BytesIO(content)
            with pdfplumber.open(pdf_file) as pdf:
                text_pages = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_pages.append(text)
                return "\n".join(text_pages)
        except ImportError:
            logger.warning("pdfplumber未安装,尝试简单文本提取")
            return content.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"PDF解析失败: {e}")
            return content.decode("utf-8", errors="ignore")

    elif ext in ["docx", "doc"]:
        # Word文件使用 python-docx
        try:
            from docx import Document

            doc_file = io.BytesIO(content)
            doc = Document(doc_file)
            text_parts = [para.text for para in doc.paragraphs if para.text]
            return "\n".join(text_parts)
        except ImportError:
            logger.warning("python-docx未安装,尝试简单文本提取")
            return content.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Word解析失败: {e}")
            return content.decode("utf-8", errors="ignore")

    elif ext in ["jpg", "jpeg", "png"]:
        # 图片文件使用OCR
        try:
            from paddleocr import PaddleOCR

            # 初始化OCR(首次调用会下载模型)
            ocr = PaddleOCR(use_angle_cls=True, lang="ch")

            # 保存图片到临时文件
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            # 执行OCR
            result = ocr.ocr(tmp_path, cls=True)

            # 清理临时文件
            import os

            os.unlink(tmp_path)

            # 提取文本
            text_lines = []
            if result and result[0]:
                for line in result[0]:
                    if line and len(line) >= 2:
                        text_lines.append(line[1][0])

            return "\n".join(text_lines)

        except ImportError:
            logger.warning("PaddleOCR未安装,无法解析图片")
            raise HTTPException(
                400, "图片解析需要安装PaddleOCR,请联系管理员"
            )
        except Exception as e:
            logger.error(f"图片OCR失败: {e}")
            raise HTTPException(500, f"图片解析失败: {str(e)}")

    else:
        # 其他格式尝试作为文本处理
        return content.decode("utf-8", errors="ignore")
