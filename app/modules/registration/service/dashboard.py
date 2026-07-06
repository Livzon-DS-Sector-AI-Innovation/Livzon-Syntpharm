"""Registration dashboard service."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.registration.models.certificate import RegistrationCertificate
from app.modules.registration.models.project import RegistrationProject
from app.modules.registration.schemas.dashboard import (
    DashboardCertificateItem,
    DashboardProjectItem,
    DashboardSummaryResponse,
)

SUBMITTED_STATUSES = ("submitted", "accepted", "under_review")
TERMINAL_STATUSES = ("approved", "withdrawn", "terminated")


async def get_dashboard_summary(db: AsyncSession) -> DashboardSummaryResponse:
    # 已获批品种数
    stmt_approved = (
        select(func.count())
        .select_from(RegistrationProject)
        .where(
            not RegistrationProject.is_deleted,
            RegistrationProject.status == "approved",
        )
    )
    approved_count = (await db.execute(stmt_approved)).scalar() or 0

    # 海外市场获批数量
    stmt_overseas = (
        select(func.count())
        .select_from(RegistrationCertificate)
        .where(
            not RegistrationCertificate.is_deleted,
            RegistrationCertificate.status.in_(("valid", "expiring")),
        )
    )
    overseas_count = (await db.execute(stmt_overseas)).scalar() or 0

    # 已申报受理品种数
    stmt_submitted = (
        select(func.count())
        .select_from(RegistrationProject)
        .where(
            not RegistrationProject.is_deleted,
            RegistrationProject.status.in_(SUBMITTED_STATUSES),
        )
    )
    submitted_count = (await db.execute(stmt_submitted)).scalar() or 0

    # 进行中项目数
    stmt_active = (
        select(func.count())
        .select_from(RegistrationProject)
        .where(
            not RegistrationProject.is_deleted,
            RegistrationProject.status.notin_(TERMINAL_STATUSES),
        )
    )
    active_count = (await db.execute(stmt_active)).scalar() or 0

    # 最近项目（10条）
    stmt_recent = (
        select(RegistrationProject)
        .where(~RegistrationProject.is_deleted)
        .order_by(RegistrationProject.updated_at.desc())
        .limit(10)
    )
    recent_result = await db.execute(stmt_recent)
    recent_projects = [
        DashboardProjectItem.model_validate(p) for p in recent_result.scalars().all()
    ]

    # 海外获批记录（10条）
    stmt_certs = (
        select(RegistrationCertificate)
        .where(~RegistrationCertificate.is_deleted)
        .order_by(RegistrationCertificate.approved_at.desc().nullslast())
        .limit(10)
    )
    cert_result = await db.execute(stmt_certs)
    overseas_approvals = [
        DashboardCertificateItem(
            id=c.id,
            product_name=c.product_name,
            market=c.market,
            certificate_no=c.certificate_no,
            approved_at=c.approved_at,
            valid_until=c.valid_until,
            certificate_status=c.status,
            file_path=c.file_path,
        )
        for c in cert_result.scalars().all()
    ]

    return DashboardSummaryResponse(
        approved_product_count=approved_count,
        overseas_approval_count=overseas_count,
        submitted_project_count=submitted_count,
        active_project_count=active_count,
        recent_projects=recent_projects,
        overseas_approvals=overseas_approvals,
    )
