"""
智能 Excel 格式转换脚本

功能：
1. 自动识别列名（支持多种别名）
2. 重命列为标准模板格式
3. 删除不需要的列
4. 添加缺失的列
5. 格式化数据（日期、数值等）
6. 映射部门名称

使用方法：
    python scripts/import/convert_excel_to_template.py <输入文件> <输出文件>
"""

import sys
from pathlib import Path
import pandas as pd


# 列名映射（与后端 COLUMN_MAPPING 保持一致）
COLUMN_NAME_MAPPING = {
    # 核心字段
    "资产编号": ["资产编号", "编号", "资产号", "Asset No", "AssetNo", "设备编号"],
    "标签号": ["标签号", "标签", "Label No", "条码号"],
    "资产说明": ["资产说明", "设备名称", "名称", "Name", "设备名"],
    "设备位号": ["设备位号", "位号", "Tag No", "位置号"],
    "设备分类": ["设备分类", "分类", "Class", "ABC分类"],
    "资产类别说明": ["资产类别说明", "类别", "Category", "设备类型"],
    # 技术参数
    "制造商": ["制造商", "厂家", "Manufacturer", "品牌"],
    "型号": ["型号", "规格型号", "Model"],
    "设备规格": ["设备规格", "规格", "Specification", "参数"],
    "供应商": ["供应商", "供货商", "Supplier"],
    # 财务信息
    "当前成本": ["当前成本", "成本", "金额", "价值", "原值", "单价"],
    "账面净值": ["账面净值", "帐面净值", "净值", "Book Value", "残值"],
    # 日期信息
    "出厂日期": ["出厂日期", "生产日期", "制造日期"],
    "启用日期": ["启用日期", "投入使用日期", "启用时间", "投用日期"],
    "报废时间": ["报废时间", "报废日期"],
    # 位置与责任
    "实物所在部门": ["实物所在部门", "部门", "使用部门", "所属部门", "归属部门"],
    "实物所在地点": ["实物所在地点", "地点", "位置", "存放地点"],
    "负责人": ["负责人", "责任人", "保管人"],
    # 状态信息
    "报废状态": ["报废状态", "状态"],
}

# 部门映射
DEPT_MAPPING = {
    "环保中心": "安全环保部",
    "安全中心": "安全环保部",
    "检验室": "质量控制部",
    "质量部": "质量保证部",
    "仪表电工班": "设备工程部",
    "仓库": "仓储部",
    "炊事班": "人事行政部",
    "头孢合成一车间": "201车间",
    "头孢合成二车间": "202车间",
    "头孢精制一车间": "301车间",
    "头孢精制二车间": "302车间",
    "头孢精制三车间": "303车间",
    "非头孢一车间": "101车间",
    "非头孢二车间": "102车间",
    "非头孢三车间": "103车间",
}


def detect_column_mapping(excel_columns: list[str]) -> dict[str, str]:
    """
    自动检测 Excel 列名到标准列名的映射

    Args:
        excel_columns: Excel 文件中的列名列表

    Returns:
        映射字典 {标准列名: Excel列名}
    """
    mapping = {}

    for standard_name, aliases in COLUMN_NAME_MAPPING.items():
        for excel_col in excel_columns:
            if excel_col in aliases:
                mapping[standard_name] = excel_col
                break

    return mapping


def convert_date_format(value) -> str:
    """统一日期格式为 YYYY-MM-DD"""
    if pd.isna(value):
        return ""

    # 如果是 datetime 对象
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")

    # 如果是字符串
    value_str = str(value).strip()
    if not value_str:
        return ""

    # 尝试多种格式
    from datetime import datetime

    for fmt in ["%Y/%m/%d", "%Y-%m-%d", "%Y年%m月%d日", "%m/%d/%Y"]:
        try:
            return datetime.strptime(value_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # 如果是 Excel 日期序列号
    try:
        num = float(value_str)
        from datetime import timedelta

        base_date = pd.Timestamp("1899-12-30")
        return (base_date + timedelta(days=num)).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass

    return value_str


def convert_excel(input_file: str, output_file: str):
    """转换 Excel 文件为标准模板格式"""

    print(f"📖 读取文件: {input_file}")

    # 读取 Excel
    try:
        df = pd.read_excel(input_file, engine="openpyxl")
    except Exception as e:
        print(f"❌ 读取失败: {e}")
        sys.exit(1)

    print(f"✅ 读取成功，共 {len(df)} 行数据")
    print(f"📋 原始列名: {list(df.columns)}")

    # 检测列名映射
    col_mapping = detect_column_mapping(list(df.columns))
    print(f"\n🔍 检测到 {len(col_mapping)} 个匹配列:")
    for standard, original in col_mapping.items():
        print(f"   {original} → {standard}")

    # 重命名列
    df.rename(columns={v: k for k, v in col_mapping.items()}, inplace=True)

    # 删除不需要的列（如"数量"）
    columns_to_drop = [col for col in df.columns if col not in COLUMN_NAME_MAPPING.keys()]
    if columns_to_drop:
        print(f"\n🗑️  删除多余列: {columns_to_drop}")
        df.drop(columns=columns_to_drop, inplace=True)

    # 添加缺失的列
    all_standard_columns = list(COLUMN_NAME_MAPPING.keys())
    missing_columns = [col for col in all_standard_columns if col not in df.columns]
    if missing_columns:
        print(f"\n➕ 添加缺失列: {missing_columns}")
        for col in missing_columns:
            df[col] = ""

    # 调整列顺序（按标准模板顺序）
    column_order = [
        "资产编号",
        "标签号",
        "资产说明",
        "设备位号",
        "设备分类",
        "资产类别说明",
        "制造商",
        "型号",
        "设备规格",
        "供应商",
        "当前成本",
        "账面净值",
        "出厂日期",
        "启用日期",
        "实物所在部门",
        "实物所在地点",
        "负责人",
        "报废状态",
        "报废时间",
    ]

    # 只保留存在的列
    existing_columns = [col for col in column_order if col in df.columns]
    df = df[existing_columns]

    # 格式化日期列
    date_columns = ["出厂日期", "启用日期", "报废时间"]
    for col in date_columns:
        if col in df.columns:
            df[col] = df[col].apply(convert_date_format)

    # 映射部门名称
    if "实物所在部门" in df.columns:
        print("\n🔄 映射部门名称...")
        df["实物所在部门"] = df["实物所在部门"].map(lambda x: DEPT_MAPPING.get(x, x) if pd.notna(x) else x)

    # 保存文件
    print(f"\n💾 保存文件: {output_file}")
    df.to_excel(output_file, index=False, engine="openpyxl")

    print("\n✅ 转换完成！")
    print(f"   - 原始行数: {len(df)}")
    print(f"   - 最终列数: {len(df.columns)}")
    print(f"   - 输出文件: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python convert_excel_to_template.py <输入文件> <输出文件>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not Path(input_file).exists():
        print(f"❌ 文件不存在: {input_file}")
        sys.exit(1)

    convert_excel(input_file, output_file)
