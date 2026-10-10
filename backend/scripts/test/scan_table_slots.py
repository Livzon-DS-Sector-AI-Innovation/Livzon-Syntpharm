"""表格槽位识别诊断：列出母本里每张表格「为什么被识别 / 为什么被漏掉」。

用途：排查「文档内表格槽位没被识别」。对 uploads/doc-gen 下的母本逐个跑规则扫描器
（spec_draft._pick_header / pending_rows），把每张表的判定路径打印出来，并标出
草拟阶段丢弃整表的具体原因，便于定位是哪条规则太严。

用法：
    cd backend && uv run python scripts/test/scan_table_slots.py            # 默认全部母本
    cd backend && uv run python scripts/test/scan_table_slots.py <文件> ...  # 指定文件
"""

from __future__ import annotations

import argparse
import glob
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from docx.table import Table  # noqa: E402

from app.modules.research.doc_gen.anchors import (  # noqa: E402
    iter_all_paragraphs,
    resolve_slot,
    run_color,
)
from app.modules.research.doc_gen.docx_markdown import render_docx_markdown  # noqa: E402
from app.modules.research.doc_gen.grid import cell_text, distinct_row_cells, normalize  # noqa: E402
from app.modules.research.doc_gen.renderer import open_document  # noqa: E402
from app.modules.research.doc_gen.spec_draft import (  # noqa: E402
    _MAX_SLOTS,
    _is_seq_header,
    _pick_header,
    draft_spec_from_bytes,
    pending_rows,
)


def _classify(table: Table) -> tuple[str, str]:
    """返回 (结论, 原因)。结论 ∈ {识别, 丢弃, 漏扫}。"""
    rows = list(table.rows)
    if len(rows) < 2:
        return "丢弃", f"行数 {len(rows)} < 2（_pick_header 直接返回 None）"
    first = [cell_text(c) for c in distinct_row_cells(rows[0])]
    picked = _pick_header(table)
    if picked is None:
        blanks = sum(1 for text in first if not text)
        return "丢弃", (f"选不出表头：首行去重后 {len(first)} 格（空 {blanks} 格），第二行也不满足「≥2 格且全非空」")
    headers, header_rows, _filled, _review, grid_like = picked
    if grid_like:
        return "逐格", f"键值网格（首行空格过半）→ 交 _scan_key_value_tables 按单元格建槽，{len(headers)} 列"
    seq_key = next((f"c{pos + 1}" for pos, text in enumerate(headers) if _is_seq_header(text)), None)
    has_empty, has_placeholder, has_partial, total = pending_rows(rows, headers, header_rows, seq_key)
    if not (has_empty or has_placeholder or has_partial):
        return "丢弃", (
            f"表头 OK（{header_rows} 行 / {len(headers)} 列）但无待填迹象："
            f"数据区没有任何一行「全空 / 全占位符 / 多数格待填」" + (f"；合计行={total}" if total else "")
        )
    flavor = "空行" if has_empty else ("占位符行" if has_placeholder else "多数格待填")
    return "识别", f"表头 {header_rows} 行 / {len(headers)} 列，待填={flavor}"


def _dump_table(table: Table, limit: int = 8) -> None:
    """打印表格前若干行的逐格文本（去重合并后），用于人工判断规则为何不命中。"""
    from docx.oxml.ns import qn

    for r_idx, row in enumerate(list(table.rows)[:limit], start=1):
        parts: list[str] = []
        for cell in distinct_row_cells(row):
            tc = cell._tc
            span = tc.grid_span if tc.tcPr is not None else 1
            vmerge = ""
            if tc.tcPr is not None:
                vm = tc.tcPr.find(qn("w:vMerge"))
                if vm is not None:
                    vmerge = "[vM]" if (vm.get(qn("w:val")) or "continue") == "continue" else "[vM首]"
            parts.append(f"{cell_text(cell) or '·'}{vmerge}{f'×{span}' if span and span > 1 else ''}")
        print(f"    行{r_idx}（{len(parts)}格）: " + " | ".join(parts))


def _report(path: Path, *, show: int | None, as_markdown: bool) -> None:
    data = path.read_bytes()
    try:
        doc = open_document(data)
    except Exception as exc:  # noqa: BLE001 - 诊断脚本，损坏文件继续跑下一个
        print(f"\n### {path}\n  打开失败：{type(exc).__name__}: {exc}")
        return

    top = [(f"表{i + 1}", t) for i, t in enumerate(doc.tables)]
    nested: list[tuple[str, Table]] = []
    for i, table in enumerate(doc.tables, start=1):
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(distinct_row_cells(row)):
                for sub_idx, sub in enumerate(cell.tables, start=1):
                    nested.append((f"表{i}.r{r_idx + 1}c{c_idx + 1}.n{sub_idx}", sub))

    spec = draft_spec_from_bytes(data, name=path.stem)
    table_slots = [s for s in spec.slots if s.kind == "table"]
    labels = Counter(s.label for s in table_slots)
    collided = [label for label, count in labels.items() if count > 1]

    # 表格内段落里的「标签：」「蓝字提示」：草拟只扫 doc.paragraphs（正文），这些位置完全扫不到
    body_paras = list(doc.paragraphs)
    all_paras = iter_all_paragraphs(doc)
    in_table_paras = len(all_paras) - len(body_paras)

    def _label_like(text: str) -> bool:
        joined = normalize(text)
        return bool(joined) and len(joined) <= 60 and joined.endswith(("：", ":"))

    body_labels = sum(1 for p in body_paras if _label_like(p.text))
    table_labels = sum(1 for p in all_paras if _label_like(p.text)) - body_labels
    table_hints = sum(
        1
        for p in all_paras
        if normalize(p.text) and any(run_color(r).upper() in {c.upper() for c in spec.hint_colors} for r in p.runs)
    ) - sum(
        1
        for p in body_paras
        if normalize(p.text) and any(run_color(r).upper() in {c.upper() for c in spec.hint_colors} for r in p.runs)
    )

    print(f"\n### {path.relative_to(_ROOT.parent) if path.is_absolute() else path}")
    print(
        f"  表格内段落 {in_table_paras} 个，其中「标签：」{table_labels} 个、彩色提示 {max(table_hints, 0)} 个"
        f" —— 草拟只扫正文段落（正文标签 {body_labels} 个），表内这些位置当前**完全识别不到**"
    )
    cell_slots = [s for s in spec.slots if s.key.startswith("cell_")]
    print(
        f"  顶层表格 {len(top)} 张 / 嵌套表格 {len(nested)} 张（嵌套表规则完全遍历不到）"
        f" → 整表槽位 {len(table_slots)} 个 + 单元格槽位 {len(cell_slots)} 个；"
        f"全部槽位 {len(spec.slots)} 个（上限 {_MAX_SLOTS}）"
    )
    if collided:
        print(f"  ⚠ 去重按 (kind,label) 合并掉了同表头表格：{collided}")

    broken: list[str] = []
    for slot in spec.slots:
        try:
            resolve_slot(doc, slot)
        except Exception as exc:  # noqa: BLE001 - 诊断脚本需要收集所有定位失败
            broken.append(f"{slot.key}({slot.label}): {type(exc).__name__} {exc}")
    if broken:
        print(f"  ❌ 锚点解析失败 {len(broken)} 个（这些槽位生成时会写不进去）：")
        for line in broken[:12]:
            print(f"     - {line}")
    else:
        print("  ✅ 全部槽位锚点可在母本解析")
    for name, table in top:
        verdict, reason = _classify(table)
        mark = {"识别": "✅", "逐格": "🔲"}.get(verdict, "❌")
        print(f"  {mark} {name}: {reason}")
        if show is not None and name == f"表{show}":
            _dump_table(table)
    for name, table in nested:
        rows = len(list(table.rows))
        first = [cell_text(c) for c in distinct_row_cells(list(table.rows)[0])] if rows else []
        print(f"  ⚠️ {name}: 未参与扫描（嵌套表；{rows} 行，首行去重 {len(first)} 格）")
    if as_markdown:
        print("\n  ---- 模板 Markdown（前 60 行）----")
        for line in render_docx_markdown(data).splitlines()[:60]:
            print(f"  {line}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="表格槽位识别诊断")
    parser.add_argument("files", nargs="*", type=Path, help="母本文件（缺省=uploads/doc-gen 全部模板）")
    parser.add_argument("--show", type=int, default=None, help="额外打印第 N 张表的逐格文本")
    parser.add_argument("--md", action="store_true", help="额外打印该母本的模板 Markdown 前 60 行")
    args = parser.parse_args(argv)

    paths = args.files or sorted(Path(match) for match in glob.glob(str(_ROOT.parent / "uploads/doc-gen/*/template.*")))
    if not paths:
        print("未找到母本文件")
        return 1
    for path in paths:
        if not path.exists():
            print(f"\n### {path}\n  文件不存在")
            continue
        _report(path, show=args.show, as_markdown=args.md)
    print(
        "\n说明：❌ 的表格目前只能靠「新增填写项 → 候选位置」人工点选补上；"
        "⚠️ 嵌套表连候选补扫也覆盖不到（补扫同样只遍历 doc.tables）。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
