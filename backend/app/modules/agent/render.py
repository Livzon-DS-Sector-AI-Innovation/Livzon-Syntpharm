"""渲染原语：pptx → pdf → png → 每页 mp4 → concat 成片。

设计要点：
- 所有页片段使用**完全相同**的编码参数（1920×1080 / 30fps / yuv420p / AAC 48k），
  成片用 concat demuxer + `-c copy` 拼接，不二次编码，避免画质损失与音画漂移；
- 每段时长 = 前间隙 + 旁白实际时长 + 后间隙，画面由静帧循环补齐（朗读完才切页）；
- 画面等比缩放 + 白底留边，不裁切、不拉伸（TC-003）。

本模块只依赖 ffmpeg/ffprobe/soffice 可执行文件，不做任何 IO 到 MinIO。
"""

import logging
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.modules.agent.config import CANVAS_HEIGHT, CANVAS_WIDTH, FRAME_RATE

logger = logging.getLogger(__name__)

FFMPEG_TIMEOUT = 900
FFPROBE_TIMEOUT = 60
AUDIO_SAMPLE_RATE = 48000
AUDIO_BITRATE = "128k"

#: 渲染管线版本：**只要改了影响画面像素的东西（字体、soffice/poppler 参数、dpi）就必须加一**。
#: 它同时作用于两处，保证「预览页图」与「成片画面」不会一半新一半旧：
#: 1. 中间 PDF 的内容寻址 key（旧 PDF 自然不再命中，见 `page_images.source_pdf_key`）；
#: 2. 项目行的 `page_images_renderer`（不等即视为页图过期，下次投递自动重出）。
RENDERER_VERSION = "2"
#: 字体配置指纹：与 `backend/assets/fontconfig/69-ppt-font-alias.conf` + 镜像里的字体包
#: （Noto CJK / Liberation / Carlito / Caladea）一一对应，改任一处都要同步改这里。
#: v2：v1 时期镜像里其实没装 Liberation/Carlito（Dockerfile 改了但镜像没重建），
#: 旧页图是「按 DejaVu 排版」的，必须整批失效重出。
FONT_PROFILE = "noto-liberation-v2"
RENDERER_KEY = f"r{RENDERER_VERSION}-{FONT_PROFILE}"

#: 拉丁字体必须命中的度量兼容替代（左边是 PPT 里声明的族名，右边是 fontconfig 应给出的 family）。
#: 映射不上时会被判给更宽的 DejaVu：文本框提前折行、压住下一行/下一个形状，
#: 实测 Arial→DejaVu 时第 4 页 6 条要点挤成 5 行、第 32 页标题折行压框。
REQUIRED_LATIN_FONTS: dict[str, str] = {
    "Arial": "Liberation Sans",
    "Times New Roman": "Liberation Serif",
    "Calibri": "Carlito",
}
#: 中文族名必须命中带中文字形的字族，否则中文整屏方块或逐字回退导致中西文度量不一致
REQUIRED_CJK_FONTS: tuple[str, ...] = ("微软雅黑", "Microsoft YaHei", "宋体", "SimSun", "思源黑体 CN")
#: 判定「含中文字形」的 family 关键字（镜像里由 fonts-noto-cjk 提供）
CJK_FAMILY_MARKER = "noto"


class RenderError(RuntimeError):
    """渲染失败，message 直接给用户看。"""


def _fc_match_family(name: str) -> str:
    """查 fontconfig 实际会把 `name` 判给哪个字族；环境缺失时返回空串。"""
    if not shutil.which("fc-match"):
        return ""
    completed = subprocess.run(  # noqa: S603 - 命令由服务端常量拼装
        ["fc-match", "-f", "%{family}", name],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    # 一个字体文件可能列出多个 family（"Liberation Sans, Liberation Sans Narrow"），取第一个
    return completed.stdout.split(",")[0].strip()


def font_environment_problems(match: Callable[[str], str] | None = None) -> list[str]:
    """列出「字体环境会让页图排版跑偏」的问题；空列表表示可用。

    只做族名解析（fc-match），不读 PPT——同一镜像对所有项目的结果相同，
    目的是把「镜像少装字体」这类环境问题在出图前就暴露，而不是渲染出一批错图。
    """
    lookup = match or _fc_match_family
    problems: list[str] = []
    for declared, expected in REQUIRED_LATIN_FONTS.items():
        actual = lookup(declared)
        if actual != expected:
            problems.append(f"{declared} → {actual or '（无匹配）'}（期望 {expected}）")
    for declared in REQUIRED_CJK_FONTS:
        actual = lookup(declared)
        if CJK_FAMILY_MARKER not in actual.lower():
            problems.append(f"{declared} → {actual or '（无匹配）'}（期望 Noto CJK 等中文字体）")
    return problems


def verify_font_environment() -> None:
    """出图前校验字体：不合格就直接失败，避免生成一批错位页图。

    宁可不渲染，也不要让用户拿到「文字折行压字」的成片——错图比报错更难排查
    （错误文本会被人当成内容读出问题）。
    """
    problems = font_environment_problems()
    if problems:
        raise RenderError(
            "渲染环境字体不完整，页图会文字折行、互相压字："
            + "；".join(problems)
            + "。请用 backend/Dockerfile.worker（以及页面出图用的 backend/Dockerfile）重建镜像后重试。"
        )


def ensure_tools() -> None:
    """启动自检：缺工具立刻报清楚，而不是等到合成时报一堆 stderr。"""
    missing = [name for name in ("ffmpeg", "ffprobe", "soffice") if not shutil.which(name)]
    if missing:
        raise RenderError(
            "渲染环境缺少必要工具：" + "、".join(missing) + "。请使用 backend/Dockerfile.worker 构建的 worker 镜像。"
        )
    verify_font_environment()


def run_command(command: list[str], timeout: int, cwd: str | Path | None = None) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(  # noqa: S603 - 命令由服务端常量拼装
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=str(cwd) if cwd else None,
        )
    except subprocess.TimeoutExpired as exc:
        raise RenderError(f"渲染命令超时（{timeout}s）：{Path(command[0]).name}") from exc
    if completed.returncode != 0:
        logger.error("command failed: %s\nstderr: %s", " ".join(command), completed.stderr[-2000:])
        raise RenderError(f"渲染失败：{Path(command[0]).name} 返回码 {completed.returncode}")
    return completed


def pptx_to_pdf(pptx_path: str | Path, out_dir: str | Path, profile_dir: str | Path) -> Path:
    """pptx → pdf（LibreOffice headless，独立 profile 防并发锁）。"""
    binary = shutil.which("soffice") or shutil.which("libreoffice")
    if not binary:
        raise RenderError("服务器未安装 LibreOffice，无法把 PPT 转成图片")
    source = Path(pptx_path)
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    profile = Path(profile_dir)
    profile.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            binary,
            f"-env:UserInstallation=file://{profile.resolve()}",
            "--headless",
            "--norestore",
            "--convert-to",
            "pdf",
            "--outdir",
            str(target_dir),
            str(source),
        ],
        timeout=FFMPEG_TIMEOUT,
    )
    pdf_path = target_dir / f"{source.stem}.pdf"
    if not pdf_path.exists():
        raise RenderError("PPT 转 PDF 失败，请确认文件可正常打开")
    return pdf_path


def pdf_page_count(pdf_path: str | Path) -> int:
    """PDF 页数（走 poppler 的 pdfinfo，不把页面读进内存）。"""
    from pdf2image import pdfinfo_from_path

    try:
        info = pdfinfo_from_path(str(pdf_path))
    except Exception as exc:  # noqa: BLE001 - pdf2image 抛多种底层异常
        logger.exception("pdf_page_count failed")
        raise RenderError(f"无法读取 PDF 页数：{exc}") from exc
    try:
        return int(info["Pages"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RenderError("无法读取 PDF 页数") from exc


#: 逐页拆图回调：`(页码, 总页数)`，页码从 1 开始
PageCallback = Callable[[int, int], None]

#: 页图 PNG 压缩级别：无损，只影响压缩率与耗时。3 比 optimize=True（zlib 9）快数倍，
#: 体积大约多 10-20%，而这份 PNG 只在服务端内部（成片/预览/缩略图）流转。
PAGE_PNG_COMPRESS_LEVEL = 3
#: 中间高亮帧的 PNG 压缩级别：帧编码完就被 ffmpeg 读走并删除，用最低档换速度
FRAME_PNG_COMPRESS_LEVEL = 1


def render_pdf_page(pdf_path: str | Path, out_dir: str | Path, page: int, dpi: int = 150) -> Path:
    """渲染单页 PDF 为 PNG（页码从 1 开始）。

    页图任务逐页调用它可以按页上报进度；`render_pdf_pages` 也走这一份实现，
    保证「带进度」与「不带进度」两条路径渲染结果完全一致。
    """
    from pdf2image import convert_from_path

    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        pages = convert_from_path(str(pdf_path), dpi=dpi, fmt="png", first_page=page, last_page=page)
    except Exception as exc:  # noqa: BLE001 - pdf2image 抛多种底层异常
        logger.exception("render_pdf_page failed at page %s", page)
        raise RenderError(f"PPT 转图片失败（第 {page} 页）：{exc}") from exc
    if not pages:
        raise RenderError(f"PPT 第 {page} 页渲染为空")
    path = target_dir / f"slide-{page:03d}.png"
    pages[0].save(path, "PNG", compress_level=PAGE_PNG_COMPRESS_LEVEL)
    return path


def render_pdf_page_batch(
    pdf_path: str | Path,
    out_dir: str | Path,
    first_page: int,
    last_page: int,
    dpi: int = 150,
) -> list[Path]:
    """一次 pdftoppm 出 [first_page, last_page] 的区间页图。

    为什么成批而不是逐页：每页一次 `pdftoppm` 都要重新解析一遍 PDF 与启动进程，
    53 页就是 53 次固定开销；一次出整本又把上百 MB 位图同时留在内存里。
    取 8 页一批，进程数降到 1/8，峰值内存 = 批大小页数。
    """
    from pdf2image import convert_from_path

    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        pages = convert_from_path(str(pdf_path), dpi=dpi, fmt="png", first_page=first_page, last_page=last_page)
    except Exception as exc:  # noqa: BLE001 - pdf2image 抛多种底层异常
        logger.exception("render_pdf_page_batch failed: %s-%s", first_page, last_page)
        raise RenderError(f"PPT 转图片失败（第 {first_page}-{last_page} 页）：{exc}") from exc
    expected = last_page - first_page + 1
    if len(pages) != expected:
        raise RenderError(f"PPT 第 {first_page}-{last_page} 页渲染数量不符（{len(pages)}/{expected}）")

    paths: list[Path] = []
    for offset, page_image in enumerate(pages):
        path = target_dir / f"slide-{first_page + offset:03d}.png"
        page_image.save(path, "PNG", compress_level=PAGE_PNG_COMPRESS_LEVEL)
        page_image.close()
        paths.append(path)
    return paths


def render_pdf_pages(
    pdf_path: str | Path,
    out_dir: str | Path,
    dpi: int = 150,
    on_page: PageCallback | None = None,
) -> list[Path]:
    """pdf → 每页 png（按页码顺序），逐页渲染。

    为什么逐页：一次 `convert_from_path` 会把整本的 PIL image 全留在内存里
    （53 页 150dpi 约 300MB+），而且拆图期间没有任何进度可报。
    逐页调用 `pdftoppm -f n -l n` 后峰值内存只有单页，
    同时可以按页向上层回调进度。53 页多 53 次进程启动（合计几秒），
    相对于本就串行的 soffice + 拆图耗时可以忽略。
    """
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    total = pdf_page_count(pdf_path)
    if total <= 0:
        raise RenderError("PPT 未渲染出任何页面")

    paths: list[Path] = []
    for index in range(1, total + 1):
        paths.append(render_pdf_page(pdf_path, target_dir, index, dpi))
        if on_page is not None:
            on_page(index, total)
    return paths


def pdf_to_pngs(pdf_path: str | Path, out_dir: str | Path, dpi: int = 150) -> list[Path]:
    """pdf → 每页 png（兼容旧调用，等价于不带进度回调的 `render_pdf_pages`）。"""
    return render_pdf_pages(pdf_path, out_dir, dpi)


#: 预览大图（编辑器中间画面）最宽像素；成片仍用原始 PNG，避免改格式触发全量重算
PREVIEW_MAX_WIDTH = 1920
PREVIEW_JPEG_QUALITY = 88
#: 时间轴缩略图最宽像素；显示区 96px，留 3 倍余量给高分屏
THUMB_WIDTH = 320
THUMB_JPEG_QUALITY = 78


def encode_jpeg(source: str | Path, out_path: str | Path, max_width: int, quality: int) -> Path:
    """页图 PNG → 指定宽度的 JPEG（预览图 / 缩略图）。

    只等比缩小、不裁切：预览图与成片必须保持同一构图，
    否则用户在预览里看到的版式会和成片对不上。
    """
    from PIL import Image

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        frame = image.convert("RGB")
        if frame.width > max_width:
            height = max(1, round(frame.height * max_width / frame.width))
            frame = frame.resize((max_width, height), Image.Resampling.LANCZOS)
        # 关掉 optimize/progressive：两者都是纯 CPU 换体积，而这两张图只发给浏览器做预览，
        # 换来的几 KB 不值得每次出图多花一倍编码时间
        frame.save(target, "JPEG", quality=quality)
    return target


def build_slide_segment(
    image_path: str | Path,
    wav_path: str | Path,
    out_path: str | Path,
    audio_duration_ms: int,
    head_padding_ms: int,
    tail_padding_ms: int,
    threads: int = 2,
) -> int:
    """静帧 + 旁白 → 单页 mp4，返回片段时长(ms)。

    音频先 `adelay` 补前间隙，再 `apad` 补齐，最后 `-t` 精确截断，
    保证每段时长恒定、无爆音（20ms 淡入淡出）。
    """
    total_ms = head_padding_ms + audio_duration_ms + tail_padding_ms
    total_seconds = total_ms / 1000.0
    filters = (
        f"[0:v]scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={CANVAS_WIDTH}:{CANVAS_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=white,"
        f"setsar=1,fps={FRAME_RATE},format=yuv420p[v];"
        f"[1:a]adelay={head_padding_ms}|{head_padding_ms},apad,"
        f"afade=t=in:st=0:d=0.02,afade=t=out:st={max(total_seconds - 0.02, 0):.3f}:d=0.02[a]"
    )
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-i",
            str(wav_path),
            "-filter_complex",
            filters,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-tune",
            "stillimage",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FRAME_RATE),
            "-threads",
            str(threads),
            "-c:a",
            "aac",
            "-ar",
            str(AUDIO_SAMPLE_RATE),
            "-b:a",
            AUDIO_BITRATE,
            "-t",
            f"{total_seconds:.3f}",
            "-movflags",
            "+faststart",
            str(out_path),
        ],
        timeout=FFMPEG_TIMEOUT,
    )
    return total_ms


_TEXT_KIND_PREFIXES = ("", "TEXT", "PLACEHOLDER", "CELL")


def _is_text_kind(kind: str | None) -> bool:
    """只有文本类区域才做文字染色；图片/图表整块染色会糊成红色剪影。"""
    prefix = str(kind or "").split(" ", 1)[0].strip().upper()
    return prefix in _TEXT_KIND_PREFIXES or prefix.startswith("TEXT")


#: 文字遮罩：背景主峰至少要占这么多像素，否则认为区域不是「平底色 + 文字」
TEXT_MASK_BG_MIN_RATIO = 0.02
#: 前景峰（文字）最低占比；文字面积再小也是一个独立灰度峰，只它比背景峰矮得多
TEXT_MASK_FG_MIN_RATIO = 0.001
#: 前景峰与背景峰的最小灰度距离，低于它视为没有对比度
TEXT_MASK_MIN_CONTRAST = 24
#: 识别不出文字时的兜底铺底透明度（0-255）：保证「选了文字变色」一定有可见变化
TEXT_MASK_FALLBACK_ALPHA = 24


def _smooth_histogram(histogram: Sequence[int]) -> list[int]:
    """±1 三点平滑：抗锯齿会把同一个字摊到相邻灰度级上，不平滑容易漏峰。"""
    size = len(histogram)
    return [
        histogram[max(0, value - 1)] + histogram[value] + histogram[min(size - 1, value + 1)] for value in range(size)
    ]


def _text_mask(region: Any, strength: float) -> Any:
    """区域内「文字像素」的软遮罩。

    用直方图峰检测找「背景主峰 + 文字次峰」，而不是按分位数取明暗极值：
    前者在文字面积占比不到 5%（标题框拉满整行、一行只有几个字）时依然能定位文字，
    后者会让 5% 分位落在背景上，直接判成「没有对比度」——这正是
    「选了文字变色、部分页却一点没变」的成因。

    纯色块 / 照片 / 渐变没有清晰的第二峰，返回 None，由 `compose_highlight_frame`
    退化为淡底（保证有可见变化，又不把整块染成主色剪影）。
    """
    gray = region.convert("L")
    histogram = _smooth_histogram(gray.histogram())
    total = sum(histogram)
    if total <= 0:
        return None

    background = max(range(256), key=lambda value: histogram[value])
    if histogram[background] < total * TEXT_MASK_BG_MIN_RATIO:
        # 没有任何一个灰度占绝对多数：照片、渐变、噪点底，不做文字染色
        return None

    foreground = -1
    for value in range(256):
        if abs(value - background) < TEXT_MASK_MIN_CONTRAST:
            continue
        if histogram[value] < total * TEXT_MASK_FG_MIN_RATIO:
            continue
        if foreground < 0 or histogram[value] > histogram[foreground]:
            foreground = value
    if foreground < 0:
        return None

    threshold = (background + foreground) / 2.0
    band = max(6.0, abs(foreground - background) / 4.0)
    # 极性直接由两个峰的位置决定：文字比底色暗就取暗侧，反之取亮侧
    dark_is_foreground = foreground < background
    table: list[int] = []
    for value in range(256):
        ratio = (threshold - value) / band if dark_is_foreground else (value - threshold) / band
        ratio = 0.0 if ratio <= 0 else (1.0 if ratio >= 1 else ratio)
        table.append(int(255 * ratio * strength))
    return gray.point(table)


@dataclass(frozen=True)
class RegionPaint:
    """一个区域实际怎么画：只染字，或铺一层底色，颜色与强度各自可调。

    区域三态（`HighlightBox.mode`）在 worker 里归一到它，渲染循环因此不再判断
    「是不是文本」——那是解析阶段的决定，这里只认画法。
    """

    accent: tuple[int, int, int] = (86, 69, 212)
    #: 只给文字染色（背景不动）
    text: bool = False
    #: 铺底色的透明度（0-255）；`area` 档用它
    fill_alpha: int = 0
    #: 文字染色强度（0-100）；`text` 档用它
    recolor_strength: int = 0


def compose_highlight_frame(
    source_path: str | Path,
    out_path: str | Path,
    boxes: list[tuple[int, int, int, int]],
    slide_size: tuple[int, int] | None = None,
    dim_alpha: int = 150,
    accent: tuple[int, int, int] = (86, 69, 212),
    outline_px: int = 4,
    *,
    kinds: Sequence[str] | None = None,
    fill_alpha: int = 0,
    recolor_strength: int = 0,
    paints: Sequence[RegionPaint] | None = None,
    base_image: Any | None = None,
) -> Path:
    """生成一段高亮静帧：整页压暗，命中区域还原亮度并描边。

    boxes 为 EMU 坐标，需配合 slide_size（页面 EMU 尺寸）换算成像素；
    slide_size 缺失或换算异常时退化为「不变暗」的原始画面，宁可不亮也不亮错。

    `paints` 与 boxes 一一对应时按框取画法（区域级配置走它）；
    不传则退回老口径：`recolor_strength > 0` 的文本区域做**文字染色**，
    其余只贴回原图并叠淡色底，避免整块变红剪影。
    """
    from PIL import Image, ImageDraw  # 延迟导入：只有开启视觉引导时才需要 Pillow

    def _legacy_paint(kind: str) -> RegionPaint:
        if recolor_strength > 0 and _is_text_kind(kind):
            return RegionPaint(accent, text=True, fill_alpha=0, recolor_strength=recolor_strength)
        return RegionPaint(accent, text=False, fill_alpha=fill_alpha, recolor_strength=0)

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if base_image is not None:
        # 同一页要出多帧：调用方解一次、传进来，省掉每帧一次 PNG 解码
        base = base_image
    else:
        with Image.open(source_path) as handle:
            base = handle.convert("RGB")

    width_px, height_px = base.size
    regions: list[tuple[tuple[int, int, int, int], RegionPaint]] = []
    if boxes and slide_size and slide_size[0] > 0 and slide_size[1] > 0:
        scale_x = width_px / slide_size[0]
        scale_y = height_px / slide_size[1]
        for index, (left, top, box_width, box_height) in enumerate(boxes):
            x0 = max(0, min(width_px - 1, int(left * scale_x)))
            y0 = max(0, min(height_px - 1, int(top * scale_y)))
            x1 = max(x0 + 1, min(width_px, int((left + box_width) * scale_x)))
            y1 = max(y0 + 1, min(height_px, int((top + box_height) * scale_y)))
            if x1 - x0 >= 4 and y1 - y0 >= 4:
                kind = kinds[index] if kinds is not None and index < len(kinds) else ""
                paint = paints[index] if paints is not None and index < len(paints) else _legacy_paint(kind)
                regions.append(((x0, y0, x1, y1), paint))

    if not regions:
        base.save(target, "PNG", compress_level=FRAME_PNG_COMPRESS_LEVEL)
        return target

    alpha = max(0, min(255, dim_alpha)) / 255.0
    result = Image.blend(base, Image.new("RGB", base.size, (0, 0, 0)), alpha) if alpha > 0 else base.copy()
    for box, paint in regions:
        region = base.crop(box)
        painted = region
        strength = max(0, min(100, paint.recolor_strength)) / 100.0
        if paint.text and strength > 0:
            mask = _text_mask(region, strength)
            if mask is not None:
                painted = Image.composite(Image.new("RGB", region.size, paint.accent), region, mask)
            else:
                # 认不出文字也不能原样贴回：那样用户选了「文字变色」却看到画面没动。
                # 退化为低强度铺底，既留出可见反馈，又不至于染成整块剪影。
                fallback = max(paint.fill_alpha, TEXT_MASK_FALLBACK_ALPHA) / 255.0
                painted = Image.blend(region, Image.new("RGB", region.size, paint.accent), min(1.0, fallback))
        else:
            fill = max(0, min(255, paint.fill_alpha)) / 255.0
            if fill > 0:
                # 区域变色：整块铺一层主色底（文字仍可读），不做文字遮罩
                painted = Image.blend(region, Image.new("RGB", region.size, paint.accent), fill)
        result.paste(painted, box[:2])
    if outline_px > 0:
        draw = ImageDraw.Draw(result)
        for box, paint in regions:
            draw.rectangle([box[0], box[1], box[2] - 1, box[3] - 1], outline=paint.accent, width=outline_px)

    result.save(target, "PNG", compress_level=FRAME_PNG_COMPRESS_LEVEL)
    return target


def build_highlighted_segment(
    frames: Sequence[tuple[str | Path, int]],
    wav_path: str | Path,
    out_path: str | Path,
    audio_duration_ms: int,
    head_padding_ms: int,
    tail_padding_ms: int,
    list_file: str | Path,
    threads: int = 2,
) -> int:
    """多段静帧 + 一段旁白 → 单页 mp4，返回片段时长(ms)。

    与 `build_slide_segment` 使用完全相同的编码参数与时长口径，
    因此上层 `concat_segments -c copy` 链路不需要任何改动。
    audio_duration_ms 之内的时长由 frames 自带的 duration 覆盖，
    首帧额外延长 head_padding_ms、末帧延长 tail_padding_ms。
    """
    total_ms = head_padding_ms + audio_duration_ms + tail_padding_ms
    total_seconds = total_ms / 1000.0

    planned = [(Path(path), max(0, int(duration))) for path, duration in frames if duration > 0]
    if not planned:
        raise RenderError("视觉引导没有可用的画面分段")

    list_path = Path(list_file)
    list_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for index, (path, duration_ms) in enumerate(planned):
        extra = head_padding_ms if index == 0 else 0
        lines.append(f"file '{path.resolve().as_posix()}'\n")
        lines.append(f"duration {(duration_ms + extra) / 1000.0:.3f}\n")
    last_path = planned[-1][0].resolve().as_posix()
    lines.append(f"file '{last_path}'\n")
    if tail_padding_ms > 0:
        lines.append(f"duration {tail_padding_ms / 1000.0:.3f}\n")
        lines.append(f"file '{last_path}'\n")
    list_path.write_text("".join(lines), encoding="utf-8")

    filters = (
        f"[0:v]scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={CANVAS_WIDTH}:{CANVAS_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=white,"
        f"setsar=1,fps={FRAME_RATE},format=yuv420p[v];"
        f"[1:a]adelay={head_padding_ms}|{head_padding_ms},apad,"
        f"afade=t=in:st=0:d=0.02,afade=t=out:st={max(total_seconds - 0.02, 0):.3f}:d=0.02[a]"
    )
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-i",
            str(wav_path),
            "-filter_complex",
            filters,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-tune",
            "stillimage",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FRAME_RATE),
            "-threads",
            str(threads),
            "-c:a",
            "aac",
            "-ar",
            str(AUDIO_SAMPLE_RATE),
            "-b:a",
            AUDIO_BITRATE,
            "-t",
            f"{total_seconds:.3f}",
            "-movflags",
            "+faststart",
            str(out_path),
        ],
        timeout=FFMPEG_TIMEOUT,
    )
    return total_ms


def concat_segments(segment_paths: list[str | Path], out_path: str | Path, list_file: str | Path) -> Path:
    """按顺序拼接页片段，`-c copy` 不重编码。"""
    if not segment_paths:
        raise RenderError("没有可拼接的页片段")
    list_path = Path(list_file)
    list_path.write_text(
        "".join(f"file '{Path(path).resolve().as_posix()}'\n" for path in segment_paths),
        encoding="utf-8",
    )
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(target),
        ],
        timeout=FFMPEG_TIMEOUT,
    )
    if not target.exists() or target.stat().st_size == 0:
        raise RenderError("视频拼接失败：输出文件为空")
    return target


def probe_duration_ms(path: str | Path) -> int:
    """ffprobe 取媒体时长(ms)。"""
    completed = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        timeout=FFPROBE_TIMEOUT,
    )
    try:
        return int(float(completed.stdout.strip()) * 1000)
    except ValueError as exc:
        raise RenderError("无法读取视频时长") from exc
