from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.identity.models import Department, User


class UserRepository:
    async def get_by_id(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> User | None:
        result = await session.execute(
            select(User).where(
                User.id == user_id,
                User.is_deleted == False,  # noqa: E712
            ),
        )
        return result.scalar_one_or_none()

    async def get_by_feishu_open_id(
        self,
        session: AsyncSession,
        open_id: str,
    ) -> User | None:
        result = await session.execute(
            select(User).where(
                User.feishu_open_id == open_id,
                User.is_deleted == False,  # noqa: E712
            ),
        )
        return result.scalar_one_or_none()

    async def get_by_feishu_user_id(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> User | None:
        result = await session.execute(
            select(User).where(
                User.feishu_user_id == user_id,
                User.is_deleted == False,  # noqa: E712
            ),
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        *,
        name: str,
        feishu_user_id: str | None,
        feishu_open_id: str,
        feishu_union_id: str | None = None,
        en_name: str | None = None,
        employee_no: str | None = None,
        email: str | None = None,
        enterprise_email: str | None = None,
        mobile: str | None = None,
        avatar_url: str | None = None,
        avatar_thumb: str | None = None,
        avatar_middle: str | None = None,
        avatar_big: str | None = None,
        tenant_key: str | None = None,
        department: str | None = None,
        position: str | None = None,
        feishu_department_ids: str | None = None,
    ) -> User:
        user = User(
            name=name,
            feishu_user_id=feishu_user_id,
            feishu_open_id=feishu_open_id,
            feishu_union_id=feishu_union_id,
            en_name=en_name,
            employee_no=employee_no,
            email=email,
            enterprise_email=enterprise_email,
            mobile=mobile,
            avatar_url=avatar_url,
            avatar_thumb=avatar_thumb,
            avatar_middle=avatar_middle,
            avatar_big=avatar_big,
            tenant_key=tenant_key,
            department=department,
            position=position,
            feishu_department_ids=feishu_department_ids,
        )
        session.add(user)
        await session.flush()
        return user

    async def list_all(
        self,
        session: AsyncSession,
        *,
        department_id: str | None = None,
        keyword: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[User], int]:
        """分页查询所有用户，支持按部门/关键词筛选。"""
        base = select(User).where(User.is_deleted == False)  # noqa: E712

        if department_id:
            base = base.where(
                User.feishu_department_ids.contains(department_id),
            )
        if keyword:
            base = base.where(
                User.name.ilike(f"%{keyword}%"),
            )

        count_stmt = select(User.id).where(User.is_deleted == False)  # noqa: E712
        if department_id:
            count_stmt = count_stmt.where(
                User.feishu_department_ids.contains(department_id),
            )
        if keyword:
            count_stmt = count_stmt.where(
                User.name.ilike(f"%{keyword}%"),
            )
        total_result = await session.execute(count_stmt)
        total = len(total_result.scalars().all())

        stmt = base.order_by(User.name).offset(offset).limit(limit)
        result = await session.execute(stmt)
        users = list(result.scalars().all())
        return users, total


class DepartmentRepository:
    async def get_by_feishu_id(
        self,
        session: AsyncSession,
        feishu_dept_id: str,
    ) -> Department | None:
        result = await session.execute(
            select(Department).where(
                Department.feishu_department_id == feishu_dept_id,
            ),
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        session: AsyncSession,
        *,
        include_deleted: bool = False,
    ) -> list[Department]:
        stmt = select(Department).where(
            Department.is_deleted == False,  # noqa: E712
        )
        if not include_deleted:
            stmt = stmt.where(Department.status_is_deleted == False)  # noqa: E712
        stmt = stmt.order_by(Department.order, Department.name)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_children(
        self,
        session: AsyncSession,
        parent_id: str,
    ) -> list[Department]:
        stmt = (
            select(Department)
            .where(
                Department.parent_feishu_department_id == parent_id,
                Department.is_deleted == False,  # noqa: E712
                Department.status_is_deleted == False,  # noqa: E712
            )
            .order_by(Department.order, Department.name)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


class LoginLogRepository:
    async def create(
        self,
        session: AsyncSession,
        *,
        user_id=None,
        user_name: str | None = None,
        login_type: str = "feishu_sso",
        status: str = "success",
        ip_address: str | None = None,
        user_agent: str | None = None,
        error_message: str | None = None,
        extra: dict | None = None,
    ):
        from app.platform.identity.models import LoginLog

        log = LoginLog(
            user_id=user_id,
            user_name=user_name,
            login_type=login_type,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=error_message,
            extra=extra,
        )
        session.add(log)
        await session.flush()
        return log

    async def list_logs(
        self,
        session: AsyncSession,
        *,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list, int]:
        from app.platform.identity.models import LoginLog

        base = select(LoginLog).where(LoginLog.is_deleted == False)  # noqa: E712
        count_base = select(LoginLog.id).where(LoginLog.is_deleted == False)  # noqa: E712

        if status:
            base = base.where(LoginLog.status == status)
            count_base = count_base.where(LoginLog.status == status)
        if keyword:
            base = base.where(LoginLog.user_name.ilike(f"%{keyword}%"))
            count_base = count_base.where(LoginLog.user_name.ilike(f"%{keyword}%"))

        total_result = await session.execute(count_base)
        total = len(total_result.scalars().all())

        stmt = (
            base.order_by(LoginLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await session.execute(stmt)
        logs = list(result.scalars().all())
        return logs, total
