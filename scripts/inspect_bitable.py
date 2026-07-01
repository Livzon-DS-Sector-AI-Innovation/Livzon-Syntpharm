"""Inspect Feishu Bitable table schema and compare with local field mapping.

Usage:
    cd dazah-backend
    uv run python scripts/inspect_bitable.py > scripts/inspect_result.txt

Requires FEISHU_APP_ID and FEISHU_APP_SECRET in environment.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings
from app.platform.integrations.feishu.client import FeishuClient

_settings = get_settings()
APP_TOKEN = _settings.FEISHU_BITABLE_APP_TOKEN
TABLE_ID = _settings.FEISHU_BITABLE_EMPLOYEE_TABLE_ID

# Fields expected by the current sync logic in service.py + employee_datasource.py
EXPECTED_FIELDS = {
    # Basic info
    "工号",
    "姓名",
    "域账号",
    "部门",
    "班组",
    "职位",
    "职类",
    "级别",
    # Personal info
    "性别",
    "籍贯",
    "政治面貌",
    "婚姻状况",
    "户籍类型",
    # Status / classification
    "统计类别",
    "分类",
    # Birth date (split into year/month/day in code)
    "年",
    "月",
    "日",
    "年龄",
    # Career
    "职称／职业资格",
    "职称类型",
    "工作年限",
    "厂龄",
    "司龄",
    # Education
    "学历",
    "毕业学校",
    "专业",
    "毕业时间",
    # IDs
    "身份证号",
    "身份证到期日",
    "身份证地址|家庭地址",
    "现住址",
    # Contract
    "合同期限",
    "第一次合同起点时间",
    "第一次合同终止时间",
    "第二次合同起点时间",
    "第二次合同终止时间",
    "第三次合同起点时间",
    "第三次合同终止时间",
    "第四次合同起点时间",
    "第四次合同终止时间",
    # Contact
    "手机",
    "邮箱地址",
    "紧急联系人电话",
    "紧急联系人|关系",
    # Banking / other
    "银行卡号",
    "培训档案编号",
    # Work history
    "参加工作时间",
    "进厂时间",
    "入丽珠时间",
    "异动（含曾经工作部门、岗位)",
    # Remarks
    "备注",
    # Formula / read-only fields (ignored on write but read on sync)
    "入职月份",
    "字段 1",
}

FIELD_TYPE_MAP = {
    1: "text",
    2: "number",
    3: "single_select",
    4: "multi_select",
    5: "date",
    7: "checkbox",
    11: "phone",
    13: "phone_v2",
    15: "url",
    17: "attachment",
    18: "link",
    20: "formula",
    21: "lookup",
    22: "rollup",
    23: "duplex_link",
    1001: "barcode",
    1002: "progress",
    1003: "currency",
    1004: "rating",
    1005: "auto_number",
}


def ft(t):
    return FIELD_TYPE_MAP.get(t, f"type_{t}")


async def inspect_table():
    client = FeishuClient()
    lines = []

    def out(s=""):
        lines.append(s)

    # ─── 0. List all tables in the base ───
    out("=" * 70)
    out("Base Info")
    out("=" * 70)
    try:
        tables_data = await client.request(
            "GET",
            f"/bitable/v1/apps/{APP_TOKEN}/tables",
            params={"page_size": 100},
        )
        tables = tables_data.get("items", [])
        out(f"  app_token: {APP_TOKEN}")
        out(f"  total_tables: {len(tables)}")
        for t in tables:
            tid = t.get("table_id", "")
            marker = " <-- TARGET" if tid == TABLE_ID else ""
            out(f"    - {t.get('name'):20s} | id={tid}{marker}")
    except Exception as e:
        out(f"  [!] Failed to list tables: {e}")
        tables = []

    # ─── 1. Fields ───
    out("")
    out("=" * 70)
    out("Fields")
    out("=" * 70)
    try:
        fields_data = await client.request(
            "GET",
            f"/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields",
            params={"page_size": 100},
        )
        fields = fields_data.get("items", [])
    except Exception as e:
        out(f"  [!] Failed to get fields: {e}")
        return "\n".join(lines)

    actual_names = set()
    for f in fields:
        name = f.get("field_name", "")
        actual_names.add(name)
        out(f"  - {name:20s} | type={ft(f.get('type')):15s} | id={f.get('field_id')}")

    # ─── 2. Field mapping comparison ───
    out("")
    out("=" * 70)
    out("Field Mapping Comparison")
    out("=" * 70)

    missing = EXPECTED_FIELDS - actual_names
    extra = actual_names - EXPECTED_FIELDS

    if missing:
        out(f"\n  [!] Missing in new table ({len(missing)} fields expected by code):")
        for name in sorted(missing):
            out(f"      - {name}")
    else:
        out("\n  [OK] All expected fields are present in the new table.")

    if extra:
        out(
            f"\n  [+] Extra fields in new table ({len(extra)} fields not used by code):"
        )
        for name in sorted(extra):
            out(f"      - {name}")
    else:
        out("\n  [i] No extra fields in the new table.")

    # ─── 3. Sample records ───
    out("")
    out("=" * 70)
    out("Sample Records (first 3)")
    out("=" * 70)
    try:
        records_data = await client.request(
            "POST",
            f"/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/search",
            json={"page_size": 3},
        )
        items = records_data.get("items", [])
        total = records_data.get("total", len(items))
    except Exception as e:
        out(f"  [!] Failed to get records: {e}")
        items = []
        total = 0

    out(f"  total_records: {total}\n")
    for i, rec in enumerate(items, 1):
        out(f"  [{i}] record_id={rec.get('record_id')}")
        for k, v in rec.get("fields", {}).items():
            preview = str(v)[:120] + ("..." if len(str(v)) > 120 else "")
            out(f"      {k}: {preview}")
        out("")

    # ─── 4. Summary ───
    out("=" * 70)
    out("Summary")
    out("=" * 70)
    out(f"  app_token:       {APP_TOKEN}")
    out(f"  table_id:        {TABLE_ID}")
    out(f"  Total fields:    {len(fields)}")
    out(f"  Total records:   {total}")
    out(f"  Expected fields: {len(EXPECTED_FIELDS)}")
    out(f"  Matched:         {len(EXPECTED_FIELDS & actual_names)}")
    out(f"  Missing:         {len(missing)}")
    out(f"  Extra:           {len(extra)}")
    if missing:
        out("\n  ACTION REQUIRED: Update _parse_feishu_record() in service.py")
        out("                   or rename fields in Feishu to match expectations.")
    else:
        out("\n  [OK] Field mapping looks good. Sync should work.")

    return "\n".join(lines)


if __name__ == "__main__":
    if not os.getenv("FEISHU_APP_ID") or not os.getenv("FEISHU_APP_SECRET"):
        print("[!] Please set FEISHU_APP_ID and FEISHU_APP_SECRET")
        sys.exit(1)

    result = asyncio.run(inspect_table())
    # Write to file first (always works)
    outfile = os.path.join(os.path.dirname(__file__), "inspect_result.txt")
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"[Saved to {outfile}]")
    # Try to print to console (may fail on Windows with GBK)
    try:
        print(result)
    except UnicodeEncodeError:
        print("[Console output skipped due to encoding; see file above]")
