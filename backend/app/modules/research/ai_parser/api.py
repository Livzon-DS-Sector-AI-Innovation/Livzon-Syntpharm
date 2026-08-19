"""AI Parser API endpoints for experiment record and process parameter parsing."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.core.deps import RequiredUser
from app.core.response import error_response, success_response

from .schemas import (
    ExperimentParseRequest,
    ExperimentParseResponse,
    ParameterParseRequest,
    ParameterParseResponse,
)
from .service import parse_experiment_record, parse_process_parameters

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["research-ai-parser"])


@router.post("/parse-experiment", summary="解析实验记录文件")
async def api_parse_experiment(
    request: ExperimentParseRequest,
    current_user: RequiredUser,
) -> JSONResponse:
    """
    解析实验记录文本内容，提取结构化数据。
    
    支持两种解析类型：
    - lab_confirmation: 小试工艺确认
    - scale_up: 放大生产
    
    返回包含置信度、结构化数据和警告信息的解析结果。
    """
    try:
        result = await parse_experiment_record(
            content=request.content,
            parse_type=request.parse_type,
        )
        
        return success_response(
            data=result.model_dump(),
            message="实验记录解析成功",
        )
    except ValueError as e:
        logger.warning(f"参数验证失败: {e}")
        return error_response(message=str(e), status_code=400)
    except Exception as e:
        logger.error(f"实验记录解析异常: {e}", exc_info=True)
        return error_response(message=f"解析失败: {str(e)}", status_code=500)


@router.post("/parse-parameters", summary="解析工艺参数文本")
async def api_parse_parameters(
    request: ParameterParseRequest,
    current_user: RequiredUser,
) -> JSONResponse:
    """
    从文本中提取工艺参数。
    
    支持从小试确认或放大生产的文本描述中提取关键工艺参数。
    返回结构化的参数字典和置信度评分。
    """
    try:
        result = await parse_process_parameters(
            content=request.content,
            parse_type=request.parse_type,
        )
        
        return success_response(
            data=result.model_dump(),
            message="工艺参数解析成功",
        )
    except ValueError as e:
        logger.warning(f"参数验证失败: {e}")
        return error_response(message=str(e), status_code=400)
    except Exception as e:
        logger.error(f"工艺参数解析异常: {e}", exc_info=True)
        return error_response(message=f"解析失败: {str(e)}", status_code=500)
