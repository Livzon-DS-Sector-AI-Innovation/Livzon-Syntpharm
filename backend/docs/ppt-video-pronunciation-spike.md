# 发音词典可行性验证（misaki 0.9.4 / Kokoro 0.9.4）

- 执行时间：2026-11-16
- 执行环境：
  - worker 容器 `erp-ppt-video-worker-dev`（`/app/.venv`）
  - API 容器 `erp-backend`（镜像 `livzon-syntpharm-backend:dev-tts`，`/app/.venv`）
- 目的：确认「发音词典 + 单页试听闭环」在不换 TTS 引擎的前提下是否可落地。

## 1. 结论

**可以落地，但两条路径要分开用：**

| 词典层级 | 落地方式 | 原因 |
|---|---|---|
| 模块级默认词表 | `pypinyin.load_phrases_dict()` / `load_single_dict()` 注入 | 一次注入、进程级生效，零文本改动，讲稿与高亮匹配不受影响 |
| 项目级覆盖词表 | 合成前文本替换（原词 → 同音替代文本） | pypinyin 词表是**进程全局**，项目级注入会串项目、且无法卸载 |

`misaki.ZHG2P` 本身没有用户词表参数，但其 `ZHFrontend._init_pypinyin()` 调用的是 pypinyin 的公开 API：

```python
# /app/.venv/lib/python3.12/site-packages/misaki/zh_frontend.py:81-88
def _init_pypinyin(self):
    large_pinyin.load()
    load_phrases_dict(self.phrases_dict)
    load_single_dict({ord("地"): "de,di4"})
```

因此「先构造 `ZHG2P`，再调用 `load_phrases_dict`」即可覆盖读音（后加载的键覆盖先前的键）。

## 2. 实测记录

环境版本：misaki 0.9.4、kokoro 0.9.4、jieba 0.42.1、pypinyin 0.55.0、spacy 3.8.18、en_core_web_sm 已安装、HF_HOME=/opt/tts-models。

### 2.1 改造前（`ZHG2P(version="1.1")` 直接调用）

| 词 | 输出音素 | 判断 |
|---|---|---|
| 阿胶 | `ㄜ1ㄐ要1`（ē jiāo） | 正确 |
| 重楼 | `ㄓ中4ㄌㄡ2`（zhòng lóu） | **错误**（应 chóng lóu） |
| 枸橼 | `ㄐㄩ3元2`（jǔ yuán） | 正确 |
| 大黄 | `ㄉㄞ4ㄏ王2`（dài huáng） | 正确 |

即：常见药材名多数能读对，专业词/多音字仍有错读，词典有必要。

### 2.2 注入后（标准 pypinyin 格式）

```python
from pypinyin import load_phrases_dict

load_phrases_dict({"重楼": [["chong2"], ["lou2"]]})
```

`重楼` → `ㄔ中2ㄌㄡ2`（chóng lóu），**注入生效**。

注意格式：必须用 pypinyin 的 `[[拼音带调号数字], ...]`；misaki 自带词表里的 `ka1i` 写法是非标准格式，不要照抄。

## 3. 实现约束（写代码时必须遵守）

1. **注入时机**：`KokoroEngine._pipeline()` 构造 `KPipeline` 之后立即注入，避免被 `ZHFrontend.__init__` 的 `load_phrases_dict` 覆盖。
2. **注入失败不能阻塞合成**：捕获异常 → `logger.warning` → 继续合成（读音退化为引擎默认）。
3. **项目级词表用文本替换**：替换发生在调用 `KPipeline` 之前；讲稿原文、`script_segments`、高亮字面匹配全部保持原样。
4. **词典指纹必须进缓存 key**：否则词条改了仍旧命中旧音频。`voice_key`（模块级注入）与 `segment_audio_key`/`audio_key`（项目级替换）都要纳入。
5. **`ZHG2P.__call__` 会先做 `cn2an` 数字转中文 + 标点映射**：词典里含数字/英文的词（如 `μg`）必须在文本替换阶段处理，注入路径对其无效。
6. **英文缩写**：两个容器都装好了 `en_core_web_sm`，`_english_g2p()` 可正常返回；若镜像回退到无 spacy 模型版本，英文会被跳过（`❓`），新增依赖检查项。
7. **单页试听环境已具备**：API 容器 venv 内 misaki/kokoro/spacy/pypinyin 齐全，`HF_HOME=/opt/tts-models`，`POST /slides/{uid}/preview` 可直接用来验证词条效果。

## 4. 验证命令（复现）

```bash
# 基线
docker exec erp-ppt-video-worker-dev /app/.venv/bin/python -c "
from misaki.zh import ZHG2P
g = ZHG2P(version='1.1')
print(g('重楼')[0])"

# 注入后
docker exec erp-ppt-video-worker-dev /app/.venv/bin/python -c "
from misaki.zh import ZHG2P
g = ZHG2P(version='1.1')
from pypinyin import load_phrases_dict
load_phrases_dict({'重楼': [['chong2'], ['lou2']]})
print(g('重楼')[0])"
```