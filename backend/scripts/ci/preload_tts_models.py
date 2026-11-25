"""构建期预下载 TTS 权重，让 worker 镜像在完全离线环境也能合成旁白。

用法（worker 镜像构建时由 Dockerfile.worker 调用）：
    HF_HOME=/opt/tts-models PRELOAD_TTS_SOURCE=modelscope \
        .venv/bin/python scripts/ci/preload_tts_models.py

设计说明：
- **两条通道**（`PRELOAD_TTS_SOURCE`，默认 modelscope）：
  - `modelscope`：直连 modelscope.cn 的 `resolve` 接口逐文件下载，匿名可用且支持 Range。
    厂区内网到 hf-mirror 只有约 20KB/s（327MB×2 要几小时），ModelScope 是 #236 的
    实际可用出口；两个仓库与 HF 同名，文件 sha256 实测逐文件一致。
  - `huggingface`：原通道，走 `HF_ENDPOINT`（默认 hf-mirror），作为回退保留。
  顺序不能反：先走 hf-mirror 会把构建时间耗光，回退就失去意义。
- **必须物化成 HF hub 布局**：运行时 `KPipeline(repo_id=…)` 只认
  `<HF_HUB_CACHE>/models--<org>--<name>/snapshots/<commit>/…` 与 `refs/main`。
  注意 `HF_HOME=/opt/tts-models` 时真实缓存根是 `/opt/tts-models/hub`，
  不能把 `HF_HOME` 直接当 cache_dir（否则权重落在运行时找不到的目录，等于白装）。
- **双钉**：`MODELSCOPE_REVISION` 钉住下载来源（可复现），`ASSET_SHA256` 钉住内容
  （下载源只影响速度，不影响结果）。任一文件缺失/不符即构建失败，不产出
  「看着成功、跑起来缺权重」的镜像。
"""

import hashlib
import importlib.util
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from types import ModuleType

#: 与 backend/app/modules/agent/tts_assets.py 同源；用路径加载可避免构建期初始化整个 app 包
_ASSETS_FILE = Path(__file__).resolve().parents[2] / "app" / "modules" / "agent" / "tts_assets.py"

IGNORE_PATTERNS = ["*.wav", "*.mp3", "samples/*", "demo/*", "*.png", "*.jpg", "*.md"]

MODELSCOPE_ENDPOINT = "https://modelscope.cn"
DOWNLOAD_ATTEMPTS = 3
DOWNLOAD_TIMEOUT_SECONDS = 120


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


def _hub_cache() -> Path:
    """huggingface_hub 实际使用的缓存根目录（与运行时 `KPipeline` 完全一致）。"""
    from huggingface_hub.constants import HF_HUB_CACHE

    return Path(HF_HUB_CACHE)


def _repo_dir(cache_root: Path, repo_id: str) -> Path:
    return cache_root / f"models--{repo_id.replace('/', '--')}"


def _snapshot_dir(cache_root: Path, repo_id: str, revision: str) -> Path:
    return _repo_dir(cache_root, repo_id) / "snapshots" / revision


def _write_ref(cache_root: Path, repo_id: str, revision: str) -> None:
    """写 `refs/main`：运行时调用不带 revision，hub 先读它再找 `snapshots/<commit>`。"""
    ref = _repo_dir(cache_root, repo_id) / "refs" / "main"
    ref.parent.mkdir(parents=True, exist_ok=True)
    ref.write_text(revision, encoding="utf-8")


def _modelscope_url(repo_id: str, revision: str, relative: str) -> str:
    quoted = urllib.parse.quote(relative)
    return f"{MODELSCOPE_ENDPOINT}/models/{repo_id}/resolve/{revision}/{quoted}"


def _download(url: str, target: Path) -> None:
    """单文件下载：3 次重试 + 指数退避，先写 `.part` 再改名，避免半截文件被当成成功。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".part")
    last_error: Exception | None = None
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "livzon-tts-preload/1.0"})
            with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
                with temp.open("wb") as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
            temp.replace(target)
            return
        except Exception as exc:  # noqa: BLE001 - 构建期把任何下载异常都当失败并重试
            last_error = exc
            temp.unlink(missing_ok=True)
            if attempt < DOWNLOAD_ATTEMPTS:
                time.sleep(2 ** (attempt - 1))  # 1s, 2s
    raise RuntimeError(f"下载失败 {url}: {last_error}")


def _preload_from_modelscope(assets: ModuleType, cache_root: Path, repo_id: str) -> list[str]:
    """逐文件从 ModelScope 下载 → 校验 → 物化成 HF hub 布局；返回问题列表。"""
    revision_ms = assets.MODELSCOPE_REVISION[repo_id]
    revision_hf = assets.HF_REVISION[repo_id]
    expected = assets.ASSET_SHA256[repo_id]
    snapshot = _snapshot_dir(cache_root, repo_id, revision_hf)

    problems: list[str] = []
    for relative, expected_sha in expected.items():
        target = snapshot / relative
        try:
            _download(_modelscope_url(repo_id, revision_ms, relative), target)
        except Exception as exc:  # noqa: BLE001 - 单文件失败汇总后决定是否回退
            problems.append(f"{relative} 下载失败：{exc}")
            continue
        actual = _sha256(target)
        if actual != expected_sha:
            target.unlink(missing_ok=True)
            problems.append(f"{relative} sha256 不符：期望 {expected_sha[:12]}… 实际 {actual[:12]}…")
    if not problems:
        _write_ref(cache_root, repo_id, revision_hf)
    return problems


def _preload_from_huggingface(assets: ModuleType, cache_root: Path, repo_id: str) -> list[str]:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:  # pragma: no cover - 构建期环境问题
        return [f"huggingface_hub 未安装：{exc}"]

    revision = assets.HF_REVISION[repo_id]
    try:
        path = snapshot_download(
            repo_id=repo_id,
            revision=revision,
            cache_dir=str(cache_root),
            ignore_patterns=IGNORE_PATTERNS,
        )
    except Exception as exc:  # noqa: BLE001 - 构建期需要把任何下载异常都当作失败
        return [f"{repo_id}@{revision[:8]} 下载失败：{exc}"]
    return _verify(Path(path), assets.ASSET_SHA256[repo_id])


def main() -> int:
    source = (os.environ.get("PRELOAD_TTS_SOURCE") or "modelscope").strip().lower()
    endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co")
    assets = _load_assets()

    try:
        cache_root = _hub_cache()
    except ImportError as exc:
        print(f"huggingface_hub 未安装，无法预下载：{exc}", file=sys.stderr)
        return 2
    print(f"PRELOAD_TTS_SOURCE={source} HF_ENDPOINT={endpoint} HF_HUB_CACHE={cache_root}")

    failures: list[str] = []
    for repo_id, expected in assets.ASSET_SHA256.items():
        channel = "huggingface"
        if source == "modelscope":
            channel = "modelscope"
            problems = _preload_from_modelscope(assets, cache_root, repo_id)
            if problems:
                print(f"⚠ {repo_id} ModelScope 通道未通过，回退 huggingface：", file=sys.stderr)
                for problem in problems:
                    print(f"    - {problem}", file=sys.stderr)
                channel = "huggingface"
                problems = _preload_from_huggingface(assets, cache_root, repo_id)
        else:
            problems = _preload_from_huggingface(assets, cache_root, repo_id)

        if problems:
            print(f"✗ {repo_id} 预装失败（通道 {channel}）：", file=sys.stderr)
            for problem in problems:
                print(f"    - {problem}", file=sys.stderr)
            failures.append(repo_id)
            continue

        snapshot = _snapshot_dir(cache_root, repo_id, assets.HF_REVISION[repo_id])
        print(
            f"✓ {repo_id}@{assets.HF_REVISION[repo_id][:8]} 经 {channel} 就绪：{snapshot}"
            f"（{len(expected)} 个文件 sha256 全部核对通过）"
        )

    if failures:
        print("以下仓库未就绪：" + ", ".join(failures), file=sys.stderr)
        return 1

    # 收尾自检：用运行时同一份判定再确认一次 refs/main 与所有文件都能命中
    leftover = assets.missing_assets()
    if leftover:
        print("收尾自检失败（运行时会找不到权重）：", file=sys.stderr)
        for problem in leftover:
            print(f"    - {problem}", file=sys.stderr)
        return 1
    print("✓ 离线自检通过：refs/main 与全部权重文件均可在 HF 缓存中命中")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
