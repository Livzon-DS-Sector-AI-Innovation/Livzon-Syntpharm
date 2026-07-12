"""偏差管理 Service"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.deviation_models import (
    CorrectionStatus,
    DeviationStatus,
    InvestigationStatus,
)
from app.modules.quality.qms.deviation_repository import (
    ApprovalRepository,
    ClosingRepository,
    CorrectionRepository,
    DeviationRepository,
    InvestigationRepository,
)
from app.modules.quality.qms.deviation_schemas import (
    ClosingCreate,
    ClosingUpdate,
    CorrectionCreate,
    CorrectionUpdate,
    DeviationCreate,
    DeviationStatistics,
    DeviationUpdate,
    InvestigationCreate,
    InvestigationUpdate,
)


class DeviationService:
    """偏差 Service"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = DeviationRepository(session)
        self.approval_repo = ApprovalRepository(session)

    def _generate_deviation_no(self) -> str:
        """生成偏差编号"""
        now = datetime.now()
        return f"DEV-{now.strftime('%Y%m%d%H%M%S')}"

    async def create_deviation(
        self,
        data: DeviationCreate,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """创建偏差"""
        deviation_data = data.model_dump()

        # 处理偏差描述字段映射
        # 前端可能发送 description 或 abnormal_description，需要统一存储到 abnormal_description
        desc = deviation_data.get("abnormal_description") or deviation_data.get("description")
        deviation_data["abnormal_description"] = desc
        # 清理不需要的字段
        deviation_data.pop("description", None)

        deviation_data["deviation_no"] = self._generate_deviation_no()
        deviation_data["status"] = DeviationStatus.DRAFT

        deviation = await self.repository.create(deviation_data)

        return {
            "deviation": deviation,
            "deviation_no": deviation.deviation_no,
        }

    async def get_deviation(self, deviation_id: UUID) -> dict[str, Any] | None:
        """获取偏差详情"""
        deviation = await self.repository.get_by_id(deviation_id)
        if not deviation:
            return None

        return {
            "deviation": deviation,
            "investigation": deviation.investigation,
            "correction": deviation.correction,
            "closing": deviation.closing,
            "approvals": deviation.approvals,
        }

    async def update_deviation(
        self,
        deviation_id: UUID,
        data: DeviationUpdate,
    ) -> dict[str, Any] | None:
        """更新偏差"""
        try:
            update_data = data.model_dump(exclude_unset=True)

            # 处理偏差描述字段映射
            desc = update_data.get("abnormal_description") or update_data.get("description")
            if desc:
                update_data["abnormal_description"] = desc
            update_data.pop("description", None)

            # 处理调查信息
            investigation_data = update_data.pop("investigation", None)
            if investigation_data:
                # 创建或更新调查记录
                from app.modules.quality.qms.deviation_repository import (
                    InvestigationRepository,
                )

                investigation_repo = InvestigationRepository(self.session)
                existing = await investigation_repo.get_by_deviation_id(deviation_id)
                if existing:
                    # 更新现有调查
                    await investigation_repo.update(deviation_id, investigation_data)
                else:
                    # 创建新调查 - 从数据中移除deviation_id避免重复
                    data_to_create = {k: v for k, v in investigation_data.items() if k != "deviation_id"}
                    data_to_create["status"] = "in_progress"
                    await investigation_repo.create(deviation_id, data_to_create)

            # 处理整改信息
            correction_data = update_data.pop("correction", None)
            if correction_data:
                from app.modules.quality.qms.deviation_repository import (
                    CorrectionRepository,
                )

                correction_repo = CorrectionRepository(self.session)
                existing = await correction_repo.get_by_deviation_id(deviation_id)  # type: ignore[assignment]
                if existing:
                    # 更新现有整改 - 解析日期字段
                    if "plan_completion_date" in correction_data:
                        correction_data["plan_completion_date"] = correction_repo._parse_date(
                            correction_data["plan_completion_date"]
                        )
                    await correction_repo.update(deviation_id, correction_data)
                else:
                    # 创建新整改 - 从数据中移除deviation_id避免重复
                    data_to_create = {k: v for k, v in correction_data.items() if k != "deviation_id"}
                    data_to_create["status"] = "pending"
                    data_to_create["progress"] = 0
                    await correction_repo.create(deviation_id, data_to_create)

                # 更新偏差状态为待整改
                await self.repository.update(deviation_id, {"status": DeviationStatus.CORRECTION_PENDING})

            deviation = await self.repository.update(deviation_id, update_data)
            if not deviation:
                return None
            return deviation  # type: ignore[return-value]
        except Exception:
            import traceback

            traceback.print_exc()
            raise

    async def delete_deviation(self, deviation_id: UUID) -> bool:
        """删除偏差"""
        return await self.repository.delete(deviation_id)

    async def list_deviations(
        self,
        deviation_no: str | None = None,
        deviation_type: str | None = None,
        deviation_level: str | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        product_batch: str | None = None,
        department: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Any], int]:
        """列表查询"""
        return await self.repository.list_with_filter(
            deviation_no=deviation_no,
            deviation_type=deviation_type,
            deviation_level=deviation_level,
            status=status,
            start_date=start_date,
            end_date=end_date,
            product_batch=product_batch,
            department=department,
            page=page,
            page_size=page_size,
        )

    async def submit_deviation(
        self,
        deviation_id: UUID,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """提交偏差"""
        deviation = await self.repository.get_by_id(deviation_id)
        if not deviation:
            raise ValueError("偏差不存在")

        if deviation.status != DeviationStatus.DRAFT:
            raise ValueError("只有草稿状态可以提交")

        # 更新状态
        await self.repository.update(deviation_id, {"status": DeviationStatus.SUBMITTED})

        # 创建提交审批记录
        await self.approval_repo.create(
            {
                "deviation_id": deviation_id,
                "approval_type": "submit",
                "approved": True,
                "approval_comments": "提交偏差",
            }
        )

        return await self.get_deviation(deviation_id)  # type: ignore[return-value]

    async def approve_deviation(
        self,
        deviation_id: UUID,
        approved: bool,
        comments: str | None = None,
        approval_type: str = "admin",
        user_id: str | None = None,
        user_name: str | None = None,
    ) -> dict[str, Any]:
        """审批偏差"""
        deviation = await self.repository.get_by_id(deviation_id)
        if not deviation:
            raise ValueError("偏差不存在")

        # 创建审批记录
        await self.approval_repo.create(
            {
                "deviation_id": deviation_id,
                "approval_type": approval_type,
                "approver_name": user_name,
                "approved": approved,
                "approval_comments": comments,
                "approved_at": datetime.now(),
            }
        )

        if not approved:
            # 驳回
            await self.repository.update(deviation_id, {"status": DeviationStatus.REJECTED})
        else:
            # 根据当前状态更新
            if deviation.status == DeviationStatus.SUBMITTED:
                await self.repository.update(deviation_id, {"status": DeviationStatus.ADMIN_APPROVED})
            elif deviation.status == DeviationStatus.ADMIN_APPROVED:
                await self.repository.update(deviation_id, {"status": DeviationStatus.QA_APPROVED})
            elif deviation.status == DeviationStatus.QA_APPROVED:
                await self.repository.update(deviation_id, {"status": DeviationStatus.ACTIVE})

        return await self.get_deviation(deviation_id)  # type: ignore[return-value]

    async def lock_batch(
        self,
        deviation_id: UUID,
        reason: str,
    ) -> dict[str, Any]:
        """锁定批次"""
        deviation = await self.repository.get_by_id(deviation_id)
        if not deviation:
            raise ValueError("偏差不存在")

        await self.repository.update(
            deviation_id,
            {
                "batch_locked": True,
                "batch_lock_reason": reason,
                "batch_locked_at": datetime.now(),
            },
        )

        return await self.get_deviation(deviation_id)  # type: ignore[return-value]

    async def unlock_batch(self, deviation_id: UUID) -> dict[str, Any]:
        """解锁批次"""
        deviation = await self.repository.get_by_id(deviation_id)
        if not deviation:
            raise ValueError("偏差不存在")

        await self.repository.update(
            deviation_id,
            {
                "batch_locked": False,
            },
        )

        return await self.get_deviation(deviation_id)  # type: ignore[return-value]

    async def get_statistics(self) -> DeviationStatistics:
        """获取统计数据"""
        stats = await self.repository.get_statistics()
        return DeviationStatistics(**stats)


class InvestigationService:
    """偏差调查 Service"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = InvestigationRepository(session)
        self.deviation_repo = DeviationRepository(session)

    async def create_investigation(
        self,
        deviation_id: UUID,
        data: InvestigationCreate,
    ) -> dict[str, Any]:
        """创建调查"""
        # 检查偏差是否存在
        deviation = await self.deviation_repo.get_by_id(deviation_id)
        if not deviation:
            raise ValueError("偏差不存在")

        # 检查是否已有调查
        existing = await self.repository.get_by_deviation_id(deviation_id)
        if existing:
            raise ValueError("该偏差已存在调查记录")

        investigation_data = data.model_dump()
        investigation_data["status"] = InvestigationStatus.PENDING

        investigation = await self.repository.create(deviation_id, investigation_data)

        # 更新偏差状态
        await self.deviation_repo.update(deviation_id, {"status": DeviationStatus.INVESTIGATING})

        return investigation  # type: ignore[return-value]

    async def update_investigation(
        self,
        deviation_id: UUID,
        data: InvestigationUpdate,
    ) -> dict[str, Any] | None:
        """更新调查"""
        update_data = data.model_dump(exclude_unset=True)
        investigation = await self.repository.update(deviation_id, update_data)
        if not investigation:
            return None
        return investigation  # type: ignore[return-value]

    async def complete_investigation(
        self,
        deviation_id: UUID,
    ) -> dict[str, Any]:
        """完成调查"""
        investigation = await self.repository.get_by_deviation_id(deviation_id)
        if not investigation:
            raise ValueError("调查记录不存在")

        await self.repository.update(deviation_id, {"status": InvestigationStatus.COMPLETED})

        # 更新偏差状态
        await self.deviation_repo.update(deviation_id, {"status": DeviationStatus.INVESTIGATION_COMPLETED})

        return investigation  # type: ignore[return-value]

    async def list_pending(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Any], int]:
        """待调查列表"""
        return await self.repository.list_pending(page, page_size)


class CorrectionService:
    """偏差整改 Service"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = CorrectionRepository(session)
        self.deviation_repo = DeviationRepository(session)

    async def create_correction(
        self,
        deviation_id: UUID,
        data: CorrectionCreate,
    ) -> dict[str, Any]:
        """创建整改"""
        # 检查偏差是否存在
        deviation = await self.deviation_repo.get_by_id(deviation_id)
        if not deviation:
            raise ValueError("偏差不存在")

        # 检查是否已有整改
        existing = await self.repository.get_by_deviation_id(deviation_id)
        if existing:
            raise ValueError("该偏差已存在整改记录")

        correction_data = data.model_dump()
        correction_data["status"] = CorrectionStatus.PENDING
        correction_data["progress"] = 0

        correction = await self.repository.create(deviation_id, correction_data)

        # 更新偏差状态
        await self.deviation_repo.update(deviation_id, {"status": DeviationStatus.CORRECTION_PENDING})

        return correction  # type: ignore[return-value]

    async def update_correction(
        self,
        deviation_id: UUID,
        data: CorrectionUpdate,
    ) -> dict[str, Any] | None:
        """更新整改"""
        update_data = data.model_dump(exclude_unset=True)
        correction = await self.repository.update(deviation_id, update_data)
        if not correction:
            return None

        # 更新偏差状态
        if correction.status == CorrectionStatus.IN_PROGRESS:
            await self.deviation_repo.update(deviation_id, {"status": DeviationStatus.CORRECTION_IN_PROGRESS})
        elif correction.status == CorrectionStatus.COMPLETED:
            await self.deviation_repo.update(deviation_id, {"status": DeviationStatus.CORRECTION_COMPLETED})

        return correction  # type: ignore[return-value]

    async def update_progress(
        self,
        deviation_id: UUID,
        progress: int,
    ) -> dict[str, Any]:
        """更新整改进度"""
        correction = await self.repository.get_by_deviation_id(deviation_id)
        if not correction:
            raise ValueError("整改记录不存在")

        update_data = {"progress": progress}
        if progress == 100:
            update_data["status"] = CorrectionStatus.COMPLETED  # type: ignore[assignment]
        elif progress > 0:
            update_data["status"] = CorrectionStatus.IN_PROGRESS  # type: ignore[assignment]

        await self.repository.update(deviation_id, update_data)

        return await self.repository.get_by_deviation_id(deviation_id)  # type: ignore[return-value]

    async def list_pending(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Any], int]:
        """待整改列表"""
        return await self.repository.list_pending(page, page_size)


class ClosingService:
    """偏差关闭 Service"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ClosingRepository(session)
        self.deviation_repo = DeviationRepository(session)

    async def create_closing(
        self,
        deviation_id: UUID,
        data: ClosingCreate,
    ) -> dict[str, Any]:
        """创建关闭申请"""
        # 检查偏差是否存在
        deviation = await self.deviation_repo.get_by_id(deviation_id)
        if not deviation:
            raise ValueError("偏差不存在")

        # 检查是否已有关闭记录
        existing = await self.repository.get_by_deviation_id(deviation_id)
        if existing:
            raise ValueError("该偏差已存在关闭记录")

        closing_data = data.model_dump()

        closing = await self.repository.create(deviation_id, closing_data)

        # 更新偏差状态
        await self.deviation_repo.update(deviation_id, {"status": DeviationStatus.CLOSING_PENDING})

        return closing  # type: ignore[return-value]

    async def update_closing(
        self,
        deviation_id: UUID,
        data: ClosingUpdate,
    ) -> dict[str, Any] | None:
        """更新关闭记录"""
        update_data = data.model_dump(exclude_unset=True)
        closing = await self.repository.update(deviation_id, update_data)
        if not closing:
            return None
        return closing  # type: ignore[return-value]

    async def complete_closing(
        self,
        deviation_id: UUID,
    ) -> dict[str, Any]:
        """完成关闭"""
        closing = await self.repository.get_by_deviation_id(deviation_id)
        if not closing:
            raise ValueError("关闭记录不存在")

        # 解锁批次
        await self.deviation_repo.update(
            deviation_id,
            {
                "batch_locked": False,
            },
        )

        # 归档并关闭
        await self.repository.update(
            deviation_id,
            {
                "batch_unlocked": True,
                "archived": True,
                "archived_at": datetime.now(),
            },
        )

        # 更新偏差状态
        await self.deviation_repo.update(
            deviation_id,
            {
                "status": DeviationStatus.CLOSED,
                "batch_locked": False,
            },
        )

        return closing  # type: ignore[return-value]

    async def list_pending(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Any], int]:
        """待关闭列表"""
        return await self.repository.list_pending(page, page_size)
