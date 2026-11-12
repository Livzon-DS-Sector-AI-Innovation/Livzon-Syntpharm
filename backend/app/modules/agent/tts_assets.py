"""TTS 权重：仓库、固定修订号与文件 sha256。

**不 import 任何业务代码**，构建期脚本（`scripts/ci/preload_tts_models.py`）可以按文件路径
直接加载本模块，不必先把整个 `app` 包初始化起来。

为什么要钉死修订号：`main` 分支上的权重会被替换，同一段讲稿可能因此换音色/换质量，
复用缓存（按音频 sha256 命中）就失去可比性。`revision` 取的是 Hugging Face 仓库的
commit sha，不可变；`ASSET_SHA256` 取的是文件 LFS oid（即文件内容的 sha256），
下载后可逐文件核对。

核实时间 2026-11，来源 hf-mirror.com 模型卡与文件清单接口：
- https://hf-mirror.com/hexgrad/Kokoro-82M          Apache-2.0
- https://hf-mirror.com/hexgrad/Kokoro-82M-v1.1-zh  Apache-2.0
"""

KOKORO_EN_REPO = "hexgrad/Kokoro-82M"
KOKORO_EN_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
KOKORO_EN_LAST_MODIFIED = "2025-04-10"

KOKORO_ZH_REPO = "hexgrad/Kokoro-82M-v1.1-zh"
KOKORO_ZH_REVISION = "01e7505bd6a7a2ac4975463114c3a7650a9f7218"
KOKORO_ZH_LAST_MODIFIED = "2025-03-04"

KOKORO_LICENSE = "Apache-2.0"

#: 仓库 → {仓库内相对路径: 文件 sha256}；只登记音色目录里用到的声线 + 主权重
ASSET_SHA256: dict[str, dict[str, str]] = {
    KOKORO_EN_REPO: {
        "kokoro-v1_0.pth": "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4",
        "voices/af_bella.pt": "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6",
        "voices/bf_emma.pt": "d0a423deabf4a52b4f49318c51742c54e21bb89bbbe9a12141e7758ddb5da701",
        "voices/am_michael.pt": "9a443b79a4b22489a5b0ab7c651a0bcd1a30bef675c28333f06971abbd47bd37",
        "voices/bm_george.pt": "f1bc812213dc59774769e5c80004b13eeb79bd78130b11b2d7f934542dab811b",
    },
    KOKORO_ZH_REPO: {
        "kokoro-v1_1-zh.pth": "b1d8410fa44dfb5c15471fd6c4225ea6b4e9ac7fa03c98e8bea47a9928476e2b",
        "voices/zf_001.pt": "9bdc9a87e13e9bb1ea3e7803259c2ecbfebaeeb2ff80b5d0c76df1a464c1c962",
        "voices/zf_002.pt": "2c8cf221ff2e0915fc807cac5f233f42798ee8e2bd58bc5ad0259fd95e405a26",
        "voices/zf_003.pt": "ac28a59eefaa7e37b2aabffc792d40081392aa89d679b579859debf5209441a1",
        "voices/zf_017.pt": "e507bb858a75f0518f08918827740530a656a008e3c057435a17b3a95f267624",
        "voices/zm_010.pt": "d2eeba86192eee269f600ca6821038034abd017532a1fe68ff7b0e86c2983b2a",
    },
}
