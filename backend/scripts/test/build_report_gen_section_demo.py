"""演示：资料比母本多时动态新增子章节并同步目录。

场景与线上一致：母本「4 工艺路线的调研」只有路线1-4，知识库里还有路线5、路线6。
脚本不调模型，直接用 ``append_subsection`` 落写入记录，再用 ``render_document`` 出稿，
产出两份 docx 供人工肉眼验收：

- ``dynamic-section-template.docx``：4 条路线的母本（含真实 TOC 域）；
- ``dynamic-section-demo.docx``：新增路线5、路线6 后的成稿（正文与目录各多两条）。

不绑定这个模板：传 ``--template`` 用任意真实母本，``--after-title`` 指定插在哪个已有
子标题之后；新增标题的编号按母本写法推断（``4.4`` / ``四、`` / ``（四）`` / ``第四章``）。

用法：``cd backend && uv run python scripts/test/build_report_gen_section_demo.py``
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

# 纯本地演示，不连飞书也不连库：补齐 settings.check() 必需的部署项，避免要求真实凭证
os.environ.setdefault("FEISHU__PLATFORM__APP_ID", "demo")
os.environ.setdefault("FEISHU__PLATFORM__APP_SECRET", "demo")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from docx import Document  # noqa: E402
from docx.enum.style import WD_STYLE_TYPE  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402

from app.modules.research.report_gen.fills import build_fills  # noqa: E402
from app.modules.research.report_gen.numbering import bump_number, parse_number  # noqa: E402
from app.modules.research.report_gen.outline import build_outline  # noqa: E402
from app.modules.research.report_gen.render import render_document  # noqa: E402
from app.modules.research.report_gen.structure import open_document  # noqa: E402
from app.modules.research.report_gen.tools import ReportGenRuntime  # noqa: E402

# 默认写系统临时目录：storage/ 归容器用户所有，本机普通用户没有写权限
DEFAULT_OUTPUT_DIR = Path(tempfile.gettempdir()) / "report_gen_section_demo"

ROUTES = {
    1: "路线1（mCPBA 氧化法）：2,4-二氨基-6-氯嘧啶经 mCPBA 氧化，再与哌啶缩合得米诺地尔。",
    2: "路线2（先氧化后缩合）：双氧水/乙酸氧化后再缩合，两步总收率约 62%。",
    3: "路线3（二氯嘧啶氨化法）：高压氨化后氧化，三废量较大。",
    4: "路线4（一锅法）：氧化与缩合连续操作，收率与纯度较优。",
    5: "路线5（酶催化氧化法）：以氧化酶替代 mCPBA，条件温和，单元操作减少一步。",
    6: "路线6（连续流缩合）：缩合段改连续流，停留时间缩短至 15 min，适合放大。",
}


class _Session:
    """写工具只落 ORM 行，演示脚本不需要真实数据库。"""

    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, row: Any) -> None:
        self.added.append(row)


def _docx(document: Any) -> bytes:
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _add_toc_entry(document: Any, title: str, page: str, style: str) -> Any:
    paragraph = document.add_paragraph(style=style)
    paragraph.add_run(title)
    tab_run = paragraph.add_run()
    tab_run._r.append(OxmlElement("w:tab"))
    paragraph.add_run(page)
    return paragraph


def _build_template() -> bytes:
    """4 条路线的母本：目录缓存 4.1-4.4，正文标题用明文编号（便于肉眼核对）。"""
    document = Document()
    existing = {style.name for style in document.styles}
    for name in ("toc 1", "toc 2"):
        if name not in existing:
            document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)

    document.add_paragraph("目录", style="Heading 1")
    field = document.add_paragraph()
    begin_run = field.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin_run._r.append(begin)
    instr_run = field.add_run()
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-2" \\h \\z \\u '
    instr_run._r.append(instr)
    separator_run = field.add_run()
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    separator_run._r.append(separate)

    _add_toc_entry(document, "4. 工艺路线的调研", "4", "toc 1")
    for route in (1, 2, 3, 4):
        _add_toc_entry(document, f"4.{route}. 路线{route}", "5", "toc 2")
    last_entry = _add_toc_entry(document, "5. 成本估算和分析", "6", "toc 1")
    end_run = last_entry.add_run()
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    end_run._r.append(end)

    document.add_paragraph("4 工艺路线的调研", style="Heading 1")
    for route in (1, 2, 3, 4):
        document.add_paragraph(f"4.{route} 路线{route}", style="Heading 2")
        document.add_paragraph(ROUTES[route])
    document.add_paragraph("5 成本估算和分析", style="Heading 1")
    document.add_paragraph("（本演示不涉及成本章节）")
    return _docx(document)


def _runtime(template: bytes) -> ReportGenRuntime:
    outline = build_outline(open_document(template))
    config = SimpleNamespace(
        write_batch_limit=10,
        search_query_limit=5,
        kb_top_k=6,
        disabled_tools=frozenset(),
    )
    job = SimpleNamespace(id=uuid4(), doc_code="DEMO-2026-001", drug_name="米诺地尔", supplement_text=None)
    project = SimpleNamespace(id=uuid4(), name="米诺地尔原料药")
    runtime = ReportGenRuntime(_Session(), job, project, outline, {}, config)
    runtime.sources["s1"] = {"source_name": "工艺路线调研资料.pdf", "evidence": "路线5/路线6 的工艺描述"}
    return runtime


def _route_anchor(template: bytes, after_title: str) -> tuple[int, int, bool, str]:
    """母本里「路线4」的标题段与正文段下标：新增子标题插在正文之后。

    返回（标题下标, 正文下标, 标题是否自动编号, 标题原文）。自动编号模板的标题文字是
    「路线4」，明文编号模板可能是「4.4 路线4」「四、路线4」，所以按关键字包含匹配。
    """
    document = open_document(template)
    outline = build_outline(document)
    for position in outline.positions:
        if position.kind != "paragraph":
            continue
        if position.heading < 2 or after_title not in (position.text or ""):
            continue
        return position.index, position.index + 1, position.numbered, position.text
    raise RuntimeError(f"母本里找不到包含「{after_title}」的子标题段落")


def _next_titles(heading_text: str, numbered: bool) -> tuple[str, str]:
    """按母本已有子标题的编号写法，推出新增两个子标题的文字。

    自动编号模板只给标题（编号由 Word 生成）；明文编号模板沿用上一条的编号格式，
    如「4.4 路线4」→「4.5 路线5」，「四、路线4」→「五、路线5」。
    """
    if numbered:
        return "路线5", "路线6"
    token = parse_number(heading_text)
    if token is None:
        return "路线5", "路线6"
    first = bump_number(token)
    if first is None:
        return "路线5", "路线6"
    second = bump_number(first)
    suffix = first.separator
    if second is None:
        return f"{first.render()}{suffix}路线5", "路线6"
    return f"{first.render()}{suffix}路线5", f"{second.render()}{suffix}路线6"


def _toc_preview(path: Path) -> list[str]:
    document = open_document(path.read_bytes())
    return [
        paragraph.text
        for paragraph in document.paragraphs
        if (paragraph.style.name or "").lower().startswith("toc") and paragraph.text.strip()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="生成动态子章节演示 docx")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="输出目录")
    parser.add_argument("--template", help="用真实母本 docx 跑一遍；不传则用内置 4 条路线母本")
    parser.add_argument("--after-title", default="路线4", help="插在哪个已有子标题之后（关键字匹配）")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    if args.template:
        template = Path(args.template).read_bytes()
        prefix = "custom-"
    else:
        template = _build_template()
        prefix = "dynamic-section-"

    heading_index, body_index, numbered, heading_text = _route_anchor(template, args.after_title)
    title5, title6 = _next_titles(heading_text, numbered)
    print(
        f"母本标题编号：{'Word 自动编号' if numbered else '明文编号'}；"
        f"插在「{args.after_title}」之后，新增标题：{title5} / {title6}"
    )

    runtime = _runtime(template)
    first = runtime.append_subsection(
        {
            "after": f"p{body_index}",
            "items": [
                {
                    "title": title5,
                    "title_clone_from": heading_index,
                    "body": [{"text": ROUTES[5], "clone_from": body_index}],
                    "source_ids": ["s1"],
                }
            ],
        }
    )
    second = runtime.append_subsection(
        {
            "after": "as1",
            "items": [
                {
                    "title": title6,
                    "title_clone_from": heading_index,
                    "body": [{"text": ROUTES[6], "clone_from": body_index}],
                    "source_ids": ["s1"],
                }
            ],
        }
    )
    print(f"新增路线5：{first.summary}")
    print(f"新增路线6：{second.summary}")

    output = render_document(
        template,
        build_fills(runtime.slot_rows.values()),
        meta={"title": "动态子章节演示"},
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{prefix}demo.docx"
    output_path.write_bytes(output.document)
    if not args.template:
        template_path = output_dir / f"{prefix}template.docx"
        template_path.write_bytes(template)
        print(f"母本：{template_path}")
    print(f"成稿：{output_path}")
    print("成稿目录条目：")
    for text in _toc_preview(output_path):
        print(f"  {text}")


if __name__ == "__main__":
    main()
