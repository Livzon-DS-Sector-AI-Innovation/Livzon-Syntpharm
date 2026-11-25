"""TTS 权重：仓库、固定修订号与文件 sha256。

**不 import 任何业务代码**，构建期脚本（`scripts/ci/preload_tts_models.py`）可以按文件路径
直接加载本模块，不必先把整个 `app` 包初始化起来。

为什么要钉死修订号：`main` 分支上的权重会被替换，同一段讲稿可能因此换音色/换质量，
复用缓存（按音频 sha256 命中）就失去可比性。`revision` 取的是 Hugging Face 仓库的
commit sha，不可变；`ASSET_SHA256` 取的是文件 LFS oid（即文件内容的 sha256），
下载后可逐文件核对。

**双钉**：#236 之后构建期多了一条 ModelScope 通道（厂区内网下 hf-mirror 只有约 20KB/s，
327MB 要几小时）。ModelScope 仓库是 HF 的镜像，但**它的 commit sha 与 HF 不同**，
因此 `MODELSCOPE_REVISION` 单独记录实际核对的 ModelScope 修订号（来源可复现），
「内容等价」仍由 `ASSET_SHA256` 保证——两侧 sha256 实测逐文件一致。

核实时间 2026-11，来源模型卡与文件清单接口：
- https://hf-mirror.com/hexgrad/Kokoro-82M          Apache-2.0
- https://hf-mirror.com/hexgrad/Kokoro-82M-v1.1-zh  Apache-2.0
- https://modelscope.cn/models/hexgrad/Kokoro-82M / ...-v1.1-zh（同仓同名镜像）
"""

KOKORO_EN_REPO = "hexgrad/Kokoro-82M"
KOKORO_EN_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
KOKORO_EN_LAST_MODIFIED = "2025-04-10"

KOKORO_ZH_REPO = "hexgrad/Kokoro-82M-v1.1-zh"
KOKORO_ZH_REVISION = "01e7505bd6a7a2ac4975463114c3a7650a9f7218"
KOKORO_ZH_LAST_MODIFIED = "2025-03-04"

KOKORO_LICENSE = "Apache-2.0"

#: 仓库 → ModelScope 侧 commit sha（2026-11 实测；内容由 ASSET_SHA256 兜底）
MODELSCOPE_REVISION: dict[str, str] = {
    KOKORO_EN_REPO: "cfde5827441f4e33047bf05b966f46b105c5881d",
    KOKORO_ZH_REPO: "3bb92ed837a15179e8ccae96912cf71b196279ee",
}

#: 仓库 → HF 侧 commit sha（运行时 `KPipeline(repo_id=…)` 解析的就是它）
HF_REVISION: dict[str, str] = {
    KOKORO_EN_REPO: KOKORO_EN_REVISION,
    KOKORO_ZH_REPO: KOKORO_ZH_REVISION,
}

#: 仓库 → {仓库内相对路径: 文件 sha256}；只登记推理必需的文件。
#: `config.json` 不是可选项：kokoro 的 `KModel` 启动时按 repo_id 读它确定模型结构，
#: 缺了会在离线环境下直接报错（正是「构建说成功、运行找不到权重」的典型症状）。
ASSET_SHA256: dict[str, dict[str, str]] = {
    KOKORO_EN_REPO: {
        "config.json": "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f",
        "kokoro-v1_0.pth": "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4",
        "voices/af_bella.pt": "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6",
        "voices/bf_emma.pt": "d0a423deabf4a52b4f49318c51742c54e21bb89bbbe9a12141e7758ddb5da701",
        "voices/am_michael.pt": "9a443b79a4b22489a5b0ab7c651a0bcd1a30bef675c28333f06971abbd47bd37",
        "voices/bm_george.pt": "f1bc812213dc59774769e5c80004b13eeb79bd78130b11b2d7f934542dab811b",
    },
    KOKORO_ZH_REPO: {
        "config.json": "bc333efa5ce4ceff433c8c8e5d027a1eca0166001e4e4a62bea2d26ff7a46890",
        "kokoro-v1_1-zh.pth": "b1d8410fa44dfb5c15471fd6c4225ea6b4e9ac7fa03c98e8bea47a9928476e2b",
        "voices/zf_001.pt": "9bdc9a87e13e9bb1ea3e7803259c2ecbfebaeeb2ff80b5d0c76df1a464c1c962",
        "voices/zf_002.pt": "2c8cf221ff2e0915fc807cac5f233f42798ee8e2bd58bc5ad0259fd95e405a26",
        "voices/zf_003.pt": "ac28a59eefaa7e37b2aabffc792d40081392aa89d679b579859debf5209441a1",
        "voices/zf_017.pt": "e507bb858a75f0518f08918827740530a656a008e3c057435a17b3a95f267624",
        "voices/zm_010.pt": "d2eeba86192eee269f600ca6821038034abd017532a1fe68ff7b0e86c2983b2a",
    },
}


def missing_assets() -> list[str]:
    """返回 HF 缓存里缺失/不可用的权重说明；空列表表示运行时可以离线命中。

    构建期（preload 脚本收尾自检）与运行期（worker 启动预检）共用这一份判定，
    避免出现「构建说好了、运行时找不到」的两套口径。

    `KPipeline(repo_id=…)` 不传 revision，走 `refs/main` → snapshots/<commit>，
    因此除了文件本身，还要核对 `refs/main` 指向钉住的 commit。
    """
    try:
        from huggingface_hub import try_to_load_from_cache
        from huggingface_hub.constants import HF_HUB_CACHE
    except ImportError:  # pragma: no cover - 构建期环境缺依赖
        return ["huggingface_hub 未安装，无法核对 TTS 权重"]

    cache_root = HF_HUB_CACHE
    problems: list[str] = []
    for repo_id, files in ASSET_SHA256.items():
        revision = HF_REVISION[repo_id]
        ref_file = f"{cache_root}/models--{repo_id.replace('/', '--')}/refs/main"
        try:
            with open(ref_file, encoding="utf-8") as handle:
                ref_value = handle.read().strip()
        except OSError:
            ref_value = ""
        if ref_value != revision:
            problems.append(f"{repo_id} refs/main 缺失或指向 {ref_value or '空'}（期望 {revision}）")
        for relative in files:
            cached = try_to_load_from_cache(repo_id=repo_id, filename=relative, revision=revision)
            if not isinstance(cached, str):
                problems.append(f"{repo_id}/{relative} 未缓存")
    return problems
