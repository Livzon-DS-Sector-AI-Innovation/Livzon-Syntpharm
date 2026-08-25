"""设备导入 v2 功能测试 (TDD)."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.equipment.api.batch_import import DEPT_MAPPING_V3, map_department_name_v3
from tests.modules.equipment.conftest import MockDB, create_mock_department


def test_dept_mapping_v2_coverage() -> None:
    """测试映射表是否包含关键别名"""
    assert "检验室" in DEPT_MAPPING_V3
    assert DEPT_MAPPING_V3["检验室"] == "质量控制部"
    assert "头孢合成一车间" in DEPT_MAPPING_V3
    assert DEPT_MAPPING_V3["头孢合成一车间"] == "201车间"


async def test_map_department_strict_alias() -> None:
    """测试别名映射逻辑"""
    db = MockDB()
    mock_dept = create_mock_department("uuid-quality-control", "质量控制部")

    with patch("app.modules.hr.repository.DepartmentRepository") as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo.get_by_name = AsyncMock(return_value=mock_dept)
        mock_repo_class.return_value = mock_repo

        name, dept_id = await map_department_name_v3("检验室", db)  # type: ignore[arg-type]
        assert name == "质量控制部"
        assert dept_id is not None


async def test_map_department_strict_workshop() -> None:
    """测试车间编号映射"""
    db = MockDB()
    mock_dept = create_mock_department("uuid-201-workshop", "201车间")

    with patch("app.modules.hr.repository.DepartmentRepository") as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo.get_by_name = AsyncMock(return_value=mock_dept)
        mock_repo_class.return_value = mock_repo

        name, dept_id = await map_department_name_v3("头孢合成一车间", db)  # type: ignore[arg-type]
        assert name == "201车间"
        assert dept_id is not None


async def test_map_department_strict_special_format() -> None:
    """测试溶剂回收车间特殊格式归口"""
    db = MockDB()
    mock_dept = create_mock_department("uuid-solvent", "溶剂回收车间")

    with patch("app.modules.hr.repository.DepartmentRepository") as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo.get_by_name = AsyncMock(return_value=mock_dept)
        mock_repo_class.return_value = mock_repo

        name, dept_id = await map_department_name_v3("溶剂回收车间-404岗", db)  # type: ignore[arg-type]
        assert name == "溶剂回收车间"
        assert dept_id is not None


async def test_map_department_strict_nonexistent() -> None:
    """测试不存在的部门返回 None"""
    db = MockDB()

    with patch("app.modules.hr.repository.DepartmentRepository") as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo.get_by_name = AsyncMock(return_value=None)
        mock_repo_class.return_value = mock_repo

        name, dept_id = await map_department_name_v3("银河系漫游指南部", db)  # type: ignore[arg-type]
        assert dept_id is None
