import logging
from typing import Any

from app.core.events import event_bus

logger = logging.getLogger(__name__)


async def _handle_work_order_created(data: dict[str, Any]) -> None:
    from app.modules.equipment.service.work_order import _notify_new_work_order  # type: ignore[attr-defined]

    await _notify_new_work_order(
        responsible_person_id=data["responsible_person_id"],
        work_order_no=data["work_order_no"],
        equipment_name=data["equipment_name"],
        order_type=data["order_type"],
        priority=data["priority"],
    )


async def _handle_work_order_assigned(data: dict[str, Any]) -> None:
    from app.modules.equipment.service.work_order import _notify_assignment  # type: ignore[attr-defined]

    await _notify_assignment(
        assignee_id=data["assignee_id"],
        work_order_no=data["work_order_no"],
        equipment_name=data["equipment_name"],
        order_type=data["order_type"],
        priority=data["priority"],
    )


async def _handle_work_order_verification_needed(data: dict[str, Any]) -> None:
    from app.modules.equipment.service.work_order import _notify_verification

    await _notify_verification(  # type: ignore[call-arg]
        feishu_user_id=data["feishu_user_id"],
        work_order_no=data["work_order_no"],
        equipment_name=data["equipment_name"],
        assignee_name=data["assignee_name"],
        priority=data["priority"],
        repair_detail=data["repair_detail"],
        work_order_id=data["work_order_id"],
        image_paths=data["image_paths"],
    )


async def _handle_work_order_rejected(data: dict[str, Any]) -> None:
    from app.modules.equipment.service.work_order import _notify_rejection  # type: ignore[attr-defined]

    await _notify_rejection(
        feishu_user_id=data["feishu_user_id"],
        work_order_no=data["work_order_no"],
        equipment_name=data["equipment_name"],
        remark=data["remark"],
    )


async def _handle_work_order_started(data: dict[str, Any]) -> None:
    from app.modules.equipment.feishu.notification import send_user_card

    await send_user_card(
        open_id=data["open_id"],
        title=data["title"],
        content=data["content"],
    )


async def _handle_work_order_claimed(data: dict[str, Any]) -> None:
    from app.platform.integrations.feishu.message import send_claim_notification

    await send_claim_notification(data["work_order_no"], data["user_name"])


event_bus.subscribe("equipment.work_order.created", _handle_work_order_created)
event_bus.subscribe("equipment.work_order.assigned", _handle_work_order_assigned)
event_bus.subscribe("equipment.work_order.verification_needed", _handle_work_order_verification_needed)
event_bus.subscribe("equipment.work_order.rejected", _handle_work_order_rejected)
event_bus.subscribe("equipment.work_order.started", _handle_work_order_started)
event_bus.subscribe("equipment.work_order.claimed", _handle_work_order_claimed)
