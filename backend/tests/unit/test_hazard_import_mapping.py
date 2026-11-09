"""危险源辨识台账 CSV 导入的行映射测试（GB18030 清单 → hazard_identifications 行）。

测试对象是导入脚本暴露的纯函数 map_row，断言值来自原始 CSV 的表头与样例行，
不复制实现里的常量，避免同义反复。
"""

from typing import Any

from app.modules.safety.service.hazard_ledger_import import map_row

# 与 危险源辨识_去重_12683.csv 表头一致（32 列）
HEADER: list[str] = [
    "表内序号",
    "检查表编号",
    "风险点编号",
    "风险点类型",
    "风险点名称",
    "作业活动名称",
    "岗位",
    "作业单元/区域",
    "设备设施名称",
    "位号/部位",
    "作业步骤/检查项目",
    "检查标准",
    "危险源/潜在事件",
    "可能事故后果",
    "风险评价方法",
    "可能性L",
    "频次E",
    "后果C",
    "严重性S",
    "风险值D",
    "风险等级_四级",
    "现有风险等级_四级",
    "管控层级",
    "管控单位",
    "工程技术措施",
    "管理措施",
    "培训教育措施",
    "个体防护措施",
    "应急处置措施",
    "责任部门",
    "责任人",
    "备注",
]


def _row(**overrides: str) -> dict[str, str]:
    row: dict[str, str] = dict.fromkeys(HEADER, "")
    row.update(overrides)
    return row


def _lec_row() -> dict[str, str]:
    """CSV 第 2 行（表内序号 12，101车间，LEC 法，风险等级=较大）。"""
    return _row(
        表内序号="12",
        风险点编号="FXD-002、\nFXD-007",
        风险点类型="常规作业",
        风险点名称="一楼备料区危废暂存区、三楼备料区",
        作业活动名称="物料、危废转运",
        **{"作业步骤/检查项目": "物料转运"},
        **{"危险源/潜在事件": "人员未正确佩戴劳保防护用品"},
        可能事故后果="搬运过程中误接触或吸入导致化学性烧伤与中毒窒息",
        可能性L="3",
        频次E="6",
        后果C="7",
        风险值D="126",
        风险等级_四级="较大",
        现有风险等级_四级="低",
        管控层级="部门(车间)级",
        管控单位="非头孢制造部",
        工程技术措施="/",
        管理措施="1.严格执行EHS-03-16804《101车间劳保防护用品操作规程》；",
        培训教育措施="1.按照EHS-02-005《EHS培训管理程序》组织培训；",
        个体防护措施="/",
        应急处置措施="1.严格执行EHS-03-90701《101车间安全生产事故应急预案》；",
        责任部门="101车间",
        责任人="刘小军",
    )


def _ls_row() -> dict[str, str]:
    """LS 法行：有严重性 S、无后果 C。"""
    return _row(
        作业活动名称="离心机操作",
        风险评价方法="LS",
        可能性L="3",
        严重性S="15",
        风险值D="45",
        风险等级_四级="一般",
        管控层级="公司(厂)级",
        责任部门="201车间",
    )


def test_map_row_copies_all_columns_into_fields() -> None:
    mapped = map_row(_lec_row(), seq=42)

    assert mapped["hazard_id_no"] == "HZ-00042"
    assert mapped["checklist_no"] is None
    assert mapped["risk_point_no"] == "FXD-002、 FXD-007"
    assert mapped["risk_point_type"] == "常规作业"
    assert mapped["risk_point_name"] == "一楼备料区危废暂存区、三楼备料区"
    assert mapped["specific_activity"] == "物料、危废转运"
    assert mapped["work_step"] == "物料转运"
    assert mapped["check_standard"] is None
    assert mapped["unsafe_behavior"] == "人员未正确佩戴劳保防护用品"
    assert mapped["possible_accident"] == "搬运过程中误接触或吸入导致化学性烧伤与中毒窒息"
    assert mapped["control_unit"] == "非头孢制造部"
    assert mapped["department"] == "101车间"
    assert mapped["responsible_person"] == "刘小军"
    assert mapped["training_measures"] == "1.按照EHS-02-005《EHS培训管理程序》组织培训；"


def test_map_row_cleans_placeholder_and_newline() -> None:
    mapped = map_row(_lec_row(), seq=1)

    # "/" 视为空
    assert mapped["existing_engineering_controls"] is None
    assert mapped["existing_ppe"] is None
    # 非空措施原样保留
    assert mapped["existing_management_controls"].startswith("1.严格执行EHS-03-16804")
    # 单元格内换行归一为单个空格
    assert "\n" not in mapped["risk_point_no"]


def test_map_row_maps_risk_levels() -> None:
    mapped = map_row(_lec_row(), seq=1)

    assert mapped["inherent_risk_level"] == "level_2"
    assert mapped["inherent_risk_label"] == "二级/较大风险"
    assert mapped["residual_risk_level"] == "level_4"
    assert mapped["residual_risk_label"] == "四级/低风险"
    # 残余 LEC 与措施后风险不写
    assert mapped["l_residual"] is None
    assert mapped["d_residual"] is None
    assert mapped["post_risk_level"] is None
    assert mapped["l_post"] is None


def test_map_row_normalizes_control_level() -> None:
    assert map_row(_lec_row(), seq=1)["control_level"] == "部门级"
    assert map_row(_ls_row(), seq=2)["control_level"] == "公司级"


def test_map_row_handles_ls_method_without_c() -> None:
    mapped = map_row(_ls_row(), seq=7)

    assert mapped["risk_method"] == "LS"
    assert mapped["severity_s"] == 15.0
    assert mapped["l_inherent"] == 3.0
    assert mapped["c_inherent"] is None
    assert mapped["d_inherent"] == 45.0


def test_map_row_handles_lec_method_without_s() -> None:
    mapped = map_row(_lec_row(), seq=7)

    assert mapped["risk_method"] == "LEC"
    assert mapped["severity_s"] is None
    assert mapped["c_inherent"] == 7.0


def test_map_row_keeps_blank_text_fields_blank() -> None:
    """用户已确认：空值不做继承，必须原样留空。"""
    mapped = map_row(_row(责任部门="101车间"), seq=3)

    assert mapped["position"] == ""
    assert mapped["production_step"] == ""
    assert mapped["risk_point_no"] is None
    assert mapped["work_unit"] is None
    assert mapped["notes"] is None


def test_map_row_marks_record_completed() -> None:
    mapped = map_row(_lec_row(), seq=1)

    assert mapped["overall_status"] == "completed"
    assert mapped["ai_node_progress"] == "completed"
    for script_no in range(1, 8):
        assert mapped[f"script{script_no}_review_status"] == "approved"


def test_map_row_unknown_risk_level_becomes_null() -> None:
    mapped = map_row(_row(责任部门="101车间", 风险等级_四级="未知等级"), seq=1)

    assert mapped["inherent_risk_level"] is None
    assert mapped["inherent_risk_label"] is None


def test_map_row_only_writes_known_fields() -> None:
    """所有键必须是 HazardIdentification 的真实列，防止拼错字段名。"""
    from app.modules.safety.models import HazardIdentification

    mapped: dict[str, Any] = map_row(_lec_row(), seq=1)
    columns = {column.name for column in HazardIdentification.__table__.columns}

    assert set(mapped) <= columns
