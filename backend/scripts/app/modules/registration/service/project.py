"""Registration project service."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.registration.models.project import RegistrationProject
from app.modules.registration.schemas.project import ProjectCreate, ProjectUpdate


async def get_projects(db: AsyncSession) -> list[RegistrationProject]:
    stmt = (
        select(RegistrationProject)
        .where(~RegistrationProject.is_deleted)
        .order_by(RegistrationProject.updated_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> RegistrationProject:
    stmt = select(RegistrationProject).where(
        RegistrationProject.id == project_id,
        ~RegistrationProject.is_deleted,
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError("项目不存在")
    return project


async def create_project(db: AsyncSession, data: ProjectCreate) -> RegistrationProject:
    project = RegistrationProject(**data.model_dump(exclude_unset=True))
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def update_project(db: AsyncSession, project_id: uuid.UUID, data: ProjectUpdate) -> RegistrationProject:
    project = await get_project(db, project_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project_id: uuid.UUID) -> None:
    project = await get_project(db, project_id)
    project.is_deleted = True
    await db.commit()
