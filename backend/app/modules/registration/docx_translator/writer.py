"""
DOCX 翻译器 - 回写器
将译文按段落ID映射回原文位置，在原文段落后插入新段落
"""

import logging
from copy import deepcopy
from typing import Any

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from .engine_models import TextUnit, TranslationResult

logger = logging.getLogger(__name__)


class DocxWriter:
    """DOCX 回写器"""

    def __init__(
        self,
        mode: str = "bilingual",
        target_lang: str = "zh",
        fallback_results: dict[str, str] | None = None,
    ) -> None:
        """
        mode: 'bilingual' 保留原文+在段落后追加译文
              'replace'    将原文替换为译文（保留段落格式）
        target_lang: 目标语言，影响译文字体设置
        fallback_results: {unit_id: translated_text} 回退译文映射，replace模式下当翻译失败时使用
        """
        self.mode = mode
        self.target_lang = target_lang
        self.fallback_results = fallback_results or {}  # 回退译文映射

    def write(
        self,
        doc: Any,
        output_path: str,
        units: list[TextUnit],
        results: list[TranslationResult],
    ) -> None:
        """
        将翻译结果回写到 DOCX 文件
        doc: 从 extractor 传入的 Document 对象（同一个实例）
        """

        # 建立 ID -> 翻译结果 映射
        result_map = {r.unit_id: r for r in results}

        processed_count = 0
        failed_count = 0
        skipped_empty = 0
        fallback_used = 0  # 使用回退译文的计数

        # 收集需要处理的 unit（过滤掉失败的）
        units_to_process = []
        for unit in units:
            if unit.is_empty:
                skipped_empty += 1
                continue
            result = result_map.get(unit.id)
            if result is None:
                failed_count += 1
                continue
            if not result.success or not result.translated_text:
                # 【回退机制】replace 模式下，如果 fallback 中有译文，仍尝试处理
                if self.mode == "replace" and unit.id in self.fallback_results and self.fallback_results[unit.id]:
                    # 创建虚拟的成功结果，使用 fallback 译文
                    result = TranslationResult(
                        unit_id=unit.id,
                        original_text=unit.text,
                        translated_text=self.fallback_results[unit.id],
                        success=True,
                    )
                    fallback_used += 1
                else:
                    failed_count += 1
                    continue
            units_to_process.append((unit, result))

        def _parse_path_for_sort(path: str):
            """将 table[0].row[1].cell[2] 解析为可正确数值排序的元组"""
            import re

            if not path:
                return ()
            return tuple(int(m) for m in re.findall(r"\[(\d+)\]", path))

        def get_element_index(elem):
            """获取元素在父节点中的索引"""
            parent = elem.getparent()
            if parent is None:
                return 0
            try:
                return list(parent).index(elem)
            except ValueError:
                return 0

        def sort_key(item):
            unit, _ = item
            if not unit.table_path:
                # 正文段落：按在文档 body 中的位置排序
                para_idx = get_element_index(unit.paragraph_element)
                return ((-1,), para_idx)
            else:
                # 表格段落：按表格路径解析的数值 + 单元格内段落索引排序
                # 不同单元格的段落互不影响插入位置，用路径区分分组
                path_nums = _parse_path_for_sort(unit.table_path)
                return (path_nums, unit.paragraph_index)

        # 记录已经处理过的原始段落，避免重复回写同一个段落（例如合并单元格重复引用）
        processed_paragraphs = set()

        if self.mode == "bilingual":
            # 双语模式：逆序插入，避免位置偏移
            units_to_process.sort(key=sort_key, reverse=True)

            # 将同段落+同单元格路径的多子段 unit 分组，统一处理
            # 用 (paragraph_element_id, table_path) 分组，避免共享合并单元格
            # 的段落被错误合并到同一组导致重复翻译。
            from collections import defaultdict

            para_groups = defaultdict(list)
            for item in units_to_process:
                unit = item[0]
                group_key = (id(unit.paragraph_element), unit.table_path)
                para_groups[group_key].append(item)

            # 先处理多子段组（按段落位置逆序）
            def _group_sort_key(item):
                group_key, group = item
                unit = group[0][0]
                return sort_key((unit, None))

            sorted_groups = sorted(para_groups.items(), key=_group_sort_key, reverse=True)
            for group_key, group in sorted_groups:
                para_id = group_key[0]
                if len(group) == 1:
                    unit, result = group[0]
                    if para_id not in processed_paragraphs:
                        self._insert_translation_paragraph(unit, result.translated_text)
                        processed_paragraphs.add(para_id)
                        processed_count += 1
                else:
                    if para_id not in processed_paragraphs:
                        self._insert_multi_sub(group, processed_paragraphs)
                        processed_count += len(group)

        else:
            # 替换模式：正序处理即可（不插入新元素，不偏移）
            units_to_process.sort(key=sort_key)
            for unit, result in units_to_process:
                orig_id = id(unit.paragraph_element)
                if orig_id in processed_paragraphs:
                    logger.warning(
                        "skip duplicated paragraph write-back: unit_id=%s path=%s",
                        unit.id,
                        unit.table_path or "body",
                        extra={"biz_module": "registration"},
                    )
                    failed_count += 1
                    continue
                self._replace_paragraph_text(unit, result.translated_text)
                processed_paragraphs.add(orig_id)
                processed_count += 1

        # 保存
        doc.save(output_path)

        logger.info(
            "docx write-back done: mode=%s processed=%d fallback=%d failed=%d",
            self.mode,
            processed_count,
            fallback_used,
            failed_count,
            extra={"biz_module": "registration"},
        )

    def _get_original_font_properties(self, original_p) -> dict:
        """提取原文段落的字体格式属性（字体大小、字体族等）
        优先检查段落级别默认属性 pPr/rPr，再检查有文本内容的 run，
        【修正】按文本内容最多的 run 取字号（而非最大字号），更准确反映主体文本字号
        """
        props = {
            "sz": None,  # 字体大小 (half-points)
            "szCs": None,  # 复杂脚本字体大小
            "rFonts": {},  # 字体族 {ascii, hAnsi, eastAsia, cs}
        }

        # 1. 先检查段落级别的默认 run 属性 (pPr/rPr) —— 标题字号常定义在这里
        pPr = original_p.find(qn("w:pPr"))
        if pPr is not None:
            def_rPr = pPr.find(qn("w:rPr"))
            if def_rPr is not None:
                sz_elem = def_rPr.find(qn("w:sz"))
                if sz_elem is not None:
                    props["sz"] = sz_elem.get(qn("w:val"))
                szCs_elem = def_rPr.find(qn("w:szCs"))
                if szCs_elem is not None:
                    props["szCs"] = szCs_elem.get(qn("w:val"))
                rFonts = def_rPr.find(qn("w:rFonts"))
                if rFonts is not None:
                    for attr in ["ascii", "hAnsi", "eastAsia", "cs"]:
                        val = rFonts.get(qn(f"w:{attr}"))
                        if val:
                            props["rFonts"][attr] = val

        # 2. 再遍历 run 级别属性，按文本内容长度取主体 run 的格式
        # 收集每个有文本的 run 的信息：(文本长度, 字号, 字体族字典)
        run_info = []
        for r in original_p.findall(qn("w:r")):
            rPr = r.find(qn("w:rPr"))
            if rPr is None:
                continue

            # 【跳过没有实际文本的空 run】
            t = r.find(qn("w:t"))
            if t is None or not t.text:
                continue
            text_len = len(t.text.strip())
            if text_len == 0:
                continue

            sz = None
            sz_elem = rPr.find(qn("w:sz"))
            if sz_elem is not None:
                sz = sz_elem.get(qn("w:val"))

            # 收集当前 run 的完整字体族（避免跨 run 混合）
            run_fonts = {}
            rFonts = rPr.find(qn("w:rFonts"))
            if rFonts is not None:
                for attr in ["ascii", "hAnsi", "eastAsia", "cs"]:
                    val = rFonts.get(qn(f"w:{attr}"))
                    if val:
                        run_fonts[attr] = val

            run_info.append((text_len, sz, run_fonts))

        # 【修正】按文本长度降序，取最长文本 run 的字号和字体族
        if run_info:
            run_info.sort(key=lambda x: x[0], reverse=True)
            dominant_sz, dominant_fonts = run_info[0][1], run_info[0][2]
            if dominant_sz is not None:
                props["sz"] = dominant_sz
            if dominant_fonts:
                props["rFonts"].update(dominant_fonts)

        return props

    def _build_run_properties(self, original_p, translated_text: str, inline_formats: list = None) -> OxmlElement:
        """构建译文 run 的格式属性
        字体大小保持原文 + 西文强制 Times New Roman + 根据目标语言设置 eastAsia
        【新增】保留原文的下划线、加粗、斜体等内联格式
        """
        rPr = OxmlElement("w:rPr")

        # 1. 复制原文的字体大小
        orig_props = self._get_original_font_properties(original_p)
        if orig_props["sz"] is not None:
            sz = OxmlElement("w:sz")
            sz.set(qn("w:val"), orig_props["sz"])
            rPr.append(sz)
        if orig_props["szCs"] is not None:
            szCs = OxmlElement("w:szCs")
            szCs.set(qn("w:val"), orig_props["szCs"])
            rPr.append(szCs)

        # 2. 设置字体族
        rFonts = OxmlElement("w:rFonts")
        if self.target_lang == "en":
            # 【英文翻译】全部强制 Times New Roman，避免宋体回退
            rFonts.set(qn("w:ascii"), "Times New Roman")
            rFonts.set(qn("w:hAnsi"), "Times New Roman")
            rFonts.set(qn("w:cs"), "Times New Roman")
            rFonts.set(qn("w:eastAsia"), "Times New Roman")
        else:
            # 【中文翻译】西文 Times New Roman，中文保留原文或默认宋体
            rFonts.set(qn("w:ascii"), "Times New Roman")
            rFonts.set(qn("w:hAnsi"), "Times New Roman")
            rFonts.set(qn("w:cs"), "Times New Roman")
            if "eastAsia" in orig_props["rFonts"]:
                rFonts.set(qn("w:eastAsia"), orig_props["rFonts"]["eastAsia"])
            else:
                rFonts.set(qn("w:eastAsia"), "宋体")
        rPr.append(rFonts)

        # 3. 译文用蓝色（仅在双语对照模式下）
        if self.mode == "bilingual":
            color = OxmlElement("w:color")
            color.set(qn("w:val"), "0000FF")
            rPr.append(color)

        # 4. 如果是中文内容，设置语言标记（有助于Word正确选择字体）
        has_chinese = any("一" <= c <= "鿿" for c in translated_text)
        if has_chinese:
            lang = OxmlElement("w:lang")
            lang.set(qn("w:eastAsia"), "zh-CN")
            rPr.append(lang)

        # 5. 【新增】保留原文的下划线、加粗、斜体等内联格式
        # inline_formats 存储格式值：'b', 'i', 'u:single', 'u:double', 'u:wave' 等
        if inline_formats:
            for fmt in inline_formats:
                if fmt.startswith("u:"):
                    u_elem = OxmlElement("w:u")
                    u_elem.set(qn("w:val"), fmt.split(":", 1)[1])
                    rPr.append(u_elem)
                elif fmt == "b":
                    b_elem = OxmlElement("w:b")
                    rPr.append(b_elem)
                elif fmt == "i":
                    i_elem = OxmlElement("w:i")
                    rPr.append(i_elem)

        return rPr

    def _insert_translation_paragraph(self, unit: TextUnit, translated_text: str) -> None:
        """在原文段落后插入译文段落（双语模式）"""
        original_p = unit.paragraph_element

        # 创建新段落元素 <w:p>
        new_p = OxmlElement("w:p")

        # 1. 复制原文段落的段落格式 <w:pPr>
        pPr = original_p.find(qn("w:pPr"))
        if pPr is not None:
            new_pPr = deepcopy(pPr)
            # 【移除自动编号，避免译文段落继续编号】
            numPr = new_pPr.find(qn("w:numPr"))
            if numPr is not None:
                new_pPr.remove(numPr)
            # 【VML 绘图段落行高豁免】ANVISA 等系统导出的文档，VML 段落 pPr 带超大
            # exact 行高（如 line=8040≈14cm，对应绘图区域高度）。复制给译文段落会
            # 产生整页空行，故恢复正常行高（仅对 >18pt 的绘图级行高生效）。
            spacing = new_pPr.find(qn("w:spacing"))
            if spacing is not None:
                line = spacing.get(qn("w:line"))
                rule = spacing.get(qn("w:lineRule"))
                if rule == "exact" and line and int(line) > 360:
                    spacing.attrib.pop(qn("w:line"), None)
                    spacing.attrib.pop(qn("w:lineRule"), None)
            new_p.append(new_pPr)

        # 2. 构建 run 格式模板
        rPr_template = self._build_run_properties(original_p, translated_text, unit.inline_formats)

        # 3. 按 \n 拆分译文，在 \n 处插入 w:br，保留原文排版
        parts = translated_text.split("\n")
        for i, part in enumerate(parts):
            if i > 0:
                br_run = OxmlElement("w:r")
                br = OxmlElement("w:br")
                br_run.append(br)
                new_p.append(br_run)
            if part or (i == len(parts) - 1 and translated_text.endswith("\n")):
                r = OxmlElement("w:r")
                r.append(deepcopy(rPr_template))
                t = OxmlElement("w:t")
                if part and (part[0].isspace() or part[-1].isspace()):
                    t.set(qn("xml:space"), "preserve")
                t.text = part
                r.append(t)
                new_p.append(r)

        # 4. 插入到原文段落后（同父节点下）
        original_p.addnext(new_p)

        # 5. 自动调整表格行高：固定行高改为最小行高，允许内容撑开
        self._adjust_table_row_height(new_p)

    def _insert_multi_sub(self, group: list, processed_paragraphs: set) -> None:
        """处理多子段段落：移除原文，交替插入子原文+子译文
        group: [(unit, result), ...] 同 paragraph_element 的多个子段
        """
        if not group:
            return

        # 按 sub_index 排序
        group.sort(key=lambda x: x[0].sub_index)

        first_unit = group[0][0]
        original_p = first_unit.paragraph_element
        parent = original_p.getparent()

        # 找到原文段落的前一个兄弟作为插入锚点
        prev_sibling = original_p.getprevious()

        # 移除原文段落（所有子段用完后移除）
        parent.remove(original_p)

        # 交替插入子原文 + 子译文
        insert_after = prev_sibling  # 插入位置：在此元素之后
        for unit, result in group:
            # 1) 创建子原文段落
            sub_orig = deepcopy(original_p)
            # 清空子原文的内容，只保留一段文本
            for child in list(sub_orig):
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag in ("r", "hyperlink", "ins", "sdt"):
                    sub_orig.remove(child)

            # 创建文本 run
            rPr_template = self._build_run_properties(original_p, unit.text, unit.inline_formats)
            r = OxmlElement("w:r")
            r.append(deepcopy(rPr_template))
            t = OxmlElement("w:t")
            t.text = unit.text
            r.append(t)
            sub_orig.append(r)

            # 插入子原文
            if insert_after is not None:
                insert_after.addnext(sub_orig)
            else:
                parent.insert(0, sub_orig)

            # 2) 创建子译文段落
            new_p = OxmlElement("w:p")
            pPr = original_p.find(qn("w:pPr"))
            if pPr is not None:
                new_pPr = deepcopy(pPr)
                numPr = new_pPr.find(qn("w:numPr"))
                if numPr is not None:
                    new_pPr.remove(numPr)
                new_p.append(new_pPr)

            rPr_trans = self._build_run_properties(original_p, result.translated_text, unit.inline_formats)
            r_trans = OxmlElement("w:r")
            r_trans.append(deepcopy(rPr_trans))
            t_trans = OxmlElement("w:t")
            t_trans.text = result.translated_text
            r_trans.append(t_trans)
            new_p.append(r_trans)

            # 插入子译文（在子原文之后）
            sub_orig.addnext(new_p)

            # 更新锚点：下次在译文之后插入
            insert_after = new_p

            # 标记已处理
            processed_paragraphs.add(id(unit.paragraph_element))

            self._adjust_table_row_height(sub_orig)
            self._adjust_table_row_height(new_p)

    def _adjust_table_row_height(self, para_element) -> None:
        """沿段落向上找到父表格行，将固定行高改为可自动扩展"""
        elem = para_element.getparent()
        while elem is not None:
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "tr":
                trPr = elem.find(qn("w:trPr"))
                if trPr is not None:
                    trHeight = trPr.find(qn("w:trHeight"))
                    if trHeight is not None:
                        hRule = trHeight.get(qn("w:hRule"))
                        if hRule == "exact":
                            trHeight.set(qn("w:hRule"), "atLeast")
                        elif hRule is None:
                            trPr.remove(trHeight)
                break
            elem = elem.getparent()

    def _replace_paragraph_text(self, unit: TextUnit, translated_text: str) -> None:
        """将原文段落内容替换为译文（单语替换模式）
        保留段落格式、书签、批注标记等非文本元素，只替换 w:r 中的文本
        【新增】保留原文的下划线、加粗、斜体等内联格式
        """
        original_p = unit.paragraph_element

        # 1. 保存段落格式 <w:pPr>
        pPr = original_p.find(qn("w:pPr"))

        # 2. 找到第一个有文本的 run，保存其 run 格式 <w:rPr>
        # 搜索直接子 w:r 和超链接内的 w:r
        first_r = None
        saved_rPr = None

        def _find_first_text_run(parent_elem):
            """递归查找第一个有文本的 w:r 元素"""
            for r in parent_elem.findall(qn("w:r")):
                t = r.find(qn("w:t"))
                if t is not None and t.text and t.text.strip():
                    return r
            # 搜索超链接内的 run
            for hl in parent_elem.findall(qn("w:hyperlink")):
                result = _find_first_text_run(hl)
                if result is not None:
                    return result
            return None

        first_r = _find_first_text_run(original_p)
        if first_r is not None:
            rPr = first_r.find(qn("w:rPr"))
            if rPr is not None:
                saved_rPr = deepcopy(rPr)

        # 2.5 保存字号（删除 w:r 后 _get_original_font_properties 找不到 run）
        saved_sz = None
        saved_szCs = None
        if saved_rPr is not None:
            sz_elem = saved_rPr.find(qn("w:sz"))
            if sz_elem is not None:
                saved_sz = sz_elem.get(qn("w:val"))
            szCs_elem = saved_rPr.find(qn("w:szCs"))
            if szCs_elem is not None:
                saved_szCs = szCs_elem.get(qn("w:val"))

        # 3. 【只删除 w:r 元素，保留其他所有元素（书签、批注标记等）】
        # 对超链接 w:hyperlink：清空内部文本但保留结构，避免丢失超链接格式
        for child in list(original_p):
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "r":
                original_p.remove(child)
            elif tag == "hyperlink":
                # 清空超链接内的文本，保留超链接结构
                for hr in child.findall(qn("w:r")):
                    t = hr.find(qn("w:t"))
                    if t is not None:
                        t.text = ""
                # 不删除超链接，保留其结构
            elif tag == "pPr":
                # pPr 单独处理，确保它在最前面
                original_p.remove(child)
            # else: 保留书签、批注标记等非文本元素

        # 4. 重新添加段落格式（作为第一个子元素）
        if pPr is not None:
            if len(original_p) > 0:
                original_p.insert(0, pPr)
            else:
                original_p.append(pPr)

        # 5. 构建 run 格式：原文格式 + 覆盖字体和颜色 + 内联格式
        rPr = self._build_run_properties(original_p, translated_text, unit.inline_formats)

        # 5.5 补回字号（删除 w:r 后 _build_run_properties 可能取不到）
        if saved_sz is not None and rPr.find(qn("w:sz")) is None:
            sz = OxmlElement("w:sz")
            sz.set(qn("w:val"), saved_sz)
            rPr.append(sz)
        if saved_szCs is not None and rPr.find(qn("w:szCs")) is None:
            szCs = OxmlElement("w:szCs")
            szCs.set(qn("w:val"), saved_szCs)
            rPr.append(szCs)

        # 如果有原文保存的 rPr，合并进去（保留原文特有的格式如加粗、斜体等）
        if saved_rPr is not None:
            for child in saved_rPr:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                # 跳过颜色、字体大小、字体族（这些已由 _build_run_properties 设置）
                if tag in ("color", "sz", "szCs", "rFonts", "lang"):
                    continue
                # 如果 _build_run_properties 已经添加了 u/b/i，避免重复
                # inline_formats 格式如 'b', 'i', 'u:single', 'u:double'
                fmt_names = {f.split(":", 1)[0] for f in (unit.inline_formats or [])}
                if tag in ("u", "b", "i") and tag in fmt_names:
                    continue
                rPr.append(deepcopy(child))

        # 6. 按 \n 拆分译文，在 \n 处插入 w:br，保留原文排版
        parts = translated_text.split("\n")
        for i, part in enumerate(parts):
            if i > 0:
                br_run = OxmlElement("w:r")
                br = OxmlElement("w:br")
                br_run.append(br)
                original_p.append(br_run)
            if part or (i == len(parts) - 1 and translated_text.endswith("\n")):
                r = OxmlElement("w:r")
                r.append(deepcopy(rPr))
                t = OxmlElement("w:t")
                if part and (part[0].isspace() or part[-1].isspace()):
                    t.set(qn("xml:space"), "preserve")
                t.text = part
                r.append(t)
                original_p.append(r)
