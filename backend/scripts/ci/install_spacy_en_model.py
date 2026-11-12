"""构建期安装 spaCy 英文模型（Kokoro 英文 G2P 的硬依赖）。

为什么需要它
------------
`kokoro` 依赖 `misaki[en]`，会装上 spaCy 本体；但 `en_core_web_sm` **不在 PyPI 上**，
只能从 GitHub Release 或 Hugging Face 镜像取。缺了它，英文页旁白合成会直接抛
「Connection reset / 无法下载模型」。所以这里在构建期装好，缺模型就让构建失败，
不允许把「英文配音不可用」的镜像静默发布出去。

两条来源（都钉版本 + 校验 sha256）
----------------------------------
1. GitHub Release 的 3.8.0 wheel（与 spaCy 3.8 严格对齐，优先）；
2. Hugging Face 镜像 `spacy/en_core_web_sm` 里的 3.7.1 wheel（GitHub 不可达时回退，
   对 spaCy 3.8 有兼容性告警但 POS 标注可用，已实测）。

用法：`.venv/bin/python scripts/ci/install_spacy_en_model.py [--force]`
环境变量：`SPACY_MODEL_SOURCE=github|hf` 可强制指定来源（默认 github → hf 依次尝试）。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

MODEL_NAME = "en_core_web_sm"

#: GitHub Release 3.8.0（首选）
GITHUB_URL = (
    "https://github.com/explosion/spacy-models/releases/download/"
    f"{MODEL_NAME}-3.8.0/{MODEL_NAME}-3.8.0-py3-none-any.whl"
)
GITHUB_SHA256 = "1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85"

#: hf-mirror 回退源：仓库内 wheel 名带 `-any-`，落地后改名成标准 wheel 名（内含 3.7.1 模型）
HF_REPO = "spacy/en_core_web_sm"
HF_REVISION = "8fb6f8155286360bf5486fe399e2738d1df7ded2"
HF_REMOTE_NAME = "en_core_web_sm-any-py3-none-any.whl"
HF_WHEEL_NAME = "en_core_web_sm-3.7.1-py3-none-any.whl"
HF_SHA256 = "86cc141f63942d4b2c5fcee06630fd6f904788d2f0ab005cce45aadb8fb73889"

#: 单次下载超时。GitHub 在厂区内网时通时不通，卡死会给构建挂上十几分钟；
#: 90 秒足够下完 12 MB 的 wheel，超时就走 hf-mirror 回退。
TIMEOUT_SECONDS = 90
CHUNK = 1024 * 1024


def _log(message: str) -> None:
    print(f"[spacy-model] {message}", flush=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, target: Path) -> None:
    _log(f"下载 {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "erp-ppt-video-worker/1.0"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response, target.open("wb") as handle:
        while chunk := response.read(CHUNK):
            handle.write(chunk)


def _site_packages() -> Path:
    import spacy  # 本地导入：脚本可能在没装 spaCy 的机器上被误跑

    return Path(spacy.__file__).resolve().parent.parent


def _is_installed() -> bool:
    try:
        import spacy

        return bool(spacy.util.is_package(MODEL_NAME))
    except Exception:  # noqa: BLE001 - 装没装都能走到下面的安装分支
        return False


def _verify_loadable() -> None:
    """装完立刻自检：能加载且能出词性，否则构建就该失败。"""
    import spacy

    pipeline = spacy.load(MODEL_NAME, enable=["tok2vec", "tagger"])
    tags = [token.tag_ for token in pipeline("Registration milestone 2026.")]
    if not tags:
        raise RuntimeError("模型加载成功但没有产出词性标注")
    _log(f"自检通过：{MODEL_NAME} 词性标注 {tags[:4]}")


def _extract_wheel(wheel: Path) -> None:
    """把 wheel 解到 site-packages（不依赖 pip/uv，镜像里也能跑）。"""
    target = _site_packages()
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        if not any(name.startswith(f"{MODEL_NAME}/") for name in names):
            raise RuntimeError(f"wheel 内容异常：未找到 {MODEL_NAME}/ 目录")
        archive.extractall(target)
    _log(f"已解包到 {target / MODEL_NAME}")


def _install_from(source: str, work_dir: Path) -> Path:
    wheel = work_dir / f"{MODEL_NAME}-{source}.whl"
    if source == "github":
        _download(GITHUB_URL, wheel)
        expected = GITHUB_SHA256
    elif source == "hf":
        endpoint = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com").rstrip("/")
        url = f"{endpoint}/{HF_REPO}/resolve/{HF_REVISION}/{HF_REMOTE_NAME}"
        _download(url, wheel)
        expected = HF_SHA256
    else:
        raise ValueError(f"未知来源：{source}")

    actual = _sha256(wheel)
    if actual != expected:
        raise RuntimeError(f"{source} 来源的 wheel sha256 不符：{actual} != {expected}")
    _log(f"{source} 来源 sha256 校验通过")
    _extract_wheel(wheel)
    return wheel


def main() -> int:
    parser = argparse.ArgumentParser(description="安装 spaCy 英文模型（构建期）")
    parser.add_argument("--force", action="store_true", help="已安装也重新安装")
    args = parser.parse_args()

    if _is_installed() and not args.force:
        _log(f"{MODEL_NAME} 已安装，跳过")
        _verify_loadable()
        return 0

    forced = os.environ.get("SPACY_MODEL_SOURCE", "").strip().lower()
    sources = [forced] if forced in {"github", "hf"} else ["github", "hf"]
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="spacy-model-") as raw_dir:
        work_dir = Path(raw_dir)
        for source in sources:
            try:
                _install_from(source, work_dir)
                _verify_loadable()
                _log(f"安装完成（来源 {source}）")
                return 0
            except Exception as exc:  # noqa: BLE001 - 逐个来源尝试，全部失败才报错
                failures.append(f"{source}: {exc}")
                _log(f"来源 {source} 失败：{exc}")

    print("[spacy-model] 所有来源都失败，英文配音将不可用，构建终止：", file=sys.stderr)
    for item in failures:
        print(f"  - {item}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
