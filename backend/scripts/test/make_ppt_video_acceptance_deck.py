"""生成「PPT 配音视频」验收样例 PPT。

覆盖四类待验收问题：
1. 左右两栏：右栏在 XML 里先插入、左栏后插入，用来验证 page_text 是否按阅读顺序（上→下、左→右）拼接；
2. 长表格：验证表格文字抽取顺序与覆盖率；
3. 多音字与单位：重楼、大黄、阿胶、枸橼、黄芩、川芎、μg、g/L、pH、GMP/HPLC；
4. 超长文字页（> 2000 字）：验证旧截断问题是否消失、覆盖率是否提示漏讲；
5. 纯图片页：正文只存在于图片里，用于确认「本页无文字」的既有边界。

用法：
    uv run python scripts/test/make_ppt_video_acceptance_deck.py
    uv run python scripts/test/make_ppt_video_acceptance_deck.py --out /tmp/acceptance.pptx
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path

from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

FONT = "Noto Sans CJK SC"
ACCENT = RGBColor(0x56, 0x45, 0xD4)
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x5D, 0x5B, 0x54)
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = REPO_ROOT / "backend" / "docs" / "samples" / "ppt-video-acceptance-deck.pptx"


def _textbox(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    text: str,
    *,
    size: int = 18,
    bold: bool = False,
    color: RGBColor = INK,
    align=PP_ALIGN.LEFT,
):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.word_wrap = True
    paragraphs = text.split("\n")
    for index, line in enumerate(paragraphs):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.alignment = align
        paragraph.space_after = Pt(6)
        run = paragraph.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = FONT
    return box


def _title(slide, text: str, subtitle: str | None = None) -> None:
    _textbox(slide, 0.6, 0.35, 12.1, 0.8, text, size=30, bold=True, color=INK)
    if subtitle:
        _textbox(slide, 0.6, 1.1, 12.1, 0.5, subtitle, size=14, color=MUTED)


def _bullets(slide, left: float, top: float, width: float, height: float, items: list[str], size: int = 17):
    text = "\n".join(f"• {item}" for item in items)
    return _textbox(slide, left, top, width, height, text, size=size)


def _build_image_page_png() -> io.BytesIO:
    """纯图片页：文字被画进图片，PPT 里没有任何文本框。"""
    width, height = 1600, 900
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([40, 40, width - 40, height - 40], outline=(86, 69, 212), width=6)
    draw.rectangle([120, 240, 520, 620], fill=(234, 231, 255), outline=(86, 69, 212), width=4)
    draw.rectangle([600, 240, 1000, 620], fill=(226, 244, 235), outline=(38, 140, 96), width=4)
    draw.rectangle([1080, 240, 1480, 620], fill=(255, 240, 230), outline=(214, 110, 40), width=4)
    try:
        from PIL import ImageFont

        font_big = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 56)
        font_small = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 40)
    except OSError:
        font_big = font_small = None
    draw.text((120, 90), "原料药车间平面示意图", fill=(26, 26, 26), font=font_big)
    draw.text((160, 380), "洁净区 C 级", fill=(26, 26, 26), font=font_small)
    draw.text((640, 380), "洁净区 D 级", fill=(26, 26, 26), font=font_small)
    draw.text((1120, 380), "包装区", fill=(26, 26, 26), font=font_small)
    draw.text((120, 700), "本页文字只存在于图片里，用于验证「无文字页」边界。", fill=(93, 91, 84), font=font_small)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def _long_page_text() -> str:
    """拼出 2500 字以上的长页，覆盖旧版 2000 字截断。"""
    sections = [
        (
            "一、研发背景",
            "本项目针对难溶性原料药的晶型稳定性问题开展系统研究。前期小试发现，原料在高温高湿条件下易发生晶型转变，"
            "导致溶出度下降并对后续制剂工艺造成波动。为解决该问题，项目组从溶剂体系、结晶温度、搅拌速率三个方面"
            "设计正交试验，并对每一组样品进行 X 射线粉末衍射、差示扫描量热与热重分析，确认晶型归属与热稳定性差异。",
        ),
        (
            "二、试验设计",
            "正交试验选取三个因素各三个水平，共安排九组试验，每组重复三次以评估批间差异。结晶温度设置低温、中温、"
            "高温三档；溶剂体系比较纯水、乙醇水溶液与丙酮水溶液；搅拌速率设置为慢速、中速与快速。所有试验均在相同"
            "的降温曲线与养晶时间下进行，避免操作差异掩盖因素效应。",
        ),
        (
            "三、关键指标",
            "以收率、纯度、晶型纯度、残留溶剂与粒径分布作为评价指标。收率按干燥品计算，纯度采用高效液相色谱法测定，"
            "残留溶剂按药典通则检测，粒径分布采用激光粒度仪测定并记录 D10、D50 与 D90。晶型纯度以特征衍射峰强度比"
            "进行半定量评价，必要时补充固体核磁确认。",
        ),
        (
            "四、结果分析",
            "九组试验结果显示，结晶温度对晶型纯度影响最显著，中温条件下目标晶型占比最高；溶剂体系对收率影响次之，"
            "乙醇水溶液体系收率稳定在 90% 以上；搅拌速率对粒径分布影响明显，中速搅拌得到的 D50 更集中。三因素之间"
            "未观察到显著的交互作用，说明工艺窗口相对稳健。",
        ),
        (
            "五、工艺确认",
            "在优选条件下进行三批放大验证，批量由实验室规模放大至中试规模。三批产品的收率分别为 92.4%、91.8% 与 "
            "93.1%，纯度均在 99.8% 以上，晶型纯度与实验室结果一致，残留溶剂全部低于限度要求。放大过程中未出现"
            "结块、粘壁等异常现象，过滤与干燥时间在可接受范围内。",
        ),
        (
            "六、稳定性考察",
            "对三批样品开展加速试验与长期试验。加速条件为温度 40 摄氏度、相对湿度 75%，考察 1 个月、2 个月、3 个月"
            "与 6 个月；长期条件为温度 25 摄氏度、相对湿度 60%，考察 3 个月、6 个月、9 个月与 12 个月。考察项目包括"
            "性状、鉴别、有关物质、含量、晶型与微生物限度，结果显示各项指标均在质量标准范围内。",
        ),
        (
            "七、风险与对策",
            "识别出的主要风险包括原料来源差异导致的晶种差异、干燥设备温度分布不均以及包装密封性不足。针对上述风险，"
            "分别制定供应商审计与入厂检验、设备温度分布验证与再验证、包装密封性试验与运输模拟试验等控制措施，并将"
            "关键参数纳入批记录与过程控制计划，确保工艺持续处于受控状态。",
        ),
        (
            "八、下一步计划",
            "下一阶段将完成工艺验证报告的定稿与注册申报资料的整理，同步推进杂质谱研究与分析方法验证。计划在第二季度"
            "完成三批工艺验证，第三季度提交注册申请，第四季度配合现场核查。项目组将按月跟踪里程碑完成情况，及时暴露"
            "偏差并制定纠正预防措施。",
        ),
        (
            "九、质量研究",
            "质量研究围绕有关物质、残留溶剂、元素杂质与基因毒性杂质四条主线展开。有关物质采用高效液相色谱法，"
            "以主成分自身对照法计算单个杂质与总杂；残留溶剂按药典通则采用顶空气相色谱法，覆盖一类、二类与三类溶剂；"
            "元素杂质按风险评估结果确定考察元素，采用电感耦合等离子体质谱法测定；基因毒性杂质按构效关系评估后，"
            "对需要控制的结构警示单元建立专属方法并完成方法学验证。",
        ),
        (
            "十、方法验证",
            "分析方法验证按专属性、精密度、准确度、线性与范围、检测限与定量限、溶液稳定性、耐用性七个项目开展。"
            "专属性考察空白溶剂、辅料与强制降解样品的干扰；精密度考察重复性与中间精密度；准确度采用加样回收，"
            "回收率控制在 98% 至 102%；线性相关系数不低于 0.999；耐用性考察不同色谱柱、不同流速与不同柱温的影响，"
            "确保方法在正常波动范围内结果一致。",
        ),
        (
            "十一、设备确认",
            "结晶釜、离心机、双锥干燥机与粉碎机均完成安装确认、运行确认与性能确认。安装确认核对材质证明、"
            "仪表校准证书与管线连接；运行确认验证温度控制精度、搅拌转速范围、真空保持能力与密封性；"
            "性能确认以空白物料与模拟物料运行，确认设备在设定参数下能稳定产出符合要求的产品，并据此确定"
            "设备的使用范围与清洁验证的取样点。",
        ),
        (
            "十二、EHS 与清洁",
            "工艺过程中使用的有机溶剂按危险化学品管理，设置密闭投料、局部排风与可燃气体报警；离心与干燥工序"
            "控制静电积累，设备接地电阻定期检测；废水按高浓度与低浓度分流，送污水处理站处理。清洁验证以活性成分"
            "残留、总有机碳与微生物限度为指标，按最差条件确定取样点与擦拭面积，连续三批结果合格后方可放行下一产品。",
        ),
        (
            "十三、供应链与入库检验",
            "原料药生产所需的关键起始物料实行双源管理，每批到货核对检验报告、批次号、有效期与包装完整性，"
            "并按入厂检验规程抽样检测性状、鉴别、含量、水分与有关物质。对供应商开展年度审计，审计内容包括"
            "生产现场、质量管理体系、变更控制与偏差处理；出现连续两批不合格或重大变更时启动专项审计，"
            "必要时暂停供货并启用备选供应商，确保生产不中断。",
        ),
        (
            "十四、文件与培训",
            "本项目的批记录、工艺规程、质量标准与验证报告按文件管理规程编号归档，电子数据按数据完整性要求"
            "设置权限、审计追踪与备份。项目启动前完成岗位培训与考核，培训内容包括工艺要点、设备操作、"
            "异常处理与安全注意事项；工艺变更后重新培训并更新文件版本，确保现场执行与文件描述一致，"
            "为后续现场核查提供完整证据链。",
        ),
        (
            "十五、里程碑与分工",
            "项目设项目经理一名，统筹进度、资源与对外沟通；工艺负责人负责试验设计、放大与技术转移；分析负责人"
            "负责方法开发与验证；质量负责人负责文件审核、偏差与变更管理。里程碑包括：第一季度完成工艺确认，"
            "第二季度完成三批工艺验证，第三季度提交注册申请，第四季度配合现场核查并完成缺陷答复。"
            "每月召开一次项目例会，输出进度报告与风险清单，重大偏差在二十四小时内上报。",
        ),
    ]
    return "\n".join(f"{title}\n{body}" for title, body in sections)


def build_deck(out_path: Path) -> Path:
    presentation = Presentation()
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)
    blank = presentation.slide_layouts[6]

    # 1. 封面
    slide = presentation.slides.add_slide(blank)
    _textbox(slide, 0.9, 1.9, 11.5, 1.2, "原料药研发季度汇报", size=44, bold=True, color=INK)
    _textbox(slide, 0.9, 3.2, 11.5, 0.7, "PPT 配音视频验收样例（2026 Q1）", size=24, color=ACCENT)
    _textbox(
        slide,
        0.9,
        4.4,
        11.5,
        1.6,
        "本样例用于验证：讲稿阅读顺序、要点覆盖率、段间停顿、多音字与单位读音。\n建议逐页试听后，再整片渲染对比。",
        size=16,
        color=MUTED,
    )

    # 2. 左右两栏：右栏先插入，验证阅读顺序
    slide = presentation.slides.add_slide(blank)
    _title(
        slide,
        "项目进展与关键指标",
        "左右两栏：右栏在文件里先插入，正确顺序应为「同一行左→右、整体上→下」",
    )
    _textbox(slide, 6.95, 2.0, 5.6, 0.6, "右栏：关键指标", size=22, bold=True, color=ACCENT)
    _bullets(
        slide,
        6.95,
        2.7,
        5.6,
        3.6,
        [
            "收率 92.4%，纯度 99.87%",
            "单批周期 18 天，较上季度缩短 3 天",
            "残留溶剂经 HPLC 检测全部合格",
            "粒径分布 D50 为 42 微米",
        ],
    )
    _textbox(slide, 0.75, 2.0, 5.6, 0.6, "左栏：项目进展", size=22, bold=True, color=ACCENT)
    _bullets(
        slide,
        0.75,
        2.7,
        5.6,
        3.6,
        [
            "2026 年第一季度完成 3 个原料药项目的申报资料准备",
            "其中 2 个项目已进入技术审评阶段",
            "GMP 现场核查预计 5 月启动",
            "同步推进杂质谱与分析方法验证",
        ],
    )

    # 3. 长表格
    slide = presentation.slides.add_slide(blank)
    _title(slide, "关键工序与控制标准", "长表格：验证表格文字抽取顺序与覆盖率")
    rows = [
        ("工序", "关键参数", "控制标准", "本批实测"),
        ("投料", "原料纯度", "≥ 99.5%", "99.87%"),
        ("溶解", "溶剂比例 乙醇/水", "g/L 配比 1:3", "1:3.1"),
        ("脱色", "活性炭用量", "2.0 g/L", "2.0 g/L"),
        ("结晶", "结晶温度", "15 ~ 20 摄氏度", "18 摄氏度"),
        ("离心", "离心转速", "1200 转/分", "1250 转/分"),
        ("干燥", "干燥温度与时间", "60 摄氏度 / 8 小时", "58 摄氏度 / 8 小时"),
        ("粉碎", "粒径 D90", "≤ 75 微米", "68 微米"),
        ("包装", "密封性", "无泄漏", "合格"),
    ]
    table_shape = slide.shapes.add_table(len(rows), 4, Inches(0.7), Inches(1.8), Inches(11.9), Inches(4.6))
    table = table_shape.table
    for column, width in enumerate((2.0, 3.6, 3.6, 2.7)):
        table.columns[column].width = Inches(width)
    for row_index, row in enumerate(rows):
        for column, value in enumerate(row):
            cell = table.cell(row_index, column)
            cell.text = value
            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(14)
                    run.font.name = FONT
                    run.font.bold = row_index == 0
                    run.font.color.rgb = INK
    _textbox(
        slide,
        0.7,
        6.55,
        11.9,
        0.5,
        "备注：μg/g 与 g/L 用于检查单位读音，表格顺序应与阅读顺序一致。",
        size=13,
        color=MUTED,
    )

    # 4. 多音字与单位
    slide = presentation.slides.add_slide(blank)
    _title(slide, "术语与读音检查", "本页用于检查多音字、英文缩写与单位的读音")
    _bullets(
        slide,
        0.8,
        1.9,
        6.0,
        4.6,
        [
            "重楼：指标成分含量不低于 0.60%",
            "大黄：游离蒽醌与结合蒽醌分别测定",
            "阿胶：驴皮来源，需检特征肽段",
            "枸橼：缓冲盐体系常用枸橼酸钠",
            "黄芩、川芎：提取工艺参数对比",
        ],
        size=18,
    )
    _bullets(
        slide,
        7.0,
        1.9,
        5.6,
        4.6,
        [
            "残留溶剂限度：μg/g 级",
            "浓度单位：g/L、mg/mL",
            "pH 7.2 的磷酸盐缓冲液",
            "GMP 与 HPLC 为英文缩写",
            "USP 通则与药典方法对照",
        ],
        size=18,
    )

    # 5. 纯图片页（无文本框）
    slide = presentation.slides.add_slide(blank)
    slide.shapes.add_picture(_build_image_page_png(), Inches(1.0), Inches(0.9), width=Inches(11.3))

    # 6. 超长文字页
    slide = presentation.slides.add_slide(blank)
    long_text = _long_page_text()
    _title(slide, "研究总结（长页，超过 2000 字）", f"本页正文 {len(long_text)} 字，用于验证送模长度与覆盖率")
    _textbox(slide, 0.7, 1.7, 12.0, 5.4, long_text, size=9)

    # 7. 备注页
    slide = presentation.slides.add_slide(blank)
    _title(slide, "下一步安排", "本页带演讲者备注，用于验证备注是否作为讲稿上下文")
    _bullets(
        slide,
        0.8,
        2.0,
        11.6,
        3.6,
        [
            "第二季度：完成三批工艺验证",
            "第三季度：提交注册申请",
            "第四季度：配合现场核查",
            "按月跟踪里程碑，偏差及时关闭",
        ],
        size=20,
    )
    notes = slide.notes_slide.notes_text_frame
    notes.text = "补充说明：工艺验证批号分别为 260301、260302、260303，验证报告由质量部归档。"

    # 8. 收尾
    slide = presentation.slides.add_slide(blank)
    _title(slide, "谢谢", "验收检查清单")
    _bullets(
        slide,
        0.9,
        2.2,
        11.5,
        3.8,
        [
            "第 2 页：讲稿顺序为同一行左→右、整体上→下（先两个栏标题，再分别讲两栏内容）",
            "第 3 页：表格内容按行依次讲到，单位读音正确",
            "第 4 页：重楼、大黄、阿胶、枸橼读音正确",
            "第 6 页：长页不被截断，覆盖率提示漏讲可一键补全",
        ],
        size=18,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    presentation.save(str(out_path))
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 PPT 配音视频验收样例")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="输出路径")
    args = parser.parse_args()
    target = build_deck(args.out)
    long_chars = len(_long_page_text())
    print(f"已生成：{target}")
    print(f"长页字数：{long_chars}（旧版送模上限 2000，现 4000）")
    print(f"页数：{len(Presentation(str(target)).slides)}")


if __name__ == "__main__":
    main()
