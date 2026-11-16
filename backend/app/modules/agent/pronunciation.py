"""发音词典：把容易读错的词替换成同音/等价写法再送 TTS。

为什么要替换而不是直接改讲稿
--------------------------
讲稿同时是高亮匹配与版本回滚的依据，改讲稿会让「讲到的词」和页面文字对不上。
这里只在「送 TTS 之前」做一次替换，讲稿、段级绑定、页面文字全部保持原样。

为什么不注入 pypinyin 词表
------------------------
验证结论（backend/docs/ppt-video-pronunciation-spike.md）：misaki 的中文前端用的是
pypinyin 全局词表，注入确实能改读音，但词表是**进程级**的，项目级词条会串到别的项目，
且无法卸载。因此统一用「文本替换」实现：行为可预测、按项目隔离、失败也不影响合成。

两层词表
--------
- 模块级：`AGENT_PPT_VIDEO_PRONUNCIATION_DICT`（JSON 字符串），全模块生效；
- 项目级：`ppt_video_project.pronunciation_dict`，覆盖同名模块级词条。

任一层的词条变化都会改变词典指纹，进而改变音频缓存 key（`cache.voice_key`），
词条改完下次试听/出片即重新合成，不需要手工清缓存。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

#: 单层词表条数上限：再多会拖慢合成前的扫描，也说明该改讲稿
MAX_ENTRIES = 500
#: 原文最长长度（防止把整句塞进 key）
MAX_KEY_CHARS = 32
#: 替代文本最长长度
MAX_VALUE_CHARS = 64


def normalize_entries(raw: Mapping[str, object] | None) -> dict[str, str]:
    """清洗一层词表：去空白、去空项、限制长度与条数；保留插入顺序。"""
    if not raw:
        return {}
    cleaned: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        source = key.strip()
        target = value.strip()
        if not source or not target or source == target:
            continue
        if len(source) > MAX_KEY_CHARS or len(target) > MAX_VALUE_CHARS:
            continue
        cleaned[source] = target
        if len(cleaned) >= MAX_ENTRIES:
            break
    return cleaned


def parse_module_dict(raw: str | None) -> dict[str, str]:
    """解析模块级 JSON 词表；坏 JSON / 非对象一律当空表，不阻塞出片。"""
    if not raw or not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except ValueError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return normalize_entries(payload)


@dataclass(frozen=True)
class Lexicon:
    """合并后的生效词表。"""

    entries: dict[str, str] = field(default_factory=dict)
    #: 最长 key 优先，保证「阿胶口服液」不会被「阿胶」先吃掉
    _pattern: re.Pattern[str] | None = None

    @property
    def fingerprint(self) -> str:
        """词表指纹：进音频缓存 key，词条一变旧音频自然失效。"""
        if not self.entries:
            return ""
        payload = "\n".join(f"{key}={self.entries[key]}" for key in sorted(self.entries))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @property
    def empty(self) -> bool:
        return not self.entries

    def apply(self, text: str) -> tuple[str, int]:
        """单遍替换，返回 (替换后的文本, 命中次数)。

        单遍是关键：替换出来的字不能再次参与匹配，否则「A→B、B→C」会连环替换。
        """
        if not self.entries or not text:
            return text, 0
        pattern = self._pattern
        if pattern is None:
            keys = sorted(self.entries, key=len, reverse=True)
            pattern = re.compile("|".join(re.escape(key) for key in keys))
            object.__setattr__(self, "_pattern", pattern)
        replaced, count = pattern.subn(lambda match: self.entries[match.group(0)], text)
        return replaced, count


def build(module_raw: str | None = None, project_entries: Mapping[str, object] | None = None) -> Lexicon:
    """合并模块级与项目级词表：项目级覆盖同名条目。"""
    merged = parse_module_dict(module_raw)
    merged.update(normalize_entries(project_entries))
    return Lexicon(entries=merged)
