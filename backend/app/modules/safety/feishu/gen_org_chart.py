"""生成公司组织架构图 (Markdown)。

#219：数据源改为 HR 主数据（``hr.departments`` / ``hr.employee_profiles``），
经 HR ``public_api`` 只读访问；``identity.departments`` 已下线。

用法: uv run python -X utf8 -m app.modules.safety.feishu.gen_org_chart
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from app.core.database import async_session_factory
from app.modules.hr.public_api import list_current_profiles, list_department_rows

logger = logging.getLogger(__name__)

_OUTPUT = Path(__file__).resolve().parent.parent.parent.parent.parent / "org_chart.md"


async def generate(output_path: str | Path | None = None) -> str:
    """生成组织架构 Markdown 并写入文件。

    Args:
        output_path: 输出路径，默认项目根目录 org_chart.md

    Returns:
        Markdown 文本
    """
    out_path = Path(output_path) if output_path else _OUTPUT

    async with async_session_factory() as session:
        depts = await list_department_rows(session)
        _, people_total = await list_current_profiles(session, limit=1)

        def _leader_name(row: dict[str, Any]) -> str:
            names = [str(name) for name in (row.get("leader_names") or []) if name]
            return names[0] if names else "-"

        # 构建树
        dept_map = {row["feishu_department_id"]: row for row in depts if row["feishu_department_id"]}
        children: dict[str, list[dict[str, Any]]] = {}
        roots: list[dict[str, Any]] = []
        for row in depts:
            parent_id = row["parent_feishu_department_id"] or ""
            if parent_id and parent_id in dept_map:
                children.setdefault(parent_id, []).append(row)
            else:
                roots.append(row)

        lines = [
            "# 丽珠集团福州福兴医药有限公司 组织架构",
            f"共 {len(depts)} 个部门，{people_total} 人",
            "",
        ]

        def _render(row: dict[str, Any], indent: int = 0) -> None:
            prefix = "  " * indent
            lines.append(f"{prefix}├─ {row['name']}  【{_leader_name(row)}】({row['member_count']}人)")
            for child in children.get(row["feishu_department_id"], []):
                _render(child, indent + 1)

        for root in sorted(roots, key=lambda row: (row["order"] or 0, row["name"] or "")):
            _render(root)

        output = "\n".join(lines)
        out_path.write_text(output, encoding="utf-8")
        logger.info("组织架构图已写入 %s", out_path)
        return output


async def main() -> None:
    output = await generate()
    logger.info(output)


if __name__ == "__main__":
    asyncio.run(main())
