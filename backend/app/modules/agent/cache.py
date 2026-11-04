"""内容寻址缓存键与复用清单（manifest）。

复用的唯一真相在 key：
    页图 sha256 ─┐
                 ├─→ segment_key ─→ 页片段 mp4（可跨项目复用）
脚本 sha256 ─→ audio_key ─(语音)
                    ↑
        voice_key（语言+音色+语速+引擎版本）

片头/正文分离：
    head_key = 第 1 页 segment_key
    body_key = 第 2～N 页 segment_key 的有序哈希（片头不参与）
因此「只改首页」时 head_key 变、body_key 不变 —— TC-006 的取证依据。

本模块只做纯计算，不碰数据库与网络，便于单测。
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.modules.agent.config import ENCODER_KEY

#: manifest 结构版本：字段增删时递增，旧版本 manifest 仍可读（只读不解析）
MANIFEST_VERSION = 1

_HASH_CHUNK = 1024 * 1024


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    """分块计算文件 sha256（MP4 可达数百 MB，不能整读进内存）。"""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(_HASH_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_script(text: str) -> str:
    """规范化讲稿，保证「视觉上相同」的讲稿得到同一个 key。

    - 行尾空白与全角空格统一
    - 连续空行折叠为一行（不改变语义）
    - 整体去首尾空白
    """
    lines = [line.replace("\u3000", " ").rstrip() for line in (text or "").splitlines()]
    collapsed: list[str] = []
    for line in lines:
        if not line and (not collapsed or not collapsed[-1]):
            continue
        collapsed.append(line)
    return "\n".join(collapsed).strip()


def script_key(text: str, language: str) -> str:
    """讲稿指纹：语言进 key，因为同一段文本中英朗读是两份不同音频。"""
    payload = f"{language}\n{normalize_script(text)}".encode()
    return sha256_bytes(payload)


def voice_key(language: str, voice_id: str, speed: float, engine: str, engine_version: str) -> str:
    """语音参数指纹：任一项变化都必须重新合成。"""
    payload = f"{engine}@{engine_version}|{language}|{voice_id}|{speed:.2f}".encode()
    return sha256_bytes(payload)


def audio_key(script_sha256: str, voice_fingerprint: str, variant: str = "") -> str:
    """页音频指纹。

    `variant` 区分「同一讲稿 + 同一音色」下的不同合成方式（如段间停顿变化）；
    为空时与改造前完全一致，老缓存照样命中。
    """
    payload = f"audio\n{script_sha256}\n{voice_fingerprint}"
    if variant:
        payload = f"{payload}\n{variant}"
    return sha256_bytes(payload.encode())


def segment_audio_key(text: str, language: str, voice_fingerprint: str) -> str:
    """段级音频指纹：只改一句话时，其余句子的音频仍能命中缓存。"""
    payload = f"audio-seg\n{language}\n{normalize_script(text)}\n{voice_fingerprint}".encode()
    return sha256_bytes(payload)


def segment_key(
    image_sha256: str,
    audio_fingerprint: str,
    encoder_key: str = ENCODER_KEY,
    visual_key: str = "",
) -> str:
    """页片段指纹：页图 + 音频 + 编码参数 + 视觉引导，任一变化都要重渲该页。

    `visual_key` 为空表示本页没有页内高亮（画面就是那张静帧）。
    开启高亮后画面变成多段静帧序列，页图 sha256 不再能代表画面内容，
    必须把分句/高亮框指纹一起进 key，否则旧片段会被原样复用、高亮永不生效。
    """
    return sha256_bytes(f"segment\n{image_sha256}\n{audio_fingerprint}\n{encoder_key}\n{visual_key}".encode())


def body_key(segment_keys: Sequence[str]) -> str:
    """正文块指纹：第 2 页起的有序哈希；空正文返回空串。"""
    ordered = list(segment_keys)
    if not ordered:
        return ""
    return sha256_bytes(("body\n" + "\n".join(ordered)).encode())


def slide_input_key(slide_no: int, script_sha256: str, voice_fingerprint: str) -> str:
    """单页「输入」指纹：渲染前即可算出，用于判断是否需要重新生成。"""
    return sha256_bytes(f"input\n{slide_no}\n{script_sha256}\n{voice_fingerprint}".encode())


def body_input_key(slide_input_keys: Sequence[str]) -> str:
    """正文输入签名：第 2 页起的有序哈希，用于 `body_stale` 判断。"""
    ordered = list(slide_input_keys)
    if not ordered:
        return ""
    return sha256_bytes(("body-input\n" + "\n".join(ordered)).encode())


def version_file_name(project_name: str, version_no: int, head_key: str) -> str:
    """视频文件名：可区分版本，且带上片头指纹前 8 位便于人工核对。"""
    safe = "".join(ch for ch in project_name if ch not in '\\/:*?"<>|').strip() or "ppt-video"
    return f"{safe}-v{version_no}-{head_key[:8]}.mp4"


@dataclass(frozen=True)
class ManifestSlide:
    """单页中间产物指纹与复用命中情况。"""

    slide_no: int
    image_sha256: str
    audio_sha256: str
    segment_sha256: str
    duration_ms: int
    cache_hit: bool
    #: 稳定页身份；老 manifest 没有该字段，读出来是空串
    slide_uid: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "slide_no": self.slide_no,
            "slide_uid": self.slide_uid,
            "image_sha256": self.image_sha256,
            "audio_sha256": self.audio_sha256,
            "segment_sha256": self.segment_sha256,
            "duration_ms": self.duration_ms,
            "cache_hit": self.cache_hit,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ManifestSlide":
        return cls(
            slide_no=int(data["slide_no"]),
            image_sha256=str(data["image_sha256"]),
            audio_sha256=str(data["audio_sha256"]),
            segment_sha256=str(data["segment_sha256"]),
            duration_ms=int(data.get("duration_ms", 0)),
            cache_hit=bool(data.get("cache_hit", False)),
            slide_uid=str(data.get("slide_uid", "")),
        )


@dataclass
class Manifest:
    """一次渲染的完整取证记录（写入版本表，供 TC-006 核对）。"""

    project_id: str
    head_key: str
    body_key_value: str
    encoder_key: str = ENCODER_KEY
    version: int = MANIFEST_VERSION
    slides: list[ManifestSlide] = field(default_factory=list)
    total_duration_ms: int = 0

    def reuse_summary(self) -> dict[str, int]:
        """复用统计：命中页数 / 新合成页数 / 片头是否复用。"""
        reused = sum(1 for slide in self.slides if slide.cache_hit)
        head = next((slide for slide in self.slides if slide.slide_no == 1), None)
        return {
            "total_slides": len(self.slides),
            "reused_slides": reused,
            "rendered_slides": len(self.slides) - reused,
            "body_reused_slides": sum(1 for slide in self.slides if slide.slide_no > 1 and slide.cache_hit),
            "body_rendered_slides": sum(1 for slide in self.slides if slide.slide_no > 1 and not slide.cache_hit),
            "head_reused": 1 if head is not None and head.cache_hit else 0,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "project_id": self.project_id,
            "encoder_key": self.encoder_key,
            "head_key": self.head_key,
            "body_key": self.body_key_value,
            "total_duration_ms": self.total_duration_ms,
            "reuse": self.reuse_summary(),
            "slides": [slide.as_dict() for slide in self.slides],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Manifest":
        return cls(
            project_id=str(data.get("project_id", "")),
            head_key=str(data.get("head_key", "")),
            body_key_value=str(data.get("body_key", "")),
            encoder_key=str(data.get("encoder_key", ENCODER_KEY)),
            version=int(data.get("version", MANIFEST_VERSION)),
            slides=[ManifestSlide.from_dict(item) for item in data.get("slides", [])],
            total_duration_ms=int(data.get("total_duration_ms", 0)),
        )
