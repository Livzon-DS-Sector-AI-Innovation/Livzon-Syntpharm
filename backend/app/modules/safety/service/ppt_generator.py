"""PPT Generator Service — AI 大纲生成 + python-pptx 渲染 + MinIO 上传。

流程：
1. 根据 template 类型选择对应 prompt，调用 AI 生成 JSON 大纲
2. 用 python-pptx 渲染 .pptx 文件（根据 style 应用配色主题）
3. 上传到 MinIO
4. 写入 ppt_generation_records 表
5. 返回 { download_url, file_name, page_count, message }
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from io import BytesIO
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import llm_client
from app.core.llm.exceptions import LLMConfigError
from app.core.storage import is_enabled as minio_enabled
from app.core.storage import upload_object
from app.modules.safety.models import SafetyKnowledgeArticle
from app.modules.safety.repository import SafetyRepository

logger = logging.getLogger(__name__)


# ==================== 配色主题 ====================

THEMES: dict[str, dict[str, Any]] = {
    "professional": {
        "bg_color": RGBColor(  # type: ignore[no-untyped-call]
            0xFF, 0xFF, 0xFF
        ),  # 白色背景
        "title_color": RGBColor(  # type: ignore[no-untyped-call]
            0x1A, 0x56, 0xDB
        ),  # 蓝色标题
        "text_color": RGBColor(  # type: ignore[no-untyped-call]
            0x33, 0x33, 0x33
        ),  # 深灰正文
        "accent_color": RGBColor(  # type: ignore[no-untyped-call]
            0x1A, 0x56, 0xDB
        ),  # 蓝色强调
        "subtitle_color": RGBColor(  # type: ignore[no-untyped-call]
            0x66, 0x66, 0x66
        ),  # 中灰副标题
        "title_font": "Microsoft YaHei",
        "body_font": "Microsoft YaHei",
        "title_size": Pt(28),
        "body_size": Pt(16),
        "subtitle_size": Pt(18),
    },
    "modern": {
        "bg_color": RGBColor(  # type: ignore[no-untyped-call]
            0x1E, 0x1E, 0x2E
        ),  # 深色背景
        "title_color": RGBColor(  # type: ignore[no-untyped-call]
            0xFF, 0xFF, 0xFF
        ),  # 白色标题
        "text_color": RGBColor(  # type: ignore[no-untyped-call]
            0xCC, 0xCC, 0xCC
        ),  # 浅灰正文
        "accent_color": RGBColor(  # type: ignore[no-untyped-call]
            0x00, 0xD4, 0xAA
        ),  # 青绿强调
        "subtitle_color": RGBColor(  # type: ignore[no-untyped-call]
            0x99, 0x99, 0x99
        ),  # 灰色副标题
        "title_font": "Microsoft YaHei",
        "body_font": "Microsoft YaHei",
        "title_size": Pt(28),
        "body_size": Pt(16),
        "subtitle_size": Pt(18),
    },
    "minimal": {
        "bg_color": RGBColor(  # type: ignore[no-untyped-call]
            0xFF, 0xFF, 0xFF
        ),  # 白色背景
        "title_color": RGBColor(  # type: ignore[no-untyped-call]
            0x00, 0x00, 0x00
        ),  # 黑色标题
        "text_color": RGBColor(  # type: ignore[no-untyped-call]
            0x44, 0x44, 0x44
        ),  # 灰色正文
        "accent_color": RGBColor(  # type: ignore[no-untyped-call]
            0x66, 0x66, 0x66
        ),  # 灰色强调
        "subtitle_color": RGBColor(  # type: ignore[no-untyped-call]
            0x88, 0x88, 0x88
        ),  # 浅灰副标题
        "title_font": "Microsoft YaHei",
        "body_font": "Microsoft YaHei",
        "title_size": Pt(28),
        "body_size": Pt(16),
        "subtitle_size": Pt(18),
    },
}


# ==================== Prompt 模板 ====================

PROMPTS: dict[str, str] = {
    "training": """你是一位资深安全培训讲师。请将以下法规文档转化为安全培训课件 PPT 大纲。

要求：
1. 第1张幻灯片为封面页（type: "title"），包含标题和副标题"安全培训专用课件"
2. 第2张为培训目标与大纲目录（type: "content"）
3. 中间幻灯片：每个核心知识点独立一页，配合实际案例或场景说明（type: "content"）
4. 适当穿插"思考题"或"讨论环节"页面
5. 倒数第2张为重点回顾与总结（type: "summary"）
6. 最后1张为 Q&A / 谢谢（type: "summary"）

总共 10-20 张幻灯片。语言简洁，适合投影讲解。

请以 JSON 格式返回：
{{
  "title": "PPT 总标题",
  "slides": [
    {{
      "title": "幻灯片标题",
      "content": "幻灯片内容（要点用换行分隔）",
      "type": "title 或 content 或 summary"
    }}
  ]
}}""",
    "briefing": """你是一位安全管理顾问。请将以下法规文档转化为管理层安全简报 PPT 大纲。

要求：
1. 第1张为封面页（type: "title"），包含标题和日期
2. 第2张为核心摘要（type: "content"），列出 3-5 个要点
3. 中间幻灯片：每页一个关键议题，突出数据/趋势/影响（type: "content"）
4. 倒数第2张为行动建议（type: "summary"），列出 2-3 条建议
5. 最后1张为结语（type: "summary"）

总共 5-8 张幻灯片。精炼扼要，适合 15 分钟汇报。

请以 JSON 格式返回：
{{
  "title": "PPT 总标题",
  "slides": [
    {{
      "title": "幻灯片标题",
      "content": "幻灯片内容（要点用换行分隔）",
      "type": "title 或 content 或 summary"
    }}
  ]
}}""",
    "audit": """你是一位安全审核专家。请将以下法规文档转化为审核检查清单 PPT 大纲。

要求：
1. 第1张为封面页（type: "title"），包含标题和"审核检查清单"副标题
2. 第2张为审核范围与依据（type: "content"）
3. 中间幻灯片：按检查类别分组，每页列出具体检查项（编号+要求+判定标准）（type: "content"）
4. 倒数第2张为常见问题与扣分项汇总（type: "summary"）
5. 最后1张为整改建议与跟踪要求（type: "summary"）

总共 8-15 张幻灯片。条目化呈现，方便逐项对照。

请以 JSON 格式返回：
{{
  "title": "PPT 总标题",
  "slides": [
    {{
      "title": "幻灯片标题",
      "content": "幻灯片内容（检查项用换行分隔）",
      "type": "title 或 content 或 summary"
    }}
  ]
}}""",
}


# ==================== 模板类型中文名 ====================

TEMPLATE_LABELS: dict[str, str] = {
    "training": "安全培训课件",
    "briefing": "安全简报",
    "audit": "审核检查清单",
}


class PptGeneratorService:
    """PPT 生成服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SafetyRepository(session)

    async def generate(
        self,
        article_id: uuid.UUID,
        template: str = "training",
        style: str = "professional",
    ) -> dict[str, Any]:
        """
        生成 PPT 并返回下载信息。

        Args:
            article_id: 知识库文章 ID
            template: 模板类型 (training/briefing/audit)
            style: 配色风格 (professional/modern/minimal)

        Returns:
            { download_url, file_name, page_count, message }
        """
        # 1. 查询文章
        article = await self.repo.get_knowledge_article_by_id(article_id)
        if not article:
            raise ValueError("文章不存在")
        if not article.content:
            raise ValueError("文章内容为空，无法生成 PPT")

        # 2. 调用 AI 生成大纲（通过全局 llm_client 单例）
        try:
            outline = await self._generate_outline(article, template)
        except LLMConfigError:
            # 降级方案：生成基础 2 页 PPT
            outline = self._fallback_outline(article)
            logger.warning("AI 服务未配置，使用降级 PPT 大纲")

        # 4. 更新文章的 ppt_content 缓存
        await self.repo.update_knowledge_article(
            article_id,
            {
                "ppt_content": outline,
                "ppt_generated_at": datetime.now(),
            },
        )
        await self.session.flush()

        # 5. 渲染 PPTX
        theme = THEMES.get(style, THEMES["professional"])
        pptx_bytes, page_count = self._render_pptx(outline, theme)

        # 6. 上传到 MinIO
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        template_label = TEMPLATE_LABELS.get(template, template)
        file_name = f"{template_label}_{timestamp}.pptx"
        object_key = f"ppt/{article_id}/{timestamp}_{template}.pptx"

        if minio_enabled():
            upload_object(
                "safety",
                object_key,
                pptx_bytes,
                len(pptx_bytes),
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )
        else:
            # MinIO 未启用时，object_key 仍作为标识返回
            logger.warning("MinIO 未启用，PPT 文件无法持久化存储")

        # 7. 写入生成记录（通过 repository）
        await self.repo.create_ppt_generation_record(
            {
                "article_id": article_id,
                "file_name": file_name,
                "template": template,
                "style": style,
                "page_count": page_count,
                "object_key": object_key,
                "status": "success",
            }
        )

        return {
            "download_url": object_key,
            "file_name": file_name,
            "page_count": page_count,
            "message": "PPT 生成成功",
        }

    async def _generate_outline(
        self,
        article: SafetyKnowledgeArticle,
        template: str,
    ) -> dict[str, Any]:
        """调用 AI 生成 PPT 大纲（使用全局 llm_client 单例）"""
        prompt_template = PROMPTS.get(template, PROMPTS["training"])
        prompt = f"""{prompt_template}

文档标题：{article.title}
文档分类：{article.category}

文档内容：
{article.content[:3000] if article.content else ""}"""

        response = await llm_client.chat_json(
            messages=[{"role": "user", "content": prompt}],
            expected_keys=["title", "slides"],
        )
        return response

    def _fallback_outline(self, article: SafetyKnowledgeArticle) -> dict[str, Any]:
        """降级方案：无 AI 时按章节自动生成多页 PPT"""
        slides = []

        # 第 1 页：封面
        slides.append(
            {
                "title": article.title,
                "content": "安全知识库文档",
                "type": "title",
            }
        )

        if not article.content:
            slides.append(
                {
                    "title": "文档概述",
                    "content": "暂无内容",
                    "type": "content",
                }
            )
            return {"title": article.title, "slides": slides}

        # 按章节拆分（匹配"第 X 章"或"第 X 条"）
        content = article.content

        # 尝试按"第 X 章"拆分
        chapter_pattern = r"(第 [一二三四五六七八九十百]+章\s+[^\n]+)"
        chapter_matches = list(re.finditer(chapter_pattern, content))

        if len(chapter_matches) >= 2:
            # 有明确的章节结构
            for i, match in enumerate(chapter_matches):
                chapter_title = match.group(1).strip()
                start = match.start()
                end = chapter_matches[i + 1].start() if i + 1 < len(chapter_matches) else len(content)
                chapter_content = content[start:end].strip()

                # 限制每章内容长度（300 字符）
                if len(chapter_content) > 300:
                    # 按条拆分
                    articles = re.split(r"(第 [一二三四五六七八九十百]+\d*条)", chapter_content)
                    current_slide_content = ""
                    current_article_title = chapter_title

                    for j, part in enumerate(articles):
                        if re.match(r"第 [一二三四五六七八九十百]+\d*条", part):
                            if current_slide_content:
                                slides.append(
                                    {
                                        "title": current_article_title,
                                        "content": current_slide_content.strip(),
                                        "type": "content",
                                    }
                                )
                            current_article_title = f"{chapter_title} - {part.strip()[:30]}"
                            current_slide_content = ""
                        else:
                            current_slide_content += part
                            if len(current_slide_content) > 250:
                                slides.append(
                                    {
                                        "title": current_article_title,
                                        "content": current_slide_content.strip()[:280] + "...",
                                        "type": "content",
                                    }
                                )
                                current_slide_content = ""

                    if current_slide_content:
                        slides.append(
                            {
                                "title": current_article_title,
                                "content": current_slide_content.strip()[:280],
                                "type": "content",
                            }
                        )
                else:
                    slides.append(
                        {
                            "title": chapter_title,
                            "content": chapter_content[:280],
                            "type": "content",
                        }
                    )
        else:
            # 没有明确章节，按段落拆分
            paragraphs = content.split("\n\n")
            current_content = ""
            page_num = 1

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                if len(current_content) + len(para) > 280 and current_content:
                    slides.append(
                        {
                            "title": f"文档内容 ({page_num})",
                            "content": current_content.strip(),
                            "type": "content",
                        }
                    )
                    current_content = para
                    page_num += 1
                else:
                    current_content += "\n" + para if current_content else para

            if current_content:
                slides.append(
                    {
                        "title": f"文档内容 ({page_num})" if page_num > 1 else "文档概述",
                        "content": current_content.strip()[:280],
                        "type": "content",
                    }
                )

        # 最后一页：总结
        slides.append(
            {
                "title": "总结",
                "content": "本文档共 {} 章，涵盖了相关法规的核心内容。".format(
                    len(chapter_matches) if chapter_matches else "多"
                ),
                "type": "summary",
            }
        )

        return {"title": article.title, "slides": slides}

    def _render_pptx(
        self,
        outline: dict[str, Any],
        theme: dict[str, Any],
    ) -> tuple[bytes, int]:
        """
        用 python-pptx 渲染 PPTX。

        Returns:
            (pptx_bytes, page_count)
        """
        prs = Presentation()
        # 设置 16:9 宽屏
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        slides = outline.get("slides", [])
        if not slides:
            slides = [{"title": outline.get("title", "PPT"), "content": "", "type": "content"}]

        # 每页最大字符数（超过则自动分页）
        max_content_chars = 300

        for slide_data in slides:
            slide_type = slide_data.get("type", "content")
            title_text = slide_data.get("title", "")
            content_text = slide_data.get("content", "")

            if slide_type == "title":
                self._add_title_slide(prs, title_text, content_text, theme)
            else:
                # 如果内容超过限制，自动拆分成多页
                if len(content_text) > max_content_chars and slide_type != "summary":
                    # 按行拆分
                    lines = content_text.split("\n")
                    current_page_lines: list[str] = []
                    current_length = 0
                    page_num = 1

                    for line in lines:
                        line_length = len(line)
                        if current_length + line_length > max_content_chars and current_page_lines:
                            total_pages = (len(content_text) + max_content_chars - 1) // max_content_chars
                            page_title = f"{title_text} ({page_num}/{total_pages})" if page_num > 1 else title_text
                            page_content = "\n".join(current_page_lines)
                            total_pages = (len(content_text) + max_content_chars - 1) // max_content_chars
                            page_title = f"{title_text} ({page_num}/{total_pages})" if page_num > 1 else title_text
                            self._add_content_slide(prs, page_title, page_content, theme, is_summary=False)
                            current_page_lines = [line]
                            current_length = line_length
                            page_num += 1
                        else:
                            current_page_lines.append(line)
                            current_length += line_length

                        self._add_content_slide(
                            prs, page_title, page_content, theme, is_summary=(slide_type == "summary")
                        )
                    if current_page_lines:
                        page_content = "\n".join(current_page_lines)
                        total_pages = (len(content_text) + max_content_chars - 1) // max_content_chars
                        page_title = f"{title_text} ({page_num}/{total_pages})" if page_num > 1 else title_text
                        self._add_content_slide(
                            prs, page_title, page_content, theme, is_summary=(slide_type == "summary")
                        )
                else:
                    self._add_content_slide(prs, title_text, content_text, theme, is_summary=(slide_type == "summary"))

        # 导出为 bytes
        buffer = BytesIO()
        prs.save(buffer)
        pptx_bytes = buffer.getvalue()
        return pptx_bytes, len(slides)

    def _add_title_slide(
        self,
        prs: Any,
        title_text: str,
        subtitle_text: str,
        theme: dict[str, Any],
    ) -> None:
        """添加封面页"""
        slide_layout = prs.slide_layouts[6]  # 空白布局
        slide = prs.slides.add_slide(slide_layout)

        # 设置背景色
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = theme["bg_color"]

        # 标题
        left = Inches(1)
        top = Inches(2.5)
        width = Inches(11.333)
        height = Inches(1.5)
        textbox = slide.shapes.add_textbox(left, top, width, height)
        tf = textbox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = theme["title_color"]
        p.font.name = theme["title_font"]
        p.alignment = PP_ALIGN.CENTER

        # 副标题
        if subtitle_text:
            top2 = Inches(4.2)
            height2 = Inches(1)
            textbox2 = slide.shapes.add_textbox(left, top2, width, height2)
            tf2 = textbox2.text_frame
            tf2.word_wrap = True
            p2 = tf2.paragraphs[0]
            p2.text = subtitle_text
            p2.font.size = theme["subtitle_size"]
            p2.font.color.rgb = theme["subtitle_color"]
            p2.font.name = theme["body_font"]
            p2.alignment = PP_ALIGN.CENTER

    def _add_content_slide(
        self,
        prs: Any,
        title_text: str,
        content_text: str,
        theme: dict[str, Any],
        is_summary: bool = False,
    ) -> None:
        """添加内容页或总结页"""
        slide_layout = prs.slide_layouts[6]  # 空白布局
        slide = prs.slides.add_slide(slide_layout)

        # 设置背景色
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = theme["bg_color"]

        # 顶部装饰条
        bar_left = Inches(0)
        bar_top = Inches(0)
        bar_width = prs.slide_width
        bar_height = Inches(0.08)
        shape = slide.shapes.add_shape(
            1,  # MSO_SHAPE.RECTANGLE
            bar_left,
            bar_top,
            bar_width,
            bar_height,
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = theme["accent_color"]
        shape.line.fill.background()

        # 标题
        left = Inches(0.8)
        top = Inches(0.4)
        width = Inches(11.733)
        height = Inches(1)
        textbox = slide.shapes.add_textbox(left, top, width, height)
        tf = textbox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = theme["title_size"]
        p.font.bold = True
        p.font.color.rgb = theme["title_color"]
        p.font.name = theme["title_font"]

        # 内容
        if content_text:
            content_top = Inches(1.6)
            content_height = Inches(5.5)
            textbox2 = slide.shapes.add_textbox(left, content_top, width, content_height)
            tf2 = textbox2.text_frame
            tf2.word_wrap = True

            # 按换行分段
            lines = content_text.split("\n")
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                if i == 0:
                    p2 = tf2.paragraphs[0]
                else:
                    p2 = tf2.add_paragraph()
                p2.text = line
                p2.font.size = theme["body_size"]
                p2.font.color.rgb = theme["text_color"]
                p2.font.name = theme["body_font"]
                p2.space_after = Pt(8)

                # 如果行首是数字+点 或 短横线，添加缩进表示列表项
                if line and (line[0].isdigit() or line[0] in "-•·"):
                    p2.level = 1
