"""运行时配置的双向登记一致性：防「改了代码没登记 seed」与「seed 插了没人读的键」。

背景：doc_gen 的运营参数走 ``core.module_settings``（Web UI 可调），代码侧由
``runtime_config.load_runtime_config`` 逐个键读取，登记由 ``seed_module_settings.py``
负责。两处只改一边就会出现：键在 Web UI 不可见、调了不生效，或 seed 插入了永不读取的脏键。
这个测试把两边钉在一起（新增配置时忘了登记会在这里失败，而不是等线上发现）。
"""

from __future__ import annotations

import re
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[4]
RUNTIME_CONFIG = BACKEND_ROOT / "app/modules/research/doc_gen/runtime_config.py"
SEED_SCRIPT = BACKEND_ROOT / "scripts/seed/seed_module_settings.py"

_KEY_RE = re.compile(r'"(DOC_GEN_[A-Z0-9_]+)"')


def _keys(path: Path) -> set[str]:
    return set(_KEY_RE.findall(path.read_text(encoding="utf-8")))


def test_every_runtime_key_is_registered_in_seed() -> None:
    """runtime_config 读取的每个 DOC_GEN_* 键都必须登记在 seed 里。"""
    missing = sorted(_keys(RUNTIME_CONFIG) - _keys(SEED_SCRIPT))
    assert missing == [], f"以下运行时配置键未登记到 seed_module_settings.py：{missing}"


def test_every_seed_key_is_read_by_runtime_config() -> None:
    """seed 里登记的每个 DOC_GEN_* 键都必须被 runtime_config 读取（防止脏键）。"""
    orphan = sorted(_keys(SEED_SCRIPT) - _keys(RUNTIME_CONFIG))
    assert orphan == [], f"seed 里存在未被 runtime_config 读取的键：{orphan}"
