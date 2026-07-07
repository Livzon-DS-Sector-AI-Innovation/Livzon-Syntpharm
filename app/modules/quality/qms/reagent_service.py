"""质量检验试剂管理 Service

提供质量检验模块试剂/标准品管理的业务逻辑。
"""

import uuid
import json
import re
from datetime import date, datetime
from typing import Optional, Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.ai.service import AiLogService


class ReagentService:
    """试剂管理服务"""

    # AI识别提示词
    SYSTEM_PROMPT_REAGENT_LABEL = """你是制药QC实验室试剂标签识别专家。
请仔细分析试剂/标准品标签图片，提取以下信息：
1. 试剂名称（reagent_name）
2. 批号（lot_no）
3. 生产厂家（manufacturer）
4. 生产日期（production_date，格式 YYYY-MM-DD，如无法识别则返回 null）
5. 有效期（expiration_date，格式 YYYY-MM-DD，如无法识别则返回 null）
6. 含量/纯度（content，从以下选项中选择最匹配的）：
   - （A溶剂）
   - （B滴定剂）
   - /
   - GC
   - GR(优级纯)
   - HPLC
   - HPLC梯度级
   - IND（指示剂）
   - 单元素标准溶液
   - 分析纯AR
   - 分析纯II类ARII
   - 光谱纯SP
   - 化学纯CP
   - 缓冲液标准品
   - 基准试剂
   - 色谱HPLC级
   - 色谱级
   - 试剂级
   - 液相色谱纯
7. 规格（含单位，如 500g、1Kg、250ml、1L 等）

如果无法从图片中识别某些信息，请标注为 null。含量如果没有匹配的请填"/"。
请以JSON格式返回：
{
    "reagent_name": "...",
    "lot_no": "...",
    "manufacturer": "...",
    "production_date": "...",
    "expiration_date": "...",
    "content": "...",
    "specification": "...",
    "confidence": 0.85
}
confidence 表示识别置信度（0-1之间）。
"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_reagents(
        self,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取试剂列表"""
        # 构建WHERE条件
        conditions = []
        params: dict[str, Any] = {}

        if keyword:
            conditions.append("""
                (reagent_name ILIKE :keyword
                OR lot_no ILIKE :keyword
                OR reagent_no ILIKE :keyword
                OR manufacturer ILIKE :keyword)
            """)
            params['keyword'] = f"%{keyword}%"

        if category:
            conditions.append("category = :category")
            params['category'] = category

        if status:
            conditions.append("status = :status")
            params['status'] = status

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 查询总数
        count_sql = text(f"""
            SELECT COUNT(*)
            FROM qms.qms_reagent_quality
            WHERE {where_clause}
        """)
        total_result = await self.session.execute(count_sql, params)
        total = total_result.scalar() or 0

        # 分页查询
        offset = (page - 1) * page_size
        params['offset'] = offset
        params['limit'] = page_size

        query_sql = text(f"""
            SELECT *
            FROM qms.qms_reagent_quality
            WHERE {where_clause}
            ORDER BY created_at DESC
            OFFSET :offset LIMIT :limit
        """)

        result = await self.session.execute(query_sql, params)
        rows = result.fetchall()
        columns = result.keys()

        # 转换为字典列表
        reagents = [dict(zip(columns, row)) for row in rows]

        return reagents, total

    async def get_reagent_by_id(self, reagent_id: str) -> Optional[dict[str, Any]]:
        """根据ID获取试剂详情"""
        query_sql = text("""
            SELECT *
            FROM qms.qms_reagent_quality
            WHERE id = :id
        """)
        result = await self.session.execute(query_sql, {"id": reagent_id})
        row = result.fetchone()

        if not row:
            return None

        columns = result.keys()
        return dict(zip(columns, row))

    async def get_next_incoming_lot_no(self, target_date: date = None) -> str:
        """获取当天的下一个入场批号
        格式：年月日9序号
        例如：260609901 表示2026年6月9日第1个
        """
        if target_date is None:
            target_date = date.today()

        # 格式化日期部分：YYMMDD (例如 260609)
        date_str = target_date.strftime('%y%m%d')

        # 查询当天最大的入场批号
        query_sql = text("""
            SELECT incoming_lot_no
            FROM qms.qms_reagent_quality
            WHERE incoming_lot_no LIKE :prefix
            ORDER BY incoming_lot_no DESC
            LIMIT 1
        """)
        prefix = f"{date_str}9%"
        
        result = await self.session.execute(query_sql, {"prefix": prefix})
        row = result.fetchone()

        next_seq = 1
        if row and row[0]:
            # 解析最大序号
            last_lot_no = str(row[0])
            if len(last_lot_no) >= 9:
                try:
                    # 格式: YYMMDD9XX，取最后2位
                    last_seq = int(last_lot_no[-2:])
                    next_seq = last_seq + 1
                except (ValueError, IndexError):
                    next_seq = 1

        # 生成新的入场批号：年月日9序号(2位)，如 260609901
        return f"{date_str}9{next_seq:02d}"

    async def create_reagent(
        self,
        data: dict,
        operator: str = "system",
    ) -> dict[str, Any]:
        """创建试剂记录"""
        reagent_id = str(uuid.uuid4())

        insert_sql = text("""
            INSERT INTO qms.qms_reagent_quality (
                id, reagent_label_urls, reagent_name, arrival_date,
                production_date, lot_no, incoming_lot_no, expiration_date,
                specification, category, reagent_no, content, manufacturer,
                quantity, unit, status, created_by
            ) VALUES (
                :id, :reagent_label_urls, :reagent_name, :arrival_date,
                :production_date, :lot_no, :incoming_lot_no, :expiration_date,
                :specification, :category, :reagent_no, :content, :manufacturer,
                :quantity, :unit, :status, :created_by
            )
            RETURNING *
        """)

        params = {
            "id": reagent_id,
            "reagent_label_urls": data.get("reagent_label_urls", []),
            "reagent_name": data["reagent_name"],
            "arrival_date": data["arrival_date"],
            "production_date": data.get("production_date"),
            "lot_no": data["lot_no"],
            "incoming_lot_no": data.get("incoming_lot_no"),
            "expiration_date": data["expiration_date"],
            "specification": data.get("specification"),
            "category": data["category"],
            "reagent_no": data.get("reagent_no"),
            "content": data.get("content"),
            "manufacturer": data.get("manufacturer"),
            "quantity": data.get("quantity", 0),
            "unit": data["unit"],
            "status": data.get("status", "available"),
            "created_by": operator,
        }

        result = await self.session.execute(insert_sql, params)
        await self.session.commit()

        row = result.fetchone()
        columns = result.keys()
        return dict(zip(columns, row))

    async def update_reagent(
        self,
        reagent_id: str,
        data: dict,
    ) -> Optional[dict[str, Any]]:
        """更新试剂记录"""
        # 构建更新字段
        update_fields = []
        params: dict[str, Any] = {"id": reagent_id}

        for key, value in data.items():
            if value is not None and key not in ["id", "created_at"]:
                update_fields.append(f"{key} = :{key}")
                params[key] = value

        if not update_fields:
            return await self.get_reagent_by_id(reagent_id)

        update_fields.append("updated_at = NOW()")

        update_sql = text(f"""
            UPDATE qms.qms_reagent_quality
            SET {', '.join(update_fields)}
            WHERE id = :id
            RETURNING *
        """)

        result = await self.session.execute(update_sql, params)
        await self.session.commit()

        row = result.fetchone()
        if not row:
            return None

        columns = result.keys()
        return dict(zip(columns, row))

    async def delete_reagent(self, reagent_id: str) -> bool:
        """删除试剂记录"""
        delete_sql = text("""
            DELETE FROM qms.qms_reagent_quality
            WHERE id = :id
        """)
        result = await self.session.execute(delete_sql, {"id": reagent_id})
        await self.session.commit()

        return result.rowcount > 0

    async def recognize_label(
        self,
        image_urls: list[str],
        operator: str = "system",
    ) -> dict:
        """AI识别试剂标签图片"""
        from app.platform.ai.minimax_util import get_vision_util

        vision_util = get_vision_util()

        # 调用MiniMax VL模型识别图片
        ai_response = None
        try:
            ai_response = await vision_util.recognize_image(
                image_urls=image_urls,
                prompt=self.SYSTEM_PROMPT_REAGENT_LABEL,
            )

            # 解析AI响应
            # MiniMax-M3 可能返回包含 思考过程，需要提取JSON部分
            import sys

            def safe_print(msg):
                """安全打印，避免GBK编码问题"""
                try:
                    print(msg)
                except Exception:
                    print(repr(msg[:100]) if len(msg) > 100 else repr(msg))

            safe_print(f"[DEBUG] AI响应长度: {len(ai_response)}")
            safe_print(f"[DEBUG] AI响应前100字符: {repr(ai_response[:100])}")
            try:
                # 尝试直接解析JSON
                result = json.loads(ai_response)
                safe_print(f"[DEBUG] 直接解析成功: {result}")
            except json.JSONDecodeError:
                # 如果直接解析失败，清理思考过程标签后提取JSON
                safe_print("[DEBUG] 直接解析失败，尝试清理思考标签...")
                # 清理思考过程标签（包括嵌套情况）
                clean_response = ai_response
                # 循环清理所有 思考标签
                while '<think>' in clean_response and '' in clean_response:
                    clean_response = re.sub(r'<think>[\s\S]*?', '', clean_response)
                clean_response = clean_response.strip()
                safe_print(f"[DEBUG] 清理后前100字符: {repr(clean_response[:100])}")

                # 查找JSON代码块（可能用```json包裹）
                json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', clean_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # 尝试直接在清理后的文本中找JSON对象
                    json_match = re.search(r'\{[\s\S]*\}', clean_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = clean_response

                safe_print(f"[DEBUG] 提取的JSON前100字符: {repr(json_str[:100])}")
                try:
                    result = json.loads(json_str)
                    safe_print(f"[DEBUG] JSON提取解析成功")
                except json.JSONDecodeError as e2:
                    safe_print(f"[DEBUG] JSON提取解析失败: {e2}")
                    result = {
                        "reagent_name": None,
                        "lot_no": None,
                        "manufacturer": None,
                        "production_date": None,
                        "expiration_date": None,
                        "category": None,
                        "specification": None,
                        "confidence": 0.0,
                    }

            # 保存AI日志（解析成功后再保存，避免编码问题中断流程）
            try:
                ai_log_service = AiLogService(self.session)
                await ai_log_service.save_ai_log(
                    operate_type="试剂标签识别",
                    operator=operator,
                    system_prompt=self.SYSTEM_PROMPT_REAGENT_LABEL,
                    user_input=f"图片URLs: {image_urls}",
                    ai_response=ai_response[:1000] if ai_response else None,  # 截断避免过长
                )
            except Exception as log_err:
                safe_print(f"[DEBUG] 保存AI日志失败（不影响结果）")

            return result

        except Exception as e:
            # 保存错误日志
            safe_print(f"[DEBUG] AI识别异常: {str(e)[:100]}")
            try:
                ai_log_service = AiLogService(self.session)
                await ai_log_service.save_ai_log(
                    operate_type="试剂标签识别",
                    operator=operator,
                    system_prompt=self.SYSTEM_PROMPT_REAGENT_LABEL,
                    user_input=f"图片URLs: {image_urls}",
                    error_message=str(e),
                )
            except Exception:
                pass
            raise