"""构建期预下载 TTS 权重，让 worker 镜像在完全离线环境也能合成旁白。

用法（worker 镜像构建时由 Dockerfile.worker 调用）：
    HF_ENDPOINT=https://hf-mirror.com HF_HOME=/opt/tts-models \
        .venv/bin/python scripts/ci/preload_tts_models.py

设计说明：
- 修订号钉死在 `app/modules/agent/tts_assets.py`（commit sha），`main` 分支换权重不会悄悄
  改变成片音质，也不会让「按音频 sha256 命中」的复用缓存前后不可比；
- 只下载推理必需的 config + voices + 主权重，跳过示例音频与 wiki 图；
- 下载后逐文件核对 sha256（HF LFS oid），不一致直接失败，避免「看着成功、跑起来缺权重」
  或「权重被换过但没人发现」；
- 任一仓库失败即退出码非 0，构建日志可直接作为交付说明的来源与版本证据。
"""

import hashlib
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

#: 与 backend/app/modules/agent/tts_assets.py 同源；用路径加载可避免构建期初始化整个 app 包
_ASSETS_FILE = Path(__file__).resolve().parents[2] / "app" / "modules" / "agent" / "tts_assets.py"

IGNORE_PATTERNS = ["*.wav", "*.mp3", "samples/*", "demo/*", "*.png", "*.jpg", "*.md"]


def _load_assets() -> ModuleType:
    spec = importlib.util.spec_from_file_location("agent_tts_assets", _ASSETS_FILE)
    if spec is None or spec.loader is None:  # pragma: no cover - 文件缺失属构建环境问题
        raise RuntimeError(f"无法加载权重清单：{_ASSETS_FILE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify(snapshot_dir: Path, expected: dict[str, str]) -> list[str]:
    """返回不匹配/缺失的文件说明；空列表表示全部通过。"""
    problems: list[str] = []
    for relative, expected_sha in expected.items():
        target = snapshot_dir / relative
        if not target.is_file():
            problems.append(f"缺少 {relative}")
            continue
        actual = _sha256(target)
        if actual != expected_sha:
            problems.append(f"{relative} sha256 不符：期望 {expected_sha[:12]}… 实际 {actual[:12]}…")
    return problems


def main() -> int:
    endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co")
    cache_dir = os.environ.get("HF_HOME", "/opt/tts-models")
    print(f"HF_ENDPOINT={endpoint} HF_HOME={cache_dir}")

    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:  # pragma: no cover - 构建期环境问题
        print(f"huggingface_hub 未安装，无法预下载：{exc}", file=sys.stderr)
        return 2

    assets = _load_assets()
    repos: tuple[tuple[str, str, str], ...] = (
        (assets.KOKORO_EN_REPO, assets.KOKORO_EN_REVISION, "en"),
        (assets.KOKORO_ZH_REPO, assets.KOKORO_ZH_REVISION, "zh"),
    )

    failures: list[str] = []
    for repo_id, revision, language in repos:
        try:
            path = snapshot_download(
                repo_id=repo_id,
                revision=revision,
                cache_dir=cache_dir,
                ignore_patterns=IGNORE_PATTERNS,
            )
        except Exception as exc:  # noqa: BLE001 - 构建期需要把任何下载异常都当作失败
            print(f"✗ [{language}] {repo_id}@{revision[:8]} 下载失败：{exc}", file=sys.stderr)
            failures.append(repo_id)
            continue

        problems = _verify(Path(path), assets.ASSET_SHA256.get(repo_id, {}))
        if problems:
            print(f"✗ [{language}] {repo_id}@{revision[:8]} 校验失败：", file=sys.stderr)
            for problem in problems:
                print(f"    - {problem}", file=sys.stderr)
            failures.append(repo_id)
            continue

        print(f"✓ [{language}] {repo_id}@{revision[:8]} -> {path}（sha256 全部核对通过）")

    if failures:
        print("以下仓库未就绪：" + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())