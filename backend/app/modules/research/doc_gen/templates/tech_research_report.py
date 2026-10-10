"""技术调研报告模板槽位定义。

锚点全部基于母本实际结构（表头文本 / 标签段落 / 坐标 + guard 校验），
不依赖段落序号，因此母本小改（增删空行、调整段落顺序）不会导致填错位置。
"""

from __future__ import annotations

from typing import Literal

from app.modules.research.doc_gen.template_spec import Anchor, ColumnSpec, Slot, TableSpec, TemplateSpec

_BASIC = ["基本信息", "药品名称"]  # 第 1 章基本信息表（合并单元格网格）
_SIGN = ["起草人"]
_CHANGELOG = ["版本", "变更描述"]
_FILING = ["登记号", "企业名称", "产品来源", "审批结果"]
_SUPPLIER = ["方案", "物料名称", "CAS号", "参考供应商"]
_MATERIAL_COST = ["物料名称", "用量", "单价", "费用占比"]
_IMPURITY = ["序号", "结构", "来源", "杂质类型", "备注"]

PENDING = "[待补充：需人工填写]"


def _cell(label: str, header: list[str], guard: str | None = None) -> Anchor:
    """表格中「行标签右侧单元格」锚点。"""
    return Anchor(type="table_cell", table_header=header, row_label=label, guard=guard)


def _coord(row: int, col: int, header: list[str], guard: str) -> Anchor:
    """坐标锚点（必须带 guard，防模板变更后填错格子）。"""
    return Anchor(type="table_cell", table_header=header, row_index=row, col_index=col, guard=guard)


def _label(text: str, mode: Literal["exact", "prefix", "contains"] = "exact") -> Anchor:
    """正文「标签：」段落锚点。"""
    return Anchor(type="paragraph_after_label", paragraph_label=text, paragraph_match=mode)


def _replace(label_text: str) -> Anchor:
    """整段替换锚点（母本中给人看的提示语段落）。"""
    return Anchor(type="replace_paragraph", paragraph_label=label_text, paragraph_match="contains")


def _section(heading: str, after: int = 0) -> Anchor:
    """章节标题下正文锚点。"""
    return Anchor(type="section_body", heading=heading, after_heading=after)


SLOTS = [
    Slot(
        key="drug_name",
        label="药品名称（原料药）",
        required=True,
        max_chars=80,
        from_meta=True,
        query_hint="母本中以 XXXX/XXX 占位的品种名",
        anchors=[
            Anchor(type="global_variable", keyword="XXXX"),
            Anchor(type="global_variable", keyword="XXX"),
        ],
    ),
    Slot(
        key="doc_code",
        label="受控编码",
        from_meta=True,
        max_chars=40,
        anchors=[Anchor(type="header_field", header_contains="编码")],
    ),
    Slot(
        key="doc_version",
        label="版本号",
        from_meta=True,
        overwrite_cell=True,
        max_chars=10,
        anchors=[
            Anchor(type="header_field", header_contains="版本号"),
            _coord(1, 0, _CHANGELOG, guard="新制定"),
        ],
    ),
    Slot(
        key="changelog_editor",
        label="变更历史起草/修订人",
        manual_only=True,
        anchors=[_coord(1, 2, _CHANGELOG, guard="新制定")],
    ),
    Slot(key="drafter", label="起草人", manual_only=True, anchors=[_coord(0, 1, _SIGN, guard="起草人")]),
    Slot(key="reviewer", label="审核人", manual_only=True, anchors=[_coord(3, 1, _SIGN, guard="审核人")]),
    Slot(key="approver", label="批准人", manual_only=True, anchors=[_coord(9, 1, _SIGN, guard="批准人")]),
    Slot(
        key="product_spec",
        label="商品名及规格",
        search_terms=["商品名", "规格", "商品规格"],
        anchors=[_cell("商品名及规格", _BASIC)],
    ),
    Slot(
        key="originator",
        label="原研企业",
        required=True,
        search_terms=["原研厂家", "原研公司", "原研药厂", "原创企业", "原研"],
        anchors=[_cell("原研企业", _BASIC)],
    ),
    Slot(
        key="domestic_market",
        label="国内上市情况",
        search_terms=["上市", "上市情况", "获批", "国内上市"],
        anchors=[_cell("国内上市情况", _BASIC)],
    ),
    Slot(key="tech_opinion", label="技术部意见", manual_only=True, anchors=[_cell("技术部意见", _BASIC)]),
    Slot(key="quality_opinion", label="质量部意见", manual_only=True, anchors=[_cell("质量部意见", _BASIC)]),
    Slot(key="production_opinion", label="生产部意见", manual_only=True, anchors=[_cell("生产部", _BASIC)]),
    Slot(key="overall_opinion", label="综合意见", manual_only=True, anchors=[_cell("综合意见", _BASIC)]),
    Slot(
        key="variety_intro",
        label="品种简介正文",
        kind="paragraph",
        max_chars=1200,
        search_terms=["品种简介", "适应症", "药理", "品种概况", "产品简介"],
        anchors=[_replace("适应症、用法用量、原研厂家进行介绍")],
    ),
    Slot(
        key="preparation_spec",
        label="制剂/规格",
        max_chars=200,
        search_terms=["剂型", "制剂规格", "规格"],
        anchors=[_label("制剂/规格：")],
    ),
    Slot(
        key="dosage_admin",
        label="用法用量",
        max_chars=300,
        search_terms=["用法", "用量", "给药途径", "服用方法"],
        anchors=[_label("用法用量：")],
    ),
    Slot(
        key="domestic_manufacturers",
        label="国内生产厂家",
        max_chars=400,
        search_terms=["国内厂家", "生产厂家", "生产企业", "国产厂家", "manufacturer"],
        anchors=[_label("国内生产厂家：")],
    ),
    Slot(
        key="name_cn",
        label="名称",
        max_chars=100,
        search_terms=["中文名称", "通用名", "药品名称", "品名"],
        anchors=[_label("名称：")],
    ),
    Slot(
        key="name_other",
        label="其他名称",
        max_chars=200,
        search_terms=["别名", "商品名", "其他名称"],
        anchors=[_label("其他名称：")],
    ),
    Slot(
        key="name_en",
        label="英文名",
        max_chars=200,
        search_terms=["英文名称", "English Name", "英文通用名", "INN", "generic name", "English name"],
        anchors=[_label("英文名：")],
    ),
    Slot(
        key="name_chemical",
        label="化学名称",
        max_chars=300,
        search_terms=["化学名", "CAS 名称", "化学结构名称", "IUPAC", "chemical name", "IUPAC name"],
        anchors=[_label("化学名称：")],
    ),
    Slot(
        key="structure_image",
        label="结构式",
        kind="image",
        manual_only=True,
        anchors=[Anchor(type="image_placeholder", paragraph_label="结构式：")],
    ),
    Slot(
        key="filing_rows",
        label="国内原料药申报情况",
        kind="table",
        required=True,
        search_terms=["申报", "登记", "受理", "注册", "登记号", "受理号", "注册申报", "原料药登记"],
        table=TableSpec(header_rows=1, row_limit=80),
        columns=[
            ColumnSpec(key="reg_no", label="登记号", max_chars=40),
            ColumnSpec(key="company", label="企业名称", max_chars=120),
            ColumnSpec(key="source", label="产品来源", max_chars=60),
            ColumnSpec(key="approval", label="审批结果", max_chars=60),
            ColumnSpec(key="update_date", label="更新日期", max_chars=20, expects="date"),
            ColumnSpec(key="on_sale", label="是否销售", max_chars=20),
        ],
        anchors=[Anchor(type="table_rows", table_header=_FILING)],
    ),
    Slot(
        key="route_design",
        label="结构分块和路线设计思路",
        kind="paragraph",
        max_chars=1500,
        draft_allowed=True,
        search_terms=["路线设计", "合成路线", "工艺路线", "逆合成", "路线思路"],
        anchors=[_replace("结构分块和路线设计思路")],
    ),
    *[
        Slot(
            key=f"route_{idx}",
            label=f"工艺路线 {idx}",
            kind="paragraph",
            max_chars=2000,
            draft_allowed=True,
            search_terms=["路线", "合成路线", "反应路线", "制备方法"],
            anchors=[_section(f"路线{idx}")],
        )
        for idx in (1, 2, 3, 4)
    ],
    Slot(
        key="route_choice",
        label="综合选择和说明",
        kind="paragraph",
        max_chars=2000,
        draft_allowed=True,
        search_terms=["路线选择", "路线比较", "综合评价", "路线优劣势"],
        anchors=[_section("综合选择和说明")],
    ),
    Slot(
        key="supplier_rows",
        label="主要物料国内供应商信息",
        kind="table",
        search_terms=["供应商", "供应", "采购", "物料供应", "厂家"],
        table=TableSpec(header_rows=1, row_limit=60),
        columns=[
            ColumnSpec(key="plan", label="方案", max_chars=40),
            ColumnSpec(key="material", label="物料名称", max_chars=100),
            ColumnSpec(key="cas", label="CAS号", max_chars=40),
            ColumnSpec(key="supplier", label="参考供应商", max_chars=200),
        ],
        anchors=[Anchor(type="table_rows", table_header=_SUPPLIER)],
    ),
    Slot(key="supplier_note", label="供应信息备注", max_chars=400, anchors=[_label("备注：", mode="contains")]),
    Slot(
        key="material_cost_rows",
        label="1kg 物料消耗表",
        kind="table",
        required=True,
        search_terms=["物料", "成本", "价格", "单价", "消耗", "原料成本", "物料清单"],
        table=TableSpec(header_rows=1, row_limit=80, total_row_label="1kg总价"),
        columns=[
            ColumnSpec(key="material", label="物料名称", max_chars=100),
            ColumnSpec(key="usage", label="用量", max_chars=30, expects="number"),
            ColumnSpec(key="price", label="单价", max_chars=30, expects="number"),
            ColumnSpec(
                key="cost", label="费用", max_chars=30, expects="number", compute="product", operands=["usage", "price"]
            ),
            ColumnSpec(
                key="ratio", label="费用占比", max_chars=20, expects="percent", compute="ratio", operands=["cost"]
            ),
        ],
        anchors=[Anchor(type="table_rows", table_header=_MATERIAL_COST)],
    ),
    Slot(
        key="quality_standard_info",
        label="质量标准信息",
        kind="paragraph",
        max_chars=2000,
        source_roles=["material", "literature"],
        search_terms=["质量标准", "质量研究", "药典", "标准", "检验", "ChP", "USP", "EP"],
        anchors=[_section("质量标准信息")],
    ),
    Slot(
        key="impurity_rows",
        label="杂质谱",
        kind="table",
        search_terms=["杂质", "有关物质", "降解产物", "工艺杂质", "杂质分析"],
        table=TableSpec(header_rows=1, row_limit=80, sequence_column="seq"),
        columns=[
            ColumnSpec(key="seq", label="序号", max_chars=6),
            ColumnSpec(key="structure", label="结构", max_chars=60),
            ColumnSpec(key="origin", label="来源", max_chars=120),
            ColumnSpec(key="impurity_type", label="杂质类型", max_chars=80),
            ColumnSpec(key="note", label="备注", max_chars=200),
        ],
        anchors=[Anchor(type="table_rows", table_header=_IMPURITY)],
    ),
    Slot(
        key="crystal_overview",
        label="晶型方面概述",
        kind="paragraph",
        max_chars=1500,
        draft_allowed=True,
        search_terms=["晶型", "多晶型", "结晶", "晶癖", "XRPD", "X射线粉末衍射"],
        anchors=[_replace("晶型方面的概述")],
    ),
    Slot(
        key="process_evaluation",
        label="工艺评价和可能存在的问题",
        kind="paragraph",
        max_chars=2500,
        draft_allowed=True,
        search_terms=["工艺评价", "工艺问题", "放大", "工艺风险", "工艺优化"],
        anchors=[_replace("结合实际进行讨论")],
    ),
]

SPEC = TemplateSpec(
    code="tech_research_report",
    name="技术调研报告",
    version="01",
    stage="initiation",
    master_asset="tech_research_report.dotx",
    description="原料药项目立项/技术调研阶段用受控报告",
    unfilled_notes=[
        "第 1 章「可行性评估」网格（市场价格/自研成本/批量选择/知识产权/设备设施/人力/场地）需人工填写",
        "第 8 章产能预期表的年度列随年份漂移，本版不自动填充",
        "表5 项目工作计划、表6 项目预算表为固定行结构，本版不自动填充",
        "表7 附件清单（附件编码来自其他受控文件）本版不自动填充",
        "所有图示（结构式、反应路线图、杂质结构图）仅留文字占位，需人工贴图",
    ],
    slots=SLOTS,
)
