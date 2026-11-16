"""Regression tests for ticket #196: remove unused HR 班组 and production settings.

The org pages are being rebuilt on the Feishu mirror, so 班组 must not exist as a
table/model/schema/permission/route, and departments must not carry production
shift settings. These assertions are cheap guards against dead concepts creeping
back into the rebuild.
"""

from app.modules.hr import models, schemas
from app.modules.hr.api import router as hr_router
from app.platform.permission.registry import ALL_PERMISSIONS, API_BINDINGS, RESOURCE_LABELS
from app.shared.base_model import Base

_PRODUCTION_FIELDS = {"is_production", "production_start_time", "production_end_time"}


def test_team_model_and_table_are_removed() -> None:
    assert not hasattr(models, "Team")
    assert "hr.teams" not in Base.metadata.tables
    assert "teams" not in models.HrDepartment.__mapper__.relationships


def test_department_model_has_no_production_columns() -> None:
    assert _PRODUCTION_FIELDS.isdisjoint(models.HrDepartment.__table__.columns.keys())


def test_team_schemas_are_removed() -> None:
    for name in ("TeamBase", "TeamCreate", "TeamUpdate", "TeamResponse"):
        assert not hasattr(schemas, name)


def test_department_schemas_have_no_production_fields() -> None:
    for model in (
        schemas.DepartmentBase,
        schemas.DepartmentCreate,
        schemas.DepartmentUpdate,
        schemas.DepartmentResponse,
    ):
        assert _PRODUCTION_FIELDS.isdisjoint(model.model_fields)


def test_team_and_production_routes_are_removed() -> None:
    paths = {getattr(route, "path", "") for route in hr_router.routes}
    assert not any(path.startswith("/teams") for path in paths)
    assert not any("production-settings" in path for path in paths)


def test_team_permissions_and_bindings_are_removed() -> None:
    assert all(not definition.code.startswith("hr:teams:") for definition in ALL_PERMISSIONS)
    assert "hr:teams" not in RESOURCE_LABELS
    assert not any(
        binding.route_template.startswith("/api/v1/hr/teams") or binding.route_template.endswith("/production-settings")
        for binding in API_BINDINGS
    )
