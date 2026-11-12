# TTS PoC 报告：Kokoro-82M 本地合成（中英）

支撑 TC-010（工具链/依赖/许可可交付）。目标不是评测「哪个 TTS 最好」，而是回答三个落地问题：
**CPU 上能不能跑、跑一页要多久、许可能不能商用**。

- 执行时间：2026-11-03
- 执行机：开发机（Intel Xeon Platinum，8 vCPU / 4 核 2 线程，纯 CPU，无 GPU）
- 并行度：`OMP_NUM_THREADS=2`（与 worker 镜像内 `OMP_NUM_THREADS=2` 一致）
- 环境：Python 3.12.14、torch 2.15.0+cpu、kokoro 0.9.4、misaki 0.9.4、soundfile 0.14.0、
  numpy 2.5.4、jieba 0.42.1、spaCy 3.8.18 + `en_core_web_sm` 3.8.0

> 说明：PoC 环境在 `/tmp/tts-poc`，**不进仓库**；仓库内固定版本的文件是
> `backend/requirements-tts.txt`（soundfile 钉 0.13.1）与 `scripts/ci/preload_tts_models.py`。
> 本次实测用 soundfile 0.14.0，差异不影响结论（只用于写 wav）。

---

## 1. 用例

| 用例 | 语言/音色 | 文本 | 字符数 |
|---|---|---|---|
| zh | `zh` / `zf_001` | 本次汇报介绍2026年第一季度研发进展，重点说明三个原料药项目的注册申报节点。 | 39 |
| en | `en` / `af_bella` | This update covers our research progress in the first quarter of 2026, focusing on three API registration milestones. | 117 |

两条都用**本地权重**加载（`KModel(config=…, model=…)` + `KPipeline(voice=<本地 .pt>)`），
不经过 `hf_hub_download`，确保测的是推理耗时而不是网络耗时。
中文用例显式传 `repo_id="hexgrad/Kokoro-82M-v1.1-zh"`（决定中文 G2P 用 v1.1 词表）。

---

## 2. 结果

| 指标 | zh（zf_001） | en（af_bella） |
|---|---|---|
| 模型加载（含 jieba/spaCy 初始化） | 3.58 s | 2.42 s |
| 首次合成（冷） | 5.54 s | 5.03 s |
| 第二次合成（热） | 3.89 s | 4.91 s |
| 音频时长 | 8.18 s | 9.15 s |
| **RTF（热，合成耗时/音频时长）** | **0.475** | **0.537** |
| RTF（冷） | 0.677 | 0.550 |
| 首块延迟 | 5.54 s（= 整段） | 5.03 s（= 整段） |
| 采样率 / 字节数 | 24 kHz / 392,444 B | 24 kHz / 439,244 B |
| wav sha256 | `56bc0981128c64a1…` | `36a4dc2af7eff0ec…` |
| 峰值 / RMS | 0.500 / 0.0517 | 0.698 / 0.0552 |
| 直流偏移 | −0.00002 | −0.00001 |
| 削波样本数（\|x\|≥0.999） | 0 | 0 |
| 首/尾静音 | 0.32 s / 0.76 s | 0.42 s / 0.58 s |
| 有效语速 | 39 字 / 7.10 s ≈ 5.5 字/秒 | 117 字符 / 8.15 s ≈ 14.4 字符/秒 |

**换算口径（2 线程 CPU）**：1 分钟音频约需 **29~32 秒**合成；12 页 × 12 秒旁白（约 144 s 音频）
约需 **70 秒**纯 TTS，另加每页 ffmpeg 编码与拼接时间。这是估算，不是实测整片耗时。

---

## 3. 结论

1. **CPU 可跑，不需要 GPU。** RTF 0.48~0.54，意味着单 worker 串行渲染时 TTS 不是瓶颈，
   瓶颈更可能在 LibreOffice 转 PDF（页数多时）与 ffmpeg 编码。
2. **热启动才代表稳定成本。** 冷启动多出 1~1.5 秒（模型加载 + 首次 kernel 预热），
   而 worker 是常驻进程、按页复用同一 pipeline，因此按 RTF 0.48~0.54 估算即可。
3. **没有流式收益。** 当前调用方式对短讲稿只产出一个 chunk，首块延迟 = 整段耗时。
   页级轮询（2 s）足够，但如果以后要「边合成边出声」，得改 `KPipeline` 的 `split_pattern`
   或按句切分再拼，本轮未做。
4. **中英混排必须注入英文 G2P。** 实测同一句中文里夹 `GMP/HPLC/API`：

   | 配置 | 音素输出（截断） |
   |---|---|
   | 无 `en_callable` | `ㄅㄣ3ㄘㄭ4 ❓ ㄖㄣ4ㄓㄥ4/ㄕㄜ4ㄐㄧ2 ❓ ㄩ3 ❓ ㄔㄜ1ㄐ言1.` |
   | 有 `en_callable` | `ㄅㄣ3ㄘㄭ4 ʤˌiˌɛmpˈi ㄖㄣ4ㄓㄥ4/ㄕㄜ4ㄐㄧ2 ˌAʧpˌiˌɛlsˈi ㄩ3 ˌApˌiˈI ㄔㄜ1ㄐ言1.` |

   `❓` 就是被丢掉读不出来的词。`app/modules/agent/tts.py` 已改为给中文 pipeline 注入
   `_english_g2p()`（依赖 `en_core_web_sm`），拿不到模型时降级为「跳过英文」并打 WARNING。

---

## 4. 听感

**必须说明：本轮没有任何人耳试听**，我无法给出「像不像真人」的判断。以下是可复核的客观事实，
主观听感请验收人按第 4.3 节清单自行确认。

### 4.1 客观指标

- 无削波（峰值 0.50 / 0.70，远低于 1.0），不存在爆音风险；
- 直流偏移约 1e-5，无声学中心偏移；
- 首尾静音 0.3~0.8 s，属于正常起收；
- 24 kHz 单声道、PCM16，与 Kokoro-82M 原生输出一致（未做重采样，没有采样率转换损失）。

### 4.2 试听文件（本机，未入库）

- `/tmp/tts-poc/out/zh_zf_001.wav`
- `/tmp/tts-poc/out/en_af_bella.wav`

### 4.3 建议的听感检查清单

1. 数字读法：`2026` 读「二零二六」还是「两千零二十六」，是否可接受；
2. 专有名词/缩写：`GMP`、`HPLC`、`API` 是否读成字母串而非拼读成一个词；
3. 断句：长句（>30 字）是否在逗号处停；
4. 语速：`speed=1.0` 是否偏快（中文 5.5 字/秒接近新闻播报，偏快）；
5. 音色稳定性：同一段文本连续合成 3 次，听是否有音色漂移/杂音。

---

## 5. 许可

| 组件 | 许可 | 商用结论 |
|---|---|---|
| Kokoro-82M 权重（en v1.0 / zh v1.1-zh） | Apache-2.0 | 可商用，保留许可与 NOTICE |
| kokoro (pip) / misaki | Apache-2.0 | 可商用 |
| torch / soundfile / spaCy / en_core_web_sm / jieba | BSD-3 / MIT | 可商用 |
| espeak-ng（misaki[en] 的 OOD 词回退） | GPL-3.0 | 内部使用无义务；对外分发镜像需附 GPL 声明 |
| 音色文件（`*.pt`） | 随仓库 Apache-2.0 | 可商用；`GET /voices` 会返回逐条许可字段 |

权重钉版本：`app/modules/agent/tts_assets.py`（仓库 rev + 11 个文件 sha256），
`scripts/ci/preload_tts_models.py` 逐文件校验，不符即构建失败。

---

## 6. 本轮没做的事（缺口）

1. 只测了 2 条音色（`zf_001`、`af_bella`），其余 7 条未抽检；
2. 未采内存峰值 RSS（长 PPT 是否会 OOM 未量化）；
3. 未测并发（worker 固定 `PPT_VIDEO_WORKER_CONCURRENCY=1`）；
4. 未做流式首响；
5. 未在 worker 镜像内复测（本机裸 venv，镜像内多套 LibreOffice/ffmpeg，TTS 部分应一致）。