"""PPT 渲染失真归因（只读诊断）。

回答三个问题：

1. 这份 PPT 到底声明了哪些字体（slides / layouts / masters / theme，含 `+mn-lt` 等主题引用）？
2. 每个声明字体在字体配置里**实际**命中了哪个文件，该文件是否真的含中文字形？
3. 渲染出的 PDF 里文字是否真的重叠（用户看到的「文字叠在一起」），哪几页、多少个位置？

不做任何写操作：不写数据库、不写对象存储、不改 PDF 缓存；
只在 `--out` 目录下生成 PDF 与每页 PNG 供人工逐页比对。

用法（容器内运行，脚本被 .dockerignore 排除，需先 docker cp 到 /tmp）：

    docker cp backend/scripts/test/diagnose_ppt_fonts.py erp-backend:/tmp/
    docker exec -w /app -e PYTHONPATH=/app erp-backend .venv/bin/python \
        /tmp/diagnose_ppt_fonts.py --project-id <uuid> --out /tmp/font-diag

也可以直接对本地文件跑（不需要应用环境）：

    .venv/bin/python scripts/test/diagnose_ppt_fonts.py --pptx a.pptx --label a
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"

#: 主题字体占位符 → theme1.xml 里的槽位
THEME_TOKENS = {
    "+mn-lt": ("minorFont", "latin"),
    "+mn-ea": ("minorFont", "ea"),
    "+mn-cs": ("minorFont", "cs"),
    "+mj-lt": ("majorFont", "latin"),
    "+mj-ea": ("majorFont", "ea"),
    "+mj-cs": ("majorFont", "cs"),
}

#: 名字里出现这些片段的字体，视为「中文版式字体」，必须在渲染环境里命中含 CJK 字形的文件
CJK_HINTS = (
    "雅黑",
    "宋体",
    "黑体",
    "楷体",
    "仿宋",
    "等线",
    "思源",
    "苹方",
    "华文",
    "微软雅黑",
    "yahei",
    "simsun",
    "simhei",
    "nsimsun",
    "kaiti",
    "fangsong",
    "dengxian",
    "source han",
    "pingfang",
    "noto sans cjk",
    "noto serif cjk",
    "songti",
    "heiti",
    "新細明體",
    "pmingliu",
    "mingliu",
)

#: 只关心中文脚本槽位；日/韩/泰等脚本的回退字体与本项目的失真无关，不进报表
CJK_SCRIPT_CODES = ("Hans", "Hant")

#: 同一行内两个词的横向重叠超过较小者宽度的这个比例，就判为「文字重叠」
OVERLAP_RATIO = 0.15
#: 重叠绝对宽度下限（pt），过滤掉抗锯齿/标点边距造成的 1~2pt 假阳性
OVERLAP_MIN_PT = 1.5


class DiagnoseError(RuntimeError):
    """诊断环境不满足要求（缺工具、缺源文件等）。"""


# ── 外部命令 ────────────────────────────────────────────────────────────────


def _run(command: list[str], timeout: int = 120) -> str:
    completed = subprocess.run(  # noqa: S603 - 命令由脚本常量与本机路径拼装
        command, capture_output=True, text=True, timeout=timeout, check=False
    )
    if completed.returncode != 0:
        raise DiagnoseError(f"{command[0]} 执行失败（{completed.returncode}）：{completed.stderr.strip()[:300]}")
    return completed.stdout


def _require_tools(names: tuple[str, ...]) -> None:
    missing = [name for name in names if not shutil.which(name)]
    if missing:
        raise DiagnoseError("缺少工具：" + "、".join(missing) + "（需要 poppler-utils 与 libreoffice）")


# ── PPT 声明字体 ────────────────────────────────────────────────────────────


@dataclass
class DeclaredFont:
    """一个 PPT 里声明过的字体，以及它在哪几类部件里出现。"""

    name: str
    places: set[str] = field(default_factory=set)

    @property
    def expects_cjk(self) -> bool:
        lowered = self.name.lower()
        return any(hint in lowered for hint in CJK_HINTS)


def _theme_fonts(zf: zipfile.ZipFile) -> tuple[dict[str, str], dict[str, str]]:
    """解析 theme1.xml，返回 (占位符→字体名, script→字体名)。

    坑点：`a:majorFont/a:ea` 在微软导出的主题里经常是空串，
    真正的中文字体挂在 `<a:font script="Hans" typeface="宋体"/>` 上。
    LibreOffice 取东亚字体时正是回落到 script=Hans 的声明，
    所以这里必须把 script 映射也纳入归因，否则会漏掉真正的元凶。
    """
    tokens: dict[str, str] = {}
    scripts: dict[str, str] = {}
    for name in zf.namelist():
        if not re.fullmatch(r"ppt/theme/theme\d+\.xml", name):
            continue
        try:
            root = ET.fromstring(zf.read(name))
        except ET.ParseError:  # 主题损坏时不影响其它部件的归因
            continue
        hans: str | None = None
        for node in root.iter(f"{{{NS_A}}}font"):
            script = node.get("script")
            typeface = node.get("typeface")
            if not script or not typeface:
                continue
            scripts.setdefault(script, typeface)
            if script == "Hans":
                hans = typeface
        for token, (group, slot) in THEME_TOKENS.items():
            node = root.find(f".//{{{NS_A}}}{group}/{{{NS_A}}}{slot}")
            typeface = node.get("typeface") if node is not None else None
            if typeface:
                tokens[token] = typeface
            elif slot in ("ea", "cs") and hans:
                # 空的 ea/cs 槽位 → 中文实际用 script=Hans 声明的字体
                tokens[token] = hans
    return tokens, scripts


def parse_declared_fonts(pptx_path: Path) -> dict[str, DeclaredFont]:
    """收集 PPT 声明的全部字体（含主题与 script 映射，不含占位符本身）。"""
    fonts: dict[str, DeclaredFont] = {}
    with zipfile.ZipFile(pptx_path) as zf:
        theme_map, script_map = _theme_fonts(zf)
        for token, typeface in theme_map.items():
            fonts.setdefault(typeface, DeclaredFont(typeface)).places.add(f"theme({token})")
        for script, typeface in script_map.items():
            if script not in CJK_SCRIPT_CODES:
                continue
            fonts.setdefault(typeface, DeclaredFont(typeface)).places.add(f"theme(script={script})")

        parts = {
            r"ppt/slides/slide\d+\.xml": "slide",
            r"ppt/slideLayouts/slideLayout\d+\.xml": "layout",
            r"ppt/slideMasters/slideMaster\d+\.xml": "master",
        }
        for name in zf.namelist():
            place = next((label for pattern, label in parts.items() if re.fullmatch(pattern, name)), None)
            if place is None:
                continue
            try:
                root = ET.fromstring(zf.read(name))
            except ET.ParseError:
                continue
            suffix = Path(name).stem
            for tag in ("latin", "ea", "cs"):
                for node in root.iter(f"{{{NS_A}}}{tag}"):
                    typeface = node.get("typeface")
                    if not typeface:
                        continue
                    resolved = theme_map.get(typeface, typeface)
                    fonts.setdefault(resolved, DeclaredFont(resolved)).places.add(f"{place}:{suffix}:{tag}")
    return fonts


def slide_size_inches(pptx_path: Path) -> tuple[float, float] | None:
    """源 PPT 画布尺寸（英寸），用于核对 4:3 / 16:9 是否被转换过程改掉。"""
    with zipfile.ZipFile(pptx_path) as zf:
        if "ppt/presentation.xml" not in zf.namelist():
            return None
        try:
            root = ET.fromstring(zf.read("ppt/presentation.xml"))
        except ET.ParseError:
            return None
    node = root.find(f".//{{{NS_P}}}sldSz")
    if node is None:
        return None
    try:
        width = int(node.get("cx", "0")) / 914400
        height = int(node.get("cy", "0")) / 914400
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return round(width, 2), round(height, 2)


# ── fontconfig 命中 ─────────────────────────────────────────────────────────


def cjk_capable_files() -> set[str]:
    """当前环境里真正覆盖简体中文字形的字体文件集合。"""
    out = _run(["fc-list", ":lang=zh-cn", "-f", "%{file}\n"])
    return {line.strip() for line in out.splitlines() if line.strip()}


def font_match(name: str, cjk_files: set[str]) -> tuple[str, str, bool]:
    """跑一次 fc-match，返回 (命中 family, 命中文件, 是否含中文字形)。"""
    out = _run(["fc-match", "-f", "%{family}|%{file}", name]).strip()
    family, _, path = out.partition("|")
    return family, path, path in cjk_files


# ── PDF 尺寸与渲染 ──────────────────────────────────────────────────────────


def pdf_page_sizes(pdf_path: Path) -> list[tuple[float, float]]:
    """每页 PDF 尺寸（pt）。"""
    out = _run(["pdfinfo", "-f", "1", "-l", "9999", str(pdf_path)])
    sizes: list[tuple[float, float]] = []
    for line in out.splitlines():
        if not line.startswith("Page") or "size:" not in line:
            continue
        match = re.search(r"size:\s*([\d.]+)\s+x\s+([\d.]+)", line)
        if match:
            sizes.append((float(match.group(1)), float(match.group(2))))
    return sizes


def render_pages(pdf_path: Path, out_dir: Path, dpi: int) -> list[Path]:
    """导出每页 PNG（逐页 pdftoppm，避免一次把整本读进内存）。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(pdf_page_sizes(pdf_path))
    paths: list[Path] = []
    for index in range(1, total + 1):
        prefix = out_dir / f"page-{index:03d}"
        _run(
            [
                "pdftoppm",
                "-png",
                "-singlefile",
                "-r",
                str(dpi),
                "-f",
                str(index),
                "-l",
                str(index),
                str(pdf_path),
                str(prefix),
            ]
        )
        produced = prefix.with_suffix(".png")
        if produced.exists():
            paths.append(produced)
    return paths


@dataclass
class OverlapHit:
    """一处文字重叠。"""

    page: int
    left: str
    right: str
    overlap_pt: float


def detect_word_overlaps(pdf_path: Path) -> list[OverlapHit]:
    """逐行检测同页两个词的横向包围盒重叠。

    正常排版下同一行的词只会相邻、不会交叠；字体被替换导致字宽缩小后，
    后一个词的起点会压进前一个词的字形范围，形成用户看到的「文字重叠」。
    """
    xml_text = _run(["pdftotext", "-bbox-layout", "-enc", "UTF-8", str(pdf_path), "-"])
    if not xml_text.strip():
        return []
    root = ET.fromstring(xml_text)
    xhtml = "{http://www.w3.org/1999/xhtml}"
    hits: list[OverlapHit] = []
    for page_no, page in enumerate(root.iter(f"{xhtml}page"), start=1):
        for line in page.iter(f"{xhtml}line"):
            boxes: list[tuple[float, float, str]] = []
            for word in line.iter(f"{xhtml}word"):
                try:
                    x_min = float(word.get("xMin", "0"))
                    x_max = float(word.get("xMax", "0"))
                except ValueError:
                    continue
                text = (word.text or "").strip()
                if not text or x_max <= x_min:
                    continue
                boxes.append((x_min, x_max, text))
            boxes.sort(key=lambda item: item[0])
            for previous, current in zip(boxes, boxes[1:]):
                overlap = min(previous[1], current[1]) - max(previous[0], current[0])
                if overlap <= OVERLAP_MIN_PT:
                    continue
                narrower = min(previous[1] - previous[0], current[1] - current[0])
                if narrower > 0 and overlap / narrower > OVERLAP_RATIO:
                    hits.append(
                        OverlapHit(
                            page=page_no,
                            left=previous[2],
                            right=current[2],
                            overlap_pt=round(overlap, 2),
                        )
                    )
    return hits


# ── 取源与转换 ──────────────────────────────────────────────────────────────


def fetch_project_source(project_id: str, target_dir: Path) -> tuple[Path, dict[str, Any]]:
    """从对象存储取项目的源 PPT（只读），返回本地路径与项目元信息。"""
    import asyncio

    from sqlalchemy import select

    from app.core import storage
    from app.core.database import async_session_factory
    from app.modules.agent.models import PptVideoProject
    from app.modules.agent.service import BUCKET_MODULE

    async def _load() -> dict[str, Any]:
        import uuid as uuid_lib

        async with async_session_factory() as session:
            project = await session.scalar(
                select(PptVideoProject).where(PptVideoProject.id == uuid_lib.UUID(project_id))
            )
            if project is None:
                raise DiagnoseError(f"项目不存在：{project_id}")
            payload = storage.get_object(BUCKET_MODULE, project.source_object_key)
            if payload is None:
                raise DiagnoseError(f"源 PPT 已丢失：{project.source_object_key}")
            data, _content_type = payload
            target_dir.mkdir(parents=True, exist_ok=True)
            suffix = Path(project.source_filename).suffix or ".pptx"
            path = target_dir / f"source{suffix}"
            path.write_bytes(data)
            return {
                "id": str(project.id),
                "name": project.name,
                "source_filename": project.source_filename,
                "source_version": project.source_version,
                "page_images_version": project.page_images_version,
                "source_sha256": project.source_sha256,
                "slide_count": project.slide_count,
                "path": str(path),
            }

    info = asyncio.run(_load())
    # 全局 async engine 绑定在第一次 `asyncio.run` 的事件循环上；脚本常一次诊断多个项目，
    # 不 dispose 会在第二个项目上抛 "attached to a different loop"。脚本只读，复用无益。
    asyncio.run(_dispose_engine())
    return Path(info["path"]), info


async def _dispose_engine() -> None:
    from app.core.database import engine

    await engine.dispose()


def convert_with_soffice(pptx_path: Path, out_dir: Path) -> Path:
    """用与生产完全相同的 invoke 方式转换（独立 profile，避免锁冲突）。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    profile = out_dir / "lo-profile"
    profile.mkdir(parents=True, exist_ok=True)
    binary = shutil.which("soffice") or shutil.which("libreoffice")
    if not binary:
        raise DiagnoseError("未安装 LibreOffice，无法转换")
    _run(
        [
            binary,
            f"-env:UserInstallation=file://{profile.resolve()}",
            "--headless",
            "--norestore",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(pptx_path),
        ],
        timeout=900,
    )
    pdf_path = out_dir / f"{pptx_path.stem}.pdf"
    if not pdf_path.exists():
        raise DiagnoseError("soffice 未产出 PDF")
    return pdf_path


# ── 报告 ────────────────────────────────────────────────────────────────────


def build_report(  # noqa: PLR0913 - 报告需要完整上下文
    label: str,
    project: dict[str, Any] | None,
    pptx_path: Path,
    pdf_path: Path | None,
    fonts: dict[str, DeclaredFont],
    matches: dict[str, tuple[str, str, bool]],
    size_inches: tuple[float, float] | None,
    page_sizes: list[tuple[float, float]],
    overlaps: list[OverlapHit],
    png_dir: Path | None,
    dpi: int,
) -> str:
    lines: list[str] = [f"### {label}", ""]
    if project:
        lines += [
            f"- 项目：`{project['name']}`（id `{project['id']}`，源 v{project['source_version']}，"
            f"页图 v{project['page_images_version']}，{project['slide_count']} 页）",
            f"- 源文件：`{project['source_filename']}`，sha256 `{project['source_sha256'][:16]}…`",
        ]
    lines.append(f"- 输入文件：`{pptx_path}`")

    if size_inches:
        width, height = size_inches
        ratio = width / height if height else 0
        shape = "16:9" if abs(ratio - 16 / 9) < 0.05 else "4:3" if abs(ratio - 4 / 3) < 0.05 else f"{ratio:.3f}"
        lines.append(f"- 源画布：{width} × {height} 英寸（{shape}）")

    if pdf_path is not None:
        sizes = ", ".join(f"{round(w)}×{round(h)}pt" for w, h in page_sizes[:3])
        more = "" if len(page_sizes) <= 3 else f" …（共 {len(page_sizes)} 页）"
        px = ", ".join(f"{round(w / 72 * dpi)}×{round(h / 72 * dpi)}px" for w, h in page_sizes[:1])
        lines.append(f"- soffice 产出 PDF：`{pdf_path}`")
        lines.append(f"- PDF 页尺寸：{sizes}{more}；@{dpi}dpi → {px}")

    lines += [
        "",
        "| PPT 声明字体 | 实际命中 family | 命中文件 | 含中文字形 | 需要中文 | 判定 | 出现位置 |",
        "|---|---|---|---|---|---|---|",
    ]
    for name in sorted(fonts, key=lambda item: (not fonts[item].expects_cjk, item)):
        family, path, has_cjk = matches[name]
        declared = fonts[name]
        need = "是" if declared.expects_cjk else "—"
        verdict = "✓" if (has_cjk or not declared.expects_cjk) else "✗ 中文回退到非中文字体"
        places = sorted(declared.places)
        place_text = places[0] + (f" 等 {len(places)} 处" if len(places) > 1 else "")
        lines.append(
            f"| `{name}` | {family} | `{Path(path).name if path else '—'}` | "
            f"{'是' if has_cjk else '否'} | {need} | {verdict} | {place_text} |"
        )

    lines += ["", "| 页码 | 重叠处数 | 示例（左 ← 右） | 重叠宽度 |", "|---|---|---|---|"]
    if overlaps:
        by_page: dict[int, list[OverlapHit]] = {}
        for hit in overlaps:
            by_page.setdefault(hit.page, []).append(hit)
        for page in sorted(by_page):
            sample = by_page[page][0]
            lines.append(
                f"| {page} | {len(by_page[page])} | `{sample.left}` ← `{sample.right}` | {sample.overlap_pt}pt |"
            )
    else:
        lines.append("| — | 0 | 未检出文字重叠 | — |")

    lines.append("")
    if png_dir is not None:
        lines.append(f"- 逐页 PNG（供与源 PPT 目视比对）：`{png_dir}`")
    lines.append("")
    return "\n".join(lines)


def diagnose(  # noqa: PLR0913 - 诊断入口参数一一对应 CLI
    label: str,
    pptx_path: Path,
    out_dir: Path,
    dpi: int,
    project: dict[str, Any] | None = None,
    render: bool = True,
) -> tuple[str, list[OverlapHit], dict[str, tuple[str, str, bool]]]:
    """跑完一条源的完整诊断，返回 (markdown 片段, 重叠列表, 字体命中表)。"""
    fonts = parse_declared_fonts(pptx_path)
    cjk_files = cjk_capable_files()
    matches = {name: font_match(name, cjk_files) for name in fonts}
    size_inches = slide_size_inches(pptx_path)

    pdf_path: Path | None = None
    page_sizes: list[tuple[float, float]] = []
    overlaps: list[OverlapHit] = []
    png_dir: Path | None = None
    if render:
        pdf_dir = out_dir / "pdf"
        pdf_path = convert_with_soffice(pptx_path, pdf_dir)
        page_sizes = pdf_page_sizes(pdf_path)
        overlaps = detect_word_overlaps(pdf_path)
        png_dir = out_dir / "png"
        render_pages(pdf_path, png_dir, dpi)

    report = build_report(
        label=label,
        project=project,
        pptx_path=pptx_path,
        pdf_path=pdf_path,
        fonts=fonts,
        matches=matches,
        size_inches=size_inches,
        page_sizes=page_sizes,
        overlaps=overlaps,
        png_dir=png_dir,
        dpi=dpi,
    )
    return report, overlaps, matches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PPT→PDF 渲染失真归因（只读）")
    parser.add_argument("--pptx", type=Path, help="直接指定本地 PPTX")
    parser.add_argument("--label", help="报告标题，默认取文件名")
    parser.add_argument("--project-id", action="append", default=[], help="从对象存储取该项目的源 PPT，可重复")
    parser.add_argument("--out", type=Path, default=Path(tempfile.gettempdir()) / "font-diag", help="输出目录")
    parser.add_argument("--dpi", type=int, default=150, help="导出 PNG 的 dpi，默认与生产一致")
    parser.add_argument("--no-render", action="store_true", help="只出字体矩阵，不跑 soffice")
    parser.add_argument("--json", action="store_true", help="额外输出机器可读结果")
    parser.add_argument("--fail-on-issue", action="store_true", help="检出中文字体回退或文字重叠时以非 0 退出")
    args = parser.parse_args(argv)

    _require_tools(("fc-match", "fc-list"))
    if not args.no_render:
        _require_tools(("soffice", "pdfinfo", "pdftoppm", "pdftotext"))

    payload: list[dict[str, Any]] = []
    issues = 0
    # 每个项目一出结果就打印：多项目诊断跑十几分钟，中途失败不该丢掉已完成的部分
    print("# PPT 渲染失真归因\n", flush=True)

    try:
        if args.pptx:
            label = args.label or args.pptx.stem
            report, overlaps, matches = diagnose(
                label=label,
                pptx_path=args.pptx,
                out_dir=args.out / label,
                dpi=args.dpi,
                render=not args.no_render,
            )
            print(report, flush=True)
            missed = [name for name, hit in matches.items() if not hit[2]]
            issues += len(overlaps) + len(missed)
            payload.append(
                {
                    "label": label,
                    "overlaps": len(overlaps),
                    "fonts": {k: list(v) for k, v in matches.items()},
                }
            )

        for index, project_id in enumerate(args.project_id, start=1):
            pptx_path, project = fetch_project_source(project_id, args.out / f"project-{index}")
            label = args.label or project["name"]
            report, overlaps, matches = diagnose(
                label=f"{label}（{project_id}）",
                pptx_path=pptx_path,
                out_dir=args.out / f"project-{index}",
                dpi=args.dpi,
                project=project,
                render=not args.no_render,
            )
            print(report, flush=True)
            missed = [name for name, hit in matches.items() if not hit[2]]
            issues += len(overlaps)
            payload.append(
                {
                    "label": label,
                    "project_id": project_id,
                    "overlaps": len(overlaps),
                    "fonts_without_cjk": missed,
                    "fonts": {name: list(hit) for name, hit in matches.items()},
                }
            )
    except DiagnoseError as exc:
        print(f"诊断失败：{exc}", file=sys.stderr)
        return 2

    if args.json:
        print("\n```json")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("```")

    if args.fail_on_issue and issues:
        print(f"\n检出 {issues} 项问题（字体回退 / 文字重叠）", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
