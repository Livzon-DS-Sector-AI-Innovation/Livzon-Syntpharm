"""试剂提醒服务

实现试剂库存不足时的飞书提醒功能
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.reagent_reminder_config import ReagentReminderConfig
from app.platform.notification.feishu_client_config import FeishuClient

logger = logging.getLogger(__name__)


class ReagentReminderService:
    """试剂提醒服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_config(self) -> ReagentReminderConfig | None:
        """获取提醒配置"""
        result = await self.session.execute(select(ReagentReminderConfig).limit(1))
        return result.scalar_one_or_none()

    async def create_or_update_config(
        self,
        feishu_app_id: str,
        feishu_app_secret: str,
        feishu_chat_id: str,
        low_stock_threshold: int = 2,
        is_enabled: bool = True,
    ) -> ReagentReminderConfig:
        """创建或更新提醒配置"""
        config = await self.get_config()

        if config:
            config.feishu_app_id = feishu_app_id
            config.feishu_app_secret = feishu_app_secret
            config.feishu_chat_id = feishu_chat_id
            config.low_stock_threshold = low_stock_threshold
            config.is_enabled = is_enabled
            config.updated_at = datetime.utcnow()
        else:
            config = ReagentReminderConfig(
                id=str(uuid.uuid4()),
                feishu_app_id=feishu_app_id,
                feishu_app_secret=feishu_app_secret,
                feishu_chat_id=feishu_chat_id,
                low_stock_threshold=low_stock_threshold,
                is_enabled=is_enabled,
                created_at=datetime.utcnow(),
            )
            self.session.add(config)

        await self.session.commit()
        await self.session.refresh(config)
        return config

    async def get_item_reminder_config(self, reagent_name: str) -> dict[str, Any] | None:
        """获取单个试剂的提醒配置"""
        result = await self.session.execute(
            text("""
                SELECT id, reagent_name, is_enabled, created_at, updated_at
                FROM qms.qms_reagent_item_reminder_config
                WHERE reagent_name = :reagent_name
            """),
            {"reagent_name": reagent_name},
        )
        row = result.fetchone()
        if row:
            return {
                "id": row[0],
                "reagent_name": row[1],
                "is_enabled": row[2],
                "created_at": str(row[3]) if row[3] else None,
                "updated_at": str(row[4]) if row[4] else None,
            }
        return None

    async def set_item_reminder_enabled(self, reagent_name: str, is_enabled: bool) -> dict[str, Any]:
        """设置单个试剂的提醒开关"""
        # 检查是否已存在
        existing = await self.get_item_reminder_config(reagent_name)

        if existing:
            await self.session.execute(
                text("""
                    UPDATE qms.qms_reagent_item_reminder_config
                    SET is_enabled = :is_enabled, updated_at = CURRENT_TIMESTAMP
                    WHERE reagent_name = :reagent_name
                """),
                {"is_enabled": is_enabled, "reagent_name": reagent_name},
            )
        else:
            await self.session.execute(
                text("""
                    INSERT INTO qms.qms_reagent_item_reminder_config (id, reagent_name, is_enabled)
                    VALUES (:id, :reagent_name, :is_enabled)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "reagent_name": reagent_name,
                    "is_enabled": is_enabled,
                },
            )

        await self.session.commit()
        return {"code": 200, "message": "设置成功"}

    async def get_all_item_configs(self) -> dict[str, Any]:
        """获取所有单个试剂的提醒配置"""
        result = await self.session.execute(
            text("SELECT reagent_name, is_enabled FROM qms.qms_reagent_item_reminder_config")
        )
        rows = result.fetchall()
        return {row[0]: row[1] for row in rows}

    async def get_low_stock_reagents(self, threshold: int = 2) -> list[dict[str, Any]]:
        """获取库存不足的试剂（按名称分组统计）"""
        # 获取所有单个试剂的提醒配置
        item_configs = await self.get_all_item_configs()

        query = text("""
            SELECT
                reagent_name,
                COUNT(*) as count,
                STRING_AGG(DISTINCT status, ', ') as statuses,
                STRING_AGG(DISTINCT unit, ', ') as units,
                MAX(arrival_date) as latest_arrival
            FROM qms.qms_reagent_quality
            WHERE status NOT IN ('scrap', 'used_up', 'expired')
            GROUP BY reagent_name
            HAVING COUNT(*) < :threshold
            ORDER BY COUNT(*) ASC, reagent_name
        """)

        result = await self.session.execute(query, {"threshold": threshold})
        rows = result.fetchall()

        return [
            {
                "reagent_name": row[0],
                "count": row[1],
                "statuses": row[2],
                "units": row[3],
                "latest_arrival": str(row[4]) if row[4] else None,
                "is_enabled": item_configs.get(row[0], True),  # 默认启用
            }
            for row in rows
        ]

    async def check_and_remind(self) -> dict[str, Any]:
        """检查库存并发送提醒"""
        config = await self.get_config()

        if not config:
            return {"code": 404, "message": "提醒配置未设置", "data": None}

        if not config.is_enabled:
            return {"code": 200, "message": "提醒功能已禁用", "data": None}

        if not config.feishu_app_id or not config.feishu_app_secret or not config.feishu_chat_id:
            return {"code": 400, "message": "飞书配置不完整", "data": None}

        # 获取库存不足的试剂
        low_stock_items = await self.get_low_stock_reagents(config.low_stock_threshold)

        if not low_stock_items:
            return {"code": 200, "message": "库存充足，无需提醒", "data": {"count": 0}}

        # 过滤出启用了提醒的试剂
        enabled_items = [item for item in low_stock_items if item.get("is_enabled", True)]

        if not enabled_items:
            return {
                "code": 200,
                "message": "所有试剂提醒均已关闭，无需提醒",
                "data": {"count": 0, "total": len(low_stock_items), "filtered": True},
            }

        # 构建提醒内容（只包含启用了提醒的试剂）
        content = self._build_reminder_content(enabled_items, len(low_stock_items))

        try:
            # 发送飞书提醒
            client = FeishuClient(config.feishu_app_id, config.feishu_app_secret)
            await client.send_card_message(
                receive_id_type="chat_id",
                receive_id=config.feishu_chat_id,
                card_content=content,
            )

            # 更新提醒历史
            config.last_remind_time = datetime.utcnow()
            config.last_remind_content = json.dumps(enabled_items, ensure_ascii=False)
            config.updated_at = datetime.utcnow()
            await self.session.commit()

            return {
                "code": 200,
                "message": "提醒发送成功",
                "data": {
                    "count": len(enabled_items),
                    "total": len(low_stock_items),
                    "items": enabled_items,
                },
            }
        except Exception as e:
            logger.error(f"发送飞书提醒失败: {str(e)}")
            return {"code": 500, "message": f"发送失败: {str(e)}", "data": None}

    def _build_reminder_content(
        self,
        items: list[dict[str, Any]],
        total_count: int = None,  # type: ignore[assignment]
    ) -> dict[str, Any]:
        """构建飞书卡片内容"""
        # 构建表格内容
        table_rows = []
        for item in items[:20]:  # 最多显示20条
            table_rows.append(f"| {item['reagent_name']} | {item['count']} | {item['statuses']} |")

        content_lines = [
            "⚠️ **试剂库存不足提醒**",
            "",
            f"共有 **{len(items)}** 种试剂库存不足（低于阈值），请及时补充：",
            "",
            "| 试剂名称 | 数量 | 状态 |",
            "| --- | --- | --- |",
        ]
        content_lines.extend(table_rows)

        if len(items) > 20:
            content_lines.append("| ... | ... | ... |")
            content_lines.append(f"| 共 {len(items)} 种试剂库存不足 | | |")

        # 如果有被过滤的试剂，添加说明
        if total_count and total_count > len(items):
            content_lines.extend(
                [
                    "",
                    f"📝 说明：已过滤 {total_count - len(items)} 种已关闭提醒的试剂",
                ]
            )

        content_lines.extend(
            [
                "",
                f"⏰ 提醒时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ]
        )

        return {
            "config": {"wide_screen_mode": True},
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "\n".join(content_lines),
                    },
                }
            ],
        }


async def run_reagent_reminder_check(session: AsyncSession) -> dict[str, Any]:
    """独立的提醒检查函数（用于定时任务调用）"""
    service = ReagentReminderService(session)
    return await service.check_and_remind()
