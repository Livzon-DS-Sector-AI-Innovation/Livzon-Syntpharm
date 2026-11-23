"""
DOCX 翻译器 - 文档提取器
负责解析 DOCX，提取所有待翻译的段落文本，跳过不需要翻译的元素
"""

import re
from typing import Any

from docx import Document
from docx.oxml.ns import qn

from .doc_converter import DocConverter
from .engine_models import TextUnit


class DocxExtractor:
    """DOCX 文档提取器（支持 .doc 自动转换为 .docx）"""

    def __init__(self) -> None:
        self._id_counter = 0
        self._converter = DocConverter()
        self._converted_temp_path: str | None = None

    def _next_id(self) -> str:
        self._id_counter += 1
        return f"u{self._id_counter:05d}"

    def extract(self, docx_path: str) -> tuple[Any, list[TextUnit]]:
        """提取文档中所有待翻译的段落，返回 (doc, units)
        如果输入是 .doc，会自动转换为临时 .docx 再提取
        """
        # 如果是 .doc，先转换为 .docx
        if docx_path.lower().endswith((".doc", ".wps")):
            docx_path = self._converter.convert(docx_path)
            self._converted_temp_path = docx_path

        try:
            doc = Document(docx_path)
        except Exception as first_error:
            # fallback: 文件可能是伪 docx（如 WPS 保存的 .doc 格式），用 LibreOffice 转换
            if not self._converter.is_available():
                raise RuntimeError(
                    f"无法打开 '{docx_path}'（可能不是有效的 .docx），且 LibreOffice 未安装\n原始错误: {first_error}"
                )
            try:
                converted = self._converter.convert(docx_path)
                self._converted_temp_path = converted
                doc = Document(converted)
            except Exception as convert_error:
                raise RuntimeError(
                    f"无法打开 '{docx_path}'，LibreOffice 转换也未成功\n"
                    f"原始错误: {first_error}\n"
                    f"转换错误: {convert_error}"
                )
        units = []

        # 1. 提取正文段落
        units.extend(self._extract_body_paragraphs(doc))

        # 2. 提取表格段落（递归，包括嵌套表格）
        for table_idx, table in enumerate(doc.tables):
            units.extend(self._extract_table(table, f"table[{table_idx}]"))

        # 3. 【跳过页眉页脚】不再提取页眉页脚段落
        # units.extend(self._extract_headers_footers(doc))

        return doc, units

    def _extract_body_paragraphs(self, doc: Document) -> list[TextUnit]:
        """提取正文段落"""
        # 预检：相邻段落对——前中文后英文 → 两个都跳过
        all_paras = list(doc.paragraphs)
        skip_idx = set()
        for i in range(len(all_paras) - 1):
            if i in skip_idx:  # 防止已配对的段落参与级联二次配对（EN→CN假阳性）
                continue
            t1 = self._get_para_text(all_paras[i]).strip()
            t2 = self._get_para_text(all_paras[i + 1]).strip()
            # 剥离 URL 后再计算中英文比例，避免 URL 干扰（如"中检院官网https://..."被误判为英文主导）
            t1 = re.sub(r"https?://\S+", "", t1).strip()
            t2 = re.sub(r"https?://\S+", "", t2).strip()
            if len(t1) < 2 or len(t2) < 2:
                continue
            c1 = re.sub(r"\s", "", t1)
            c2 = re.sub(r"\s", "", t2)
            tot1, tot2 = len(c1) or 1, len(c2) or 1
            cn1 = len(re.findall(r"[\u4e00-\u9fff]", c1))
            en1 = len(re.findall(r"[a-zA-Z]", c1))
            cn2 = len(re.findall(r"[\u4e00-\u9fff]", c2))
            en2 = len(re.findall(r"[a-zA-Z]", c2))
            if cn1 / tot1 > 0.1 and en1 / tot1 < 0.5 and en2 / tot2 > 0.5 and cn2 / tot2 < 0.1:
                skip_idx.add(i)
                skip_idx.add(i + 1)
            elif en1 / tot1 > 0.5 and cn1 / tot1 < 0.1 and cn2 / tot2 > 0.1 and en2 / tot2 < 0.5:
                skip_idx.add(i)
                skip_idx.add(i + 1)

        units = []
        for idx, para in enumerate(all_paras):
            if idx in skip_idx:
                continue
            if self._should_skip_paragraph(para, is_table=False):
                continue
            text = self._get_para_text(para).strip()
            inline_formats = self._extract_inline_formats(para)
            # 按 w:br 拆分为多个子段，每个子段独立作为 TextUnit
            sub_texts = text.split("\n") if "\n" in text else [text]
            for sub_idx, sub_text in enumerate(sub_texts):
                sub_text = sub_text.strip()
                if not sub_text:
                    continue
                unit = TextUnit(
                    id=self._next_id(),
                    text=sub_text,
                    location_type="body",
                    section_index=-1,
                    table_path="",
                    paragraph_element=para._element,
                    parent_element=para._element.getparent(),
                    paragraph_index=idx,
                    inline_formats=inline_formats,
                    sub_index=sub_idx,
                    sub_count=len(sub_texts),
                )
                units.append(unit)
        return units

    def _extract_table(
        self, table, path_prefix: str, is_nested: bool = False, _visited_para_ids: set = None
    ) -> list[TextUnit]:
        """递归提取表格（包括嵌套表格）中的段落

        Args:
            _visited_para_ids: 内部递归用，记录已访问的 (w:p 元素, cell_path) 对，
                              避免同一个段落在同一单元格内被重复提取，
                              但允许同一 w:p 在不同 cell_path 中被提取（合法共享单元格）。
        """
        units = []
        visited_para_ids = _visited_para_ids if _visited_para_ids is not None else set()

        for row_idx, row in enumerate(table.rows):
            # 当前行已访问的 tc，用于跳过 gridSpan 横向合并导致的幻影单元格。
            visited_tc_ids = set()

            for cell_idx, cell in enumerate(row.cells):
                cell_path = f"{path_prefix}.row[{row_idx}].cell[{cell_idx}]"

                # 【跳过合并单元格的后续单元格】（规范格式的纵向/横向合并）
                if self._is_merged_cell_continuation(cell):
                    continue

                # 【跳过 gridSpan 导致的幻影单元格】
                tc_elem = cell._tc
                if tc_elem in visited_tc_ids:
                    continue
                visited_tc_ids.add(tc_elem)

                # 提取单元格内的所有段落（递归，包括 sdt 容器内的）
                paragraphs = self._get_cell_paragraphs(cell)
                # 预检：同一单元格内相邻中英对照段落 → 跳过
                skip_para_idx = self._skip_bilingual_cell_pairs(paragraphs)
                for para_idx, para in enumerate(paragraphs):
                    if para_idx in skip_para_idx:
                        continue
                    # 【去重：按 (w:p 元素, cell_path) 对去重】
                    # 同一 w:p 在同一 cell_path 内只提取一次
                    # 但同一 w:p 在不同 cell_path 中允许提取（合法共享单元格）
                    para_elem = para._element
                    para_key = (id(para_elem), cell_path)
                    if para_key in visited_para_ids:
                        continue
                    visited_para_ids.add(para_key)

                    if self._should_skip_paragraph(para, is_table=True):
                        continue
                    text = self._get_para_text(para).strip()
                    location = "nested_table_cell" if is_nested else "table_cell"
                    inline_formats = self._extract_inline_formats(para)
                    # 按 w:br 拆分为多个子段
                    sub_texts = text.split("\n") if "\n" in text else [text]
                    for sub_idx, sub_text in enumerate(sub_texts):
                        sub_text = sub_text.strip()
                        if not sub_text:
                            continue
                        unit = TextUnit(
                            id=self._next_id(),
                            text=sub_text,
                            location_type=location,
                            section_index=-1,
                            table_path=cell_path,
                            paragraph_element=para._element,
                            parent_element=para._element.getparent(),
                            paragraph_index=para_idx,
                            inline_formats=inline_formats,
                            sub_index=sub_idx,
                            sub_count=len(sub_texts),
                        )
                        units.append(unit)

                # 递归提取嵌套表格（共享 visited_para_ids）
                for nested_idx, nested_table in enumerate(cell.tables):
                    nested_path = f"{cell_path}.nested_table[{nested_idx}]"
                    units.extend(
                        self._extract_table(
                            nested_table, nested_path, is_nested=True, _visited_para_ids=visited_para_ids
                        )
                    )
        return units

    def _skip_bilingual_cell_pairs(self, paragraphs: list) -> set:
        """检测同一单元格内相邻段落的中英对照对，返回应跳过的段落下标集合"""
        skip_idx = set()
        for i in range(len(paragraphs) - 1):
            if i in skip_idx:  # 防止已配对的段落参与级联二次配对
                continue
            t1 = self._get_para_text(paragraphs[i]).strip()
            t2 = self._get_para_text(paragraphs[i + 1]).strip()
            # 剥离 URL 后再计算中英文比例
            t1 = re.sub(r"https?://\S+", "", t1).strip()
            t2 = re.sub(r"https?://\S+", "", t2).strip()
            if len(t1) < 2 or len(t2) < 2:
                continue
            c1 = re.sub(r"\s", "", t1)
            c2 = re.sub(r"\s", "", t2)
            tot1, tot2 = len(c1) or 1, len(c2) or 1
            cn1 = len(re.findall(r"[\u4e00-\u9fff]", c1))
            en1 = len(re.findall(r"[a-zA-Z]", c1))
            cn2 = len(re.findall(r"[\u4e00-\u9fff]", c2))
            en2 = len(re.findall(r"[a-zA-Z]", c2))
            if cn1 / tot1 > 0.1 and en1 / tot1 < 0.5 and en2 / tot2 > 0.5 and cn2 / tot2 < 0.1:
                skip_idx.add(i)
                skip_idx.add(i + 1)
            elif en1 / tot1 > 0.5 and cn1 / tot1 < 0.1 and cn2 / tot2 > 0.1 and en2 / tot2 < 0.5:
                skip_idx.add(i)
                skip_idx.add(i + 1)
        return skip_idx

    def _get_cell_paragraphs(self, cell) -> list:
        """递归获取单元格内的所有段落（包括嵌套在 sdt/sdtContent 等容器内的）"""
        paragraphs = []

        def _find_paragraphs_recursive(elem):
            if elem.tag == qn("w:p"):
                from docx.text.paragraph import Paragraph

                paragraphs.append(Paragraph(elem, cell))
                return
            # 不递归进入嵌套表格，避免与 cell.tables 递归重复
            if elem.tag == qn("w:tbl"):
                return
            for child in elem:
                _find_paragraphs_recursive(child)

        _find_paragraphs_recursive(cell._tc)
        return paragraphs

    def _is_merged_cell_continuation(self, cell) -> bool:
        """检测单元格是否是合并单元格的后续部分（非首个），应跳过"""
        tc = cell._tc
        tcPr = tc.find(qn("w:tcPr"))
        if tcPr is None:
            return False

        # 检测纵向合并（vMerge）
        vMerge = tcPr.find(qn("w:vMerge"))
        if vMerge is not None:
            val = vMerge.get(qn("w:val"))
            # vMerge 无 val 属性 或 val != "restart" → 是合并的后续单元格，跳过
            if val != "restart":
                return True

        # 检测横向合并（hMerge）——旧格式
        hMerge = tcPr.find(qn("w:hMerge"))
        if hMerge is not None:
            val = hMerge.get(qn("w:val"))
            if val != "restart":
                return True

        # 注：gridSpan 导致的重复 tc 引用由 _extract_table 中的 visited_tcs 处理
        return False

    def _extract_headers_footers(self, doc: Document) -> list[TextUnit]:
        """提取页眉页脚段落（当前不再调用，保留方法以备后续可选使用）"""
        units = []
        for sec_idx, section in enumerate(doc.sections):
            # 页眉
            for header in [section.header, section.first_page_header, section.even_page_header]:
                if header is None:
                    continue
                for para_idx, para in enumerate(header.paragraphs):
                    if self._should_skip_paragraph(para, is_table=False):
                        continue
                    text = para.text.strip()
                    unit = TextUnit(
                        id=self._next_id(),
                        text=text,
                        location_type="header",
                        section_index=sec_idx,
                        table_path="",
                        paragraph_element=para._element,
                        parent_element=para._element.getparent(),
                        paragraph_index=para_idx,
                    )
                    units.append(unit)

            # 页脚
            for footer in [section.footer, section.first_page_footer, section.even_page_footer]:
                if footer is None:
                    continue
                for para_idx, para in enumerate(footer.paragraphs):
                    if self._should_skip_paragraph(para, is_table=False):
                        continue
                    text = para.text.strip()
                    unit = TextUnit(
                        id=self._next_id(),
                        text=text,
                        location_type="footer",
                        section_index=sec_idx,
                        table_path="",
                        paragraph_element=para._element,
                        parent_element=para._element.getparent(),
                        paragraph_index=para_idx,
                    )
                    units.append(unit)
        return units

    def _should_skip_paragraph(self, para, is_table: bool = False) -> bool:
        """判断段落是否应该跳过（不翻译）
        is_table: 该段落是否来自表格单元格（表格中超短内容也跳过）
        """
        # 1. 空段落跳过（使用 _get_para_text 以覆盖 w:ins 等修订标记内的文本）
        text = self._get_para_text(para).strip()
        if not text:
            return True

        # 2. 检查段落在文本框/形状内（通过检查祖先元素）
        elem = para._element
        while elem is not None:
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            # 检测文本框、形状、图片、绘图、嵌入对象
            # 注意：sdt/sdtContent（内容控件）内的文本通常也需要翻译，故不跳过
            if tag in ("txbxContent", "textbox", "shape", "pic", "drawing", "object", "embeddedObject", "control"):
                # 【VML 布局文本框豁免】ANVISA 等系统导出文档把正文/法规内容画在
                # w:pict→v:group→v:shape→v:textbox→w:txbxContent 里（VML 旧式绘图，
                # 是文档布局的一部分而非注释框）。此类文本框内容必须翻译，不跳过。
                in_vml_pict = False
                e2 = elem
                while e2 is not None:
                    t2 = e2.tag.split("}")[-1] if "}" in e2.tag else e2.tag
                    if t2 == "pict":
                        in_vml_pict = True
                        break
                    e2 = e2.getparent()
                if in_vml_pict:
                    break  # VML 布局文本框 → 不跳过，继续翻译
                # anchor/inline 是 DrawingML 包装容器，内部可能包含 txbxContent 文本框
                # 不应直接跳过，由 txbxContent 检测决定是否跳过
                return True
            elem = elem.getparent()

        # 3. 【全局】正文中的纯数字/符号段落（如标题编号、版本号）不强制跳过，
        # 由翻译策略决定（LLM 提示词要求"如果某段只有数字、符号或空白，保持原样"）。
        # 此处的全局数字/符号跳过已移除，仅保留在表格判断中。

        # 4. 表格单元格的跳过策略（更保守，避免漏翻译缩写）
        # - 如果单元格只包含数字和标点/符号，跳过（表格数据值）
        # - 如果是单个中文字符（常为标记），跳过
        # - 其它情况保留（包括短英文缩写如 API、GMP、No. 等）以便术语表或翻译策略处理
        if is_table:
            # 保护特殊符号：选择框、勾选框等视为有效内容
            has_special_symbols = bool(re.search(r"[☐☑✓✗◊◇◆▪▫●○✔✘□]", text))
            # 纯数字/符号（无字母或中文）视为表格数据，跳过
            # 但如果有特殊符号则不跳过
            if not has_special_symbols and not re.search(r"[a-zA-Z\u4e00-\u9fff]", text):
                return True

        # 5. 分段双语检测：按 \n 或 / 拆段，存在中文主导段+英文主导段 → 跳过
        # 英文段要求 ≥5 字母，避免误杀缩写（如 RABS/磨粉分装机控制系统）
        segments = [s.strip() for s in re.split(r"[\n/]", text) if s.strip()]
        if len(segments) >= 2:

            def _cn_ratio(s):
                clean = re.sub(r"\s", "", s)
                total = len(clean) or 1
                return len(re.findall(r"[\u4e00-\u9fff]", clean)) / total

            def _en_ratio(s):
                clean = re.sub(r"\s", "", s)
                total = len(clean) or 1
                return len(re.findall(r"[a-zA-Z]", clean)) / total

            cn_heavy = any(_cn_ratio(s) > 0.7 for s in segments)
            en_heavy = any(_en_ratio(s) > 0.7 and len(re.sub(r"\s", "", s)) >= 5 for s in segments)
            if cn_heavy and en_heavy:
                return True

        return False

    def _extract_inline_formats(self, para) -> list:
        """检测段落中所有有文本 run 的共有内联格式（交集）
        返回格式值列表（如 ['b', 'i', 'u:double']）
        【修正】取所有 run 的交集，避免部分加粗导致全文加粗，
        也避免只取第一个 run 导致主文格式被个别字符格式覆盖
        """

        def _get_run_formats(r_elem) -> set:
            """提取单个 run 的内联格式（含 val 属性）"""
            fmts = set()
            rPr = r_elem.find(qn("w:rPr"))
            if rPr is None:
                return fmts
            u_elem = rPr.find(qn("w:u"))
            if u_elem is not None:
                u_val = u_elem.get(qn("w:val"))
                if u_val not in ("none", "0", "false"):
                    fmts.add(f"u:{u_val}" if u_val else "u:single")
            b_elem = rPr.find(qn("w:b"))
            if b_elem is not None:
                b_val = b_elem.get(qn("w:val"))
                if b_val not in ("0", "false", "none"):
                    fmts.add("b")
            i_elem = rPr.find(qn("w:i"))
            if i_elem is not None:
                i_val = i_elem.get(qn("w:val"))
                if i_val not in ("0", "false", "none"):
                    fmts.add("i")
            return fmts

        common_formats = None
        for r in para._element.findall(qn("w:r")):
            t = r.find(qn("w:t"))
            if t is None or not t.text or not t.text.strip():
                continue
            current = _get_run_formats(r)
            if common_formats is None:
                common_formats = current
            else:
                common_formats &= current
            if not common_formats:
                break  # 交集为空，无需继续

        if common_formats is None:
            return []
        return sorted(list(common_formats))

    def _get_para_text(self, para) -> str:
        """提取段落文本，保留 w:br（换行）和 w:tab（制表符）
        【修正】para.text 完全忽略 w:br，导致原文多行文本变成一行
        【修正】递归处理 w:ins/w:sdt/w:smartTag/w:customXml 容器，避免漏文本
        """

        def _extract_runs_text(elem) -> str:
            """从元素中递归提取所有 w:r 的文本（含 w:br/w:tab）"""
            parts = []
            for child in elem:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "r":
                    for sub in child:
                        sub_tag = sub.tag.split("}")[-1] if "}" in sub.tag else sub.tag
                        if sub_tag == "t" and sub.text:
                            parts.append(sub.text)
                        elif sub_tag == "br":
                            parts.append("\n")
                        elif sub_tag == "tab":
                            parts.append("\t")
                        elif sub_tag == "pict":
                            # VML 绘图对象内的文本框文字（ANVISA 等导出文档的正文可能在此）
                            parts.append(_extract_runs_text(sub))
                elif tag == "hyperlink":
                    for hr in child.findall(qn("w:r")):
                        for sub in hr:
                            sub_tag = sub.tag.split("}")[-1] if "}" in sub.tag else sub.tag
                            if sub_tag == "t" and sub.text:
                                parts.append(sub.text)
                            elif sub_tag == "br":
                                parts.append("\n")
                            elif sub_tag == "tab":
                                parts.append("\t")
                elif tag in (
                    "ins",
                    "sdt",
                    "sdtContent",
                    "smartTag",
                    "customXml",
                    "p",
                    "pict",
                    "group",
                    "shape",
                    "textbox",
                    "txbxContent",
                ):
                    # 递归处理容器元素（修订插入、结构化标签、sdt 内容、嵌套段落、智能标记、
                    # 自定义XML、VML 绘图对象 pict→group→shape→textbox→txbxContent）
                    # ANVISA 等系统导出的文档把正文/法规内容画在 VML 文本框里，必须提取
                    parts.append(_extract_runs_text(child))
            return "".join(parts)

        return _extract_runs_text(para._element)

    def get_statistics(self, units: list[TextUnit]) -> dict:
        """获取提取统计信息"""
        stats = {
            "total_units": len(units),
            "body": 0,
            "table_cell": 0,
            "nested_table_cell": 0,
            "header": 0,
            "footer": 0,
            "empty_skipped": 0,
        }
        for u in units:
            if u.location_type in stats:
                stats[u.location_type] += 1
        return stats

    def get_converted_temp_path(self) -> str | None:
        """获取转换后的临时文件路径（供清理用）"""
        return self._converted_temp_path

    def cleanup_converted(self) -> None:
        """清理临时转换文件"""
        if self._converted_temp_path:
            self._converter.cleanup(self._converted_temp_path)
            self._converted_temp_path = None
