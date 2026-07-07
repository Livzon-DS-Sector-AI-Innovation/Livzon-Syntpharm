"""AI 能力服务层

提供 AI 日志保存等通用 AI 相关服务。
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.ai.models import QmsAiLog

logger = logging.getLogger(__name__)


class AiLogService:
    """AI 日志服务

    提供 AI 交互日志的保存和查询功能。
    """

    def __init__(self, session: AsyncSession):
        """初始化 AI 日志服务

        Args:
            session: 数据库会话
        """
        self.session = session

    async def save_ai_log(
        self,
        operate_type: str,
        operator: str,
        system_prompt: str,
        user_input: str,
        ai_response: str | None = None,
        error_message: str | None = None,
        bill_no: str | None = None,
        tokens_used: int | None = None,
        latency_ms: int | None = None,
    ) -> str:
        """保存 AI 交互日志

        Args:
            operate_type: 操作类型（如：试剂领用辅助、试剂报废辅助）
            operator: 操作人账号
            system_prompt: 系统提示词
            user_input: 用户输入内容
            ai_response: AI 返回内容
            error_message: 错误信息
            bill_no: 关联单据编号
            tokens_used: 使用的 token 数量
            latency_ms: 响应耗时（毫秒）

        Returns:
            日志记录 ID
        """
        log_entry = QmsAiLog(
            id=uuid.uuid4(),
            bill_no=bill_no,
            operate_type=operate_type,
            operator=operator,
            system_prompt=system_prompt,
            user_input=user_input,
            ai_response=ai_response,
            error_message=error_message,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            created_at=datetime.now(),
        )
        self.session.add(log_entry)
        await self.session.flush()
        logger.info(
            f"AI 日志保存成功: operate_type={operate_type}, "
            f"operator={operator}, log_id={log_entry.id}"
        )
        return str(log_entry.id)

    async def list_logs(
        self,
        operate_type: str | None = None,
        operator: str | None = None,
        bill_no: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[QmsAiLog], int]:
        """查询 AI 日志列表

        Args:
            operate_type: 操作类型过滤
            operator: 操作人过滤
            bill_no: 单据编号过滤
            start_date: 开始时间过滤
            end_date: 结束时间过滤
            page: 页码
            page_size: 每页数量

        Returns:
            (日志列表, 总数)
        """
        params = {}
        conditions = []

        if operate_type:
            conditions.append("operate_type = :operate_type")
            params["operate_type"] = operate_type
        if operator:
            conditions.append("operator = :operator")
            params["operator"] = operator
        if bill_no:
            conditions.append("bill_no = :bill_no")
            params["bill_no"] = bill_no
        if start_date:
            conditions.append("created_at >= :start_date")
            params["start_date"] = start_date
        if end_date:
            conditions.append("created_at <= :end_date")
            params["end_date"] = end_date

        # 构建WHERE子句
        if conditions:
            where_clause = " AND ".join(conditions)
        else:
            where_clause = "1=1"

        # 查询SQL - 始终按创建时间倒序
        query_sql = text(f"""
            SELECT id, bill_no, operate_type, operator, system_prompt, user_input, 
                   ai_response, error_message, tokens_used, latency_ms, created_at
            FROM qms.qms_ai_log
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        # 统计SQL
        count_sql = text(f"SELECT COUNT(*) FROM qms.qms_ai_log WHERE {where_clause}")

        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        result = await self.session.execute(query_sql, params)
        logs = result.fetchall()

        count_result = await self.session.execute(count_sql, params)
        total = count_result.scalar() or 0

        return logs, total


def log_ai_interaction(
    service: AiLogService,
    operate_type: str,
    operator: str,
    system_prompt: str,
    user_input: str,
    ai_response: str | None = None,
    error: Exception | None = None,
    bill_no: str | None = None,
) -> str:
    """AI 交互日志记录辅助函数

    Args:
        service: AiLogService 实例
        operate_type: 操作类型
        operator: 操作人账号
        system_prompt: 系统提示词
        user_input: 用户输入
        ai_response: AI 响应
        error: 异常对象
        bill_no: 单据编号

    Returns:
        日志记录 ID
    """
    import asyncio
    import concurrent.futures

    def _save_log():
        return asyncio.new_event_loop().run_until_complete(
            service.save_ai_log(
                operate_type=operate_type,
                operator=operator,
                system_prompt=system_prompt,
                user_input=user_input,
                ai_response=ai_response,
                error_message=str(error) if error else None,
                bill_no=bill_no,
            )
        )

    with concurrent.futures.ThreadPoolExecutor() as pool:
        return pool.submit(_save_log).result()