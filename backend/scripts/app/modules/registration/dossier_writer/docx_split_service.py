"""DOCX Template Splitting Service (Index-based Refactor)."""

import logging
import shutil
import time
from pathlib import Path
from typing import Any

from docx import Document

logger = logging.getLogger(__name__)
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def is_heading(element: Any, style_map: dict[str, int]) -> int | None:
    p_pr = element.find(".//w:pPr", NS)
    if p_pr is not None:
        # 1. Try named style (e.g., Heading1, 标题1)
        p_style = p_pr.find("w:pStyle", NS)
        if p_style is not None:
            style_name = p_style.get(f"{{{NS['w']}}}val")
            if style_name in style_map:
                return style_map[style_name]

        # 2. Fallback: Try outline level (w:outlineLvl)
        outline_lvl = p_pr.find("w:outlineLvl", NS)
        if outline_lvl is not None:
            val = outline_lvl.get(f"{{{NS['w']}}}val")
            if val is not None:
                try:
                    # outlineLvl is 0-based, we want 1-based level
                    return int(val) + 1
                except ValueError:
                    pass
    return None


def split_template(
    template_path: Path, output_dir: Path, chapter_codes: list[str], style_map: dict[str, int]
) -> dict[str, Path]:
    start_time = time.time()

    # Load original to identify ranges by index
    orig_doc = Document(str(template_path))
    orig_body = orig_doc.element.body
    total_elements = len(orig_body)

    # Identify which indices belong to which chapter
    chapter_indices: dict[str, list[int]] = {code: [] for code in chapter_codes}
    current_code = None

    for i, element in enumerate(orig_body):
        level = is_heading(element, style_map)
        if level is not None:
            text = element.text or ""
            for code in chapter_codes:
                if text.startswith(code):
                    current_code = code
                    break

        if current_code and current_code in chapter_indices:
            chapter_indices[current_code].append(i)

    result_paths = {}
    for code, indices in chapter_indices.items():
        if not indices:
            continue

        safe_code = code.replace(".", "_")
        target_path = output_dir / f"{safe_code}_{template_path.name}"

        # Copy template first
        shutil.copy2(template_path, target_path)

        # Load copy and delete elements NOT in the index range
        target_doc = Document(str(target_path))
        target_body = target_doc.element.body

        # We must iterate backwards to keep indices valid during deletion
        # But we need to know which indices to KEEP.
        keep_set = set(indices)

        # Always keep the last element if it's sectPr (section properties)
        # In python-docx, sectPr is usually part of the last paragraph or a separate element.
        # We'll ensure we don't delete the very last element of the body to preserve document structure.

        for i in reversed(range(total_elements)):
            if i not in keep_set:
                # Don't delete the very last element if it's the only one left or if it's sectPr
                if i == total_elements - 1 and len(target_body) == 1:
                    continue
                try:
                    elem = target_body[i]
                    target_body.remove(elem)
                except IndexError:
                    pass

        target_doc.save(str(target_path))
        result_paths[code] = target_path

    elapsed = time.time() - start_time
    logger.info("[Split] Completed", extra={"chapter_count": len(result_paths), "elapsed_seconds": round(elapsed, 2)})
    return result_paths
