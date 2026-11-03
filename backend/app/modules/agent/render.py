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
from collections.abc import Sequence
from pathlib import Path

from app.modules.agent.config import CANVAS_HEIGHT, CANVAS_WIDTH, FRAME_RATE

logger = logging.getLogger(__name__)

FFMPEG_TIMEOUT = 900
FFPROBE_TIMEOUT = 60
AUDIO_SAMPLE_RATE = 48000
AUDIO_BITRATE = "128k"


class RenderError(RuntimeError):
    """渲染失败，message 直接给用户看。"""


def ensure_tools() -> None:
    """启动自检：缺工具立刻报清楚，而不是等到合成时报一堆 stderr。"""
    missing = [name for name in ("ffmpeg", "ffprobe", "soffice") if not shutil.which(name)]
    if missing:
        raise RenderError(
            "渲染环境缺少必要工具：" + "、".join(missing) + "。请使用 backend/Dockerfile.worker 构建的 worker 镜像。"
        )


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


def pdf_to_pngs(pdf_path: str | Path, out_dir: str | Path, dpi: int = 150) -> list[Path]:
    """pdf → 每页 png（按页码顺序）。"""
    from pdf2image import convert_from_path

    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        pages = convert_from_path(str(pdf_path), dpi=dpi, fmt="png")
    except Exception as exc:  # noqa: BLE001 - pdf2image 抛多种底层异常
        logger.exception("pdf_to_pngs failed")
        raise RenderError(f"PPT 转图片失败：{exc}") from exc

    paths: list[Path] = []
    for index, page in enumerate(pages, start=1):
        path = target_dir / f"slide-{index:03d}.png"
        page.save(path, "PNG", optimize=True)
        paths.append(path)
    if not paths:
        raise RenderError("PPT 未渲染出任何页面")
    return paths


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


def compose_highlight_frame(
    source_path: str | Path,
    out_path: str | Path,
    boxes: list[tuple[int, int, int, int]],
    slide_size: tuple[int, int] | None = None,
    dim_alpha: int = 150,
    accent: tuple[int, int, int] = (86, 69, 212),
    outline_px: int = 4,
) -> Path:
    """生成一段高亮静帧：整页压暗，命中区域还原亮度并描边。

    boxes 为 EMU 坐标，需配合 slide_size（页面 EMU 尺寸）换算成像素；
    slide_size 缺失或换算异常时退化为「不变暗」的原始画面，宁可不亮也不亮错。
    """
    from PIL import Image, ImageDraw  # 延迟导入：只有开启视觉引导时才需要 Pillow

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as handle:
        base = handle.convert("RGB")

    width_px, height_px = base.size
    usable: list[tuple[int, int, int, int]] = []
    if boxes and slide_size and slide_size[0] > 0 and slide_size[1] > 0:
        scale_x = width_px / slide_size[0]
        scale_y = height_px / slide_size[1]
        for left, top, box_width, box_height in boxes:
            x0 = max(0, min(width_px - 1, int(left * scale_x)))
            y0 = max(0, min(height_px - 1, int(top * scale_y)))
            x1 = max(x0 + 1, min(width_px, int((left + box_width) * scale_x)))
            y1 = max(y0 + 1, min(height_px, int((top + box_height) * scale_y)))
            if x1 - x0 >= 4 and y1 - y0 >= 4:
                usable.append((x0, y0, x1, y1))

    if not usable:
        base.save(target, "PNG", optimize=True)
        return target

    alpha = max(0, min(255, dim_alpha)) / 255.0
    result = Image.blend(base, Image.new("RGB", base.size, (0, 0, 0)), alpha) if alpha > 0 else base.copy()
    for box in usable:
        result.paste(base.crop(box), box[:2])
    if outline_px > 0:
        draw = ImageDraw.Draw(result)
        for box in usable:
            draw.rectangle([box[0], box[1], box[2] - 1, box[3] - 1], outline=accent, width=outline_px)

    result.save(target, "PNG", optimize=True)
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
