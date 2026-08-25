"""Tests for department mapping logic in equipment import."""

from unittest.mock import AsyncMock, MagicMock, patch

from tests.modules.equipment.conftest import MockDB, create_mock_department


async def test_exact_match_in_mapping() -> None:
    from app.modules.equipment.api.batch_import import map_department_name_v3

    db = MockDB()
    mock_dept = create_mock_department("uuid-quality-control", "质量控制部")

    with patch("app.modules.hr.repository.DepartmentRepository") as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo.get_by_name = AsyncMock(return_value=mock_dept)
        mock_repo_class.return_value = mock_repo

        name, id_val = await map_department_name_v3("检验室", db)  # type: ignore[arg-type]
        assert name == "质量控制部"
        assert id_val == "uuid-quality-control"


async def test_solvent_workshop_mapping() -> None:
    from app.modules.equipment.api.batch_import import map_department_name_v3

    db = MockDB()
    mock_dept = create_mock_department("uuid-solvent-recovery", "溶剂回收车间")

    with patch("app.modules.hr.repository.DepartmentRepository") as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo.get_by_name = AsyncMock(return_value=mock_dept)
        mock_repo_class.return_value = mock_repo

        name, id_val = await map_department_name_v3("溶剂回收车间-401岗", db)  # type: ignore[arg-type]
        assert name == "溶剂回收车间"
        assert id_val == "uuid-solvent-recovery"


async def test_unknown_department_returns_none() -> None:
    from app.modules.equipment.api.batch_import import map_department_name_v3

    db = MockDB()

    with patch("app.modules.hr.repository.DepartmentRepository") as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo.get_by_name = AsyncMock(return_value=None)
        mock_repo_class.return_value = mock_repo

        name, id_val = await map_department_name_v3("不存在的火星部门", db)  # type: ignore[arg-type]
        assert name is None
        assert id_val is None
