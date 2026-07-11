"""偏差填报人提醒服务

检查偏差任务并向填报人发送飞书提醒：
- 未完成任务：发送督促提醒
- 已完成任务：发送完成通知
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import spawn_task
from app.modules.quality.qms.feishu_service import get_feishu_config_from_db
from app.platform.notification.feishu_client_config import FeishuClient

logger = logging.getLogger(__name__)


class DeviationReporterReminderService:
    """偏差填报人提醒服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_and_remind(self) -> dict[str, Any]:
        """检查偏差任务并发送提醒"""
        # 获取所有未完成的偏差任务（包含填报人信息）
        unfinished_deviations = await self._get_unfinished_deviations()

        # 按填报人分组未完成任务
        unfinished_grouped = self._group_by_reporter(unfinished_deviations)

        # 获取飞书配置
        feishu_config = await get_feishu_config_from_db()
        if not feishu_config or not feishu_config.get("app_id"):
            logger.warning("飞书机器人配置未启用，跳过提醒")
            return {"unfinished": 0, "reminded": 0, "error": "飞书配置未启用"}

        client = FeishuClient(feishu_config["app_id"], feishu_config["app_secret"])

        reminded_count = 0

        # 发送未完成任务的督促提醒
        for reporter_open_id, items in unfinished_grouped.items():
            if not reporter_open_id:
                continue

            try:
                await self._send_urge_reminder(client, reporter_open_id, items)
                reminded_count += 1
            except Exception as e:
                logger.error(f"发送督促提醒给 {reporter_open_id} 失败: {e}")

        return {
            "unfinished_total": len(unfinished_deviations),
            "unfinished_reporters": len(unfinished_grouped),
            "reminded": reminded_count,
        }

    async def _get_unfinished_deviations(self) -> list[dict[str, Any]]:
        """获取未完成的偏差任务"""
        result = await self.session.execute(
            text("""
                SELECT 
                    id, deviation_no, theme, status, reporter,
                    reporter_feishu_open_id, deviation_type, urgency_level, created_at
                FROM qms.qms_deviation
                WHERE is_deleted = FALSE
                  AND status != 'completed'
                  AND reporter_feishu_open_id IS NOT NULL
                  AND reporter_feishu_open_id != ''
                ORDER BY created_at DESC
            """)
        )
        rows = result.fetchall()

        # 计算剩余天数
        from datetime import timedelta

        now = datetime.now()
        deadline_days = 30

        deviations = []
        for row in rows:
            created_at = row[8]
            remaining_days = 0
            if created_at:
                deadline = created_at + timedelta(days=deadline_days)
                remaining_days = max(0, (deadline - now).days)

            deviations.append(
                {
                    "id": row[0],
                    "deviation_no": row[1],
                    "theme": row[2],
                    "status": row[3],
                    "reporter": row[4],
                    "reporter_open_id": row[5],
                    "deviation_type": row[6],
                    "urgency_level": row[7],
                    "remaining_days": remaining_days,
                }
            )

        return deviations

    def _group_by_reporter(
        self, deviations: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """按填报人分组"""
        grouped = {}
        for d in deviations:
            open_id = d["reporter_open_id"]
            if open_id not in grouped:
                grouped[open_id] = []
            grouped[open_id].append(d)
        return grouped

    def _get_status_label(self, status: str) -> str:
        """获取状态中文标签"""
        status_labels = {
            "draft": "草稿",
            "basic_completed": "基础完成",
            "detail_completed": "详情完成",
            "completed": "已完成",
        }
        return status_labels.get(status, status)

    def _get_type_label(self, deviation_type: str) -> str:
        """获取偏差类型中文标签"""
        type_labels = {
            "ipc_defect": "过程控制（IPC）缺陷",
            "foreign_object": "外来异物（有形）",
            "calibration_maintenance": "校验/预防维修",
            "mixup": "混淆",
            "material_quality_defect": "物料质量缺陷",
            "personnel_error": "人员失误",
            "oos_result": "超标检验结果",
            "documentation_defect": "文件记录缺陷",
            "equipment_failure": "设备故障/过程中断",
            "environment": "环境",
            "other": "其它",
        }
        return type_labels.get(deviation_type, deviation_type or "未知")

    async def _send_urge_reminder(
        self,
        client: FeishuClient,
        reporter_open_id: str,
        deviations: list[dict[str, Any]],
    ):
        """发送督促提醒给填报人（针对未完成的任务）"""
        count = len(deviations)

        # 构建偏差列表
        deviation_list_md = ""
        for i, d in enumerate(deviations[:5], 1):  # 最多显示5条
            status_label = self._get_status_label(d["status"])
            remaining = d.get("remaining_days", 0)
            deviation_list_md += f"{i}. **{d['deviation_no']}** - {d['theme'][:20]}...\n   当前状态：{status_label} | 剩余完成天数：{remaining}天\n"

        if count > 5:
            deviation_list_md += f"\n...还有 {count - 5} 条偏差任务待处理"

        content = f"""**📋 偏差任务待处理提醒**

您有 **{count}** 条偏差任务尚未完成，请及时处理：

{deviation_list_md}

请登录系统查看详情并继续填写。"""

        card_content = {
            "config": {"wide_screen_mode": True},
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": content}}
            ],
        }

        await client.send_card_message(
            receive_id_type="open_id",
            receive_id=reporter_open_id,
            card_content=card_content,
        )

        logger.info(f"已发送督促提醒给 {reporter_open_id}，共 {count} 条待处理任务")


def send_completion_notification(
    session: AsyncSession, reporter_open_id: str, deviation_no: str, theme: str
):
    """发送任务完成通知（供偏差完成时调用）"""

    async def _send():
        feishu_config = await get_feishu_config_from_db()
        if not feishu_config or not feishu_config.get("app_id"):
            logger.warning("飞书机器人配置未启用，跳过完成通知")
            return

        client = FeishuClient(feishu_config["app_id"], feishu_config["app_secret"])

        content = f"""**✅ 偏差任务已完成**

您提交的偏差单 **偏差单 {deviation_no}** 已完成全部填写流程！

**偏差主题：** {theme}

感谢您的配合，偏差报告已归档。如有疑问，请联系QA人员。"""

        card_content = {
            "config": {"wide_screen_mode": True},
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": content}}
            ],
        }

        await client.send_card_message(
            receive_id_type="open_id",
            receive_id=reporter_open_id,
            card_content=card_content,
        )

        logger.info(f"已发送完成通知给 {reporter_open_id}，偏差单 {deviation_no}")

    spawn_task(_send())
