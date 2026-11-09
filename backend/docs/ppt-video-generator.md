# PPT 配音视频生成器（智能体模块）

把一份 `.pptx` + 逐页讲稿，批量合成「每页一张静帧 + 该页旁白」的 MP4，支持中英双语、
多音色、单页试听、渲染进度轮询，并把每页中间产物的 sha256 写进版本 manifest，
用于证明「片头/正文复用」是否成立（TC-006）。

讲稿不必先写：上传 PPT 后系统读取每页文字，由 AI 逐页生成讲稿**初稿**并默认填入，
用户进工作台直接改。已有讲稿（上传的、手改的）不会被覆盖，纯图片页留空待手填。

- 代码位置：`backend/app/modules/agent/`（API/服务/队列/渲染 worker/TTS）
- 前端位置：`frontend/src/app/(dashboard)/agent/ppt-videos/`、`frontend/src/components/agent/ppt-video/`
- 权限码：`agent:ppt-video:read`（看列表/详情/试听）、`agent:ppt-video:manage`（上传/改讲稿/渲染/删除）

---

## 1. 用户怎么用

1. 进入「智能体 → PPT 配音视频」（`/agent/ppt-videos`）。
2. 点「上传 PPT」：选 `.pptx`，逐页讲稿可选（上传即按「第 N 页」/空行/`---` 标记拆分）。
   上传时同步完成 **pptx 解析**：每页抽成页面图片、抽出页内文字与演讲者备注。
   解析完后台自动跑 **AI 讲稿初稿**（不阻塞上传响应）：以页内文字为主、备注作补充，
   按项目默认语言逐页写口播稿，**只写讲稿为空的页**；页内文字与备注都为空的页不发模型，
   在工作台标「本页无文字」。
3. 进入三栏工作台（`/agent/ppt-videos/<id>`）：
   - 左：页面时间轴（页码、时长、是否有讲稿/音频、`AI 初稿` / `本页无文字` 标签）
   - 中：当前页画面 + 讲稿编辑（语言 zh/en、音色、语速 0.5~2.0），可看讲稿来源
   - 右：属性、版本列表、manifest 抽屉
   - 顶部横幅：初稿生成进度（3 秒轮询详情）；部分失败或服务重启中断时可点「重新生成剩余页」
4. 「试听本页」：合成（或命中缓存）该页 wav，直接在页面播放；**不产生业务副作用**，但走 Server Action。
5. 「生成视频」：提交渲染任务，接口立刻返回 `202 + job_id`；`RenderProgress` 每 2s 轮询
   `GET /ppt-videos/{id}/job`，显示 queued/running/succeeded/failed 与失败原因。
6. 完成后在右侧版本面板看到新版本；点「复用记录」抽屉看每页 sha256 与是否命中缓存；
   点「下载/播放」取成片 MP4。

单页讲稿上限 2000 字符，PPT 上限 100MB，页数上限默认 60 页（可调，见第 5 节）。

---

## 2. 数据流

```
浏览器 ──Server Action──> POST /api/v1/agent/ppt-videos（multipart）
                              │
                              ├─ MinIO: ppt-video/{project}/source.pptx
                              ├─ soffice → pdf → pdf2image → 每页 PNG 入 MinIO
                              ├─ 解析每页文字/备注 + 可选讲稿拆分 → agent.ppt_video_slide
                              └─ commit 后 submit_job_safe("agent.ppt-video.script-ai")
                                       │
                         后台协程（core.jobs，非渲染 worker）
                                       ├─ 分批调 llm_client.chat_json（默认 6 页/批）
                                       ├─ 条件 UPDATE 只写空讲稿页，script_source=ai
                                       └─ script_ai_status: queued→running→done/partial/failed
POST .../render (202) ──> agent.ppt_video_job（queued）
                              │
        ppt-video-worker（独立容器，轮询队列）
                              ├─ 每页：TTS → wav（content-addressed）
                              ├─ 每页：ffmpeg 静帧+旁白 → 页片段 mp4
                              ├─ concat -c copy → 成片 MP4 → MinIO
                              └─ agent.ppt_video_version（含 manifest JSON）
```

API 与渲染彻底分离：API 侧不做 ffmpeg/LibreOffice，任何请求都不超过 5 秒；渲染在
`ppt-video-worker` 容器里跑（`PPT_VIDEO_WORKER_CONCURRENCY=1`）。

### 表（schema `agent`）

| 表 | 作用 |
|---|---|
| `ppt_video_project` | 项目主表：名称、源文件 sha256、页数、默认语言/音色、`body_input_key`、状态、AI 初稿状态/进度/错误 |
| `ppt_video_slide` | 每页：图片 key、讲稿（含来源 `script_source`：upload/ai/manual）、页内文字/备注、语言/音色/语速、音频 key/sha256/时长 |
| `ppt_video_segment` | 页片段缓存登记（按内容指纹，可跨项目复用） |
| `ppt_video_version` | 成片版本：version_no、head_key、body_key、manifest JSON、文件 sha256 |
| `ppt_video_job` | 渲染任务：status、attempt、progress、error、version_id |

迁移：

- `alembic/versions/0101_create_agent_schema_and_ppt_video_tables.py`（down_revision = `0100_safety_equipment_facility_hazards`）
- `alembic/versions/0102_agent_ppt_video_script_ai.py`：`ppt_video_project` 加 `script_ai_status` /
  `script_ai_error` / `script_ai_progress`，`ppt_video_slide` 加 `script_source`（upload/ai/manual）。
  历史项目取默认值（idle / 空来源），旧数据与渲染链路不受影响。

### 对象存储布局（全部服务端生成，禁止拼用户输入）

| key | 内容 |
|---|---|
| `ppt-video/{project_id}/source.pptx` | 原始上传文件 |
| `ppt-video/{project_id}/slides/{no:03d}.png` | 页面渲染图 |
| `ppt-video/audio/{audio_fp}.wav` | 旁白音频（内容寻址，跨项目共享） |
| `ppt-video/segments/{segment_fp}.mp4` | 页片段（内容寻址，跨项目共享） |
| `ppt-video/{project_id}/versions/v{no:04d}.mp4` | 成片 |

### 接口清单（`/api/v1/agent`）

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/voices` | read | 音色目录（含语言、许可） |
| GET | `/ppt-videos` | read | 列表（分页/搜索） |
| POST | `/ppt-videos` | manage | 上传 PPT + 可选讲稿；返回后自动后台生成初稿（响应结构不变） |
| GET | `/ppt-videos/{id}` | read | 详情（slides/versions/latest_job/body_stale/script_ai/page_images） |
| POST | `/ppt-videos/{id}/page-images` | manage | 重出页图（老项目回填 / 失败重试），**202 + job_id**；进度由前端轮下一个接口 |
| GET | `/ppt-videos/{id}/page-images/status` | read | 页图生成状态（status/progress/done/total/error/job_id），左栏进度条 2s 轮询 |
| POST | `/ppt-videos/{id}/script-ai?force=true` | manage | （重新）生成初稿，**只填空页**；`force` 默认 true（服务重启后强制重发），上传后的自动触发用 force=false 保证幂等，202 |
| DELETE | `/ppt-videos/{id}` | manage | 软删除（已生成文件保留） |
| PUT | `/ppt-videos/{id}/slides/{no}` | manage | 保存单页讲稿/语言/音色/语速/高亮样式与颜色/区域级高亮配置 |
| POST | `/ppt-videos/{id}/slides/{no}/preview` | manage | 单页试听（合成或命中缓存） |
| GET | `/ppt-videos/{id}/slides/{no}/image` | read | 页面图片 |
| GET | `/ppt-videos/{id}/slides/{no}/regions` | read | 区域设置面板数据：页面尺寸 + 可点选元素清单（id/类型/文本/EMU 坐标） |
| GET | `/ppt-videos/{id}/slides/{no}/audio` | read | 页面旁白 wav（支持 Range） |
| POST | `/ppt-videos/{id}/render` | manage | 提交渲染，**202 + job_id** |
| GET | `/ppt-videos/{id}/job` | read | 最近任务状态（轮询） |
| GET | `/ppt-videos/{id}/versions` | read | 版本列表 |
| GET | `/ppt-videos/versions/{vid}/manifest` | read | 复用记录 |
| GET | `/ppt-videos/versions/{vid}/file` | read | 成片 MP4（支持 Range）；`?inline=true` 供浏览器在线预览，默认仍是下载 |

响应统一信封 `{code, data, message, meta}`，`code=200` 表示成功。

### 在线预览

预览与下载**共用同一个端点**，只切换 `Content-Disposition`：`inline=true` 时 `inline; filename=...`，
否则 `attachment; filename=...`。Range/206/`Content-Range` 行为完全一致，播放器拖进度不受影响。

- 版本对象与项目摘要都带 `preview_url`（相对路径，经 `proxy.ts` 转发并带 cookie），前端不自己拼字符串。
- 列表页「预览」与工作台右栏常驻播放器都走这个 URL；弹窗用 `destroyOnHidden`，关闭即卸载 `<video>`、停掉请求。
- 「下载」按钮保留原 `download` 属性，语义不变（预览不会触发落盘）。
- 鉴权与下载同源，都是 `agent:ppt-video:read`。

### 页内视觉引导（讲到哪、亮到哪）

画面是同一张页图，按时间轴切换「压暗整页 + 还原命中框 + 描边」的静帧。三段契约：

**1）元素 id（`highlight.iter_elements`）**

| id | 含义 |
|---|---|
| `s0`、`s1` … | `layout.shapes` 里第 i 个顶层形状（文本框/图片/图表/组合/表格整表） |
| `s3.r2c1` | 第 3 个形状是表格时，其第 2 行第 1 列的单元格（行/列均从 1 起） |

id 由 layout 内序号**确定性生成**，不落库、不迁移历史 layout。表格单元格的几何在解析时按行列宽高累加算出
（python-pptx 的单元格没有 `left/top`），合并单元格只在合并起点出一条记录。组合形状按**整组外框**高亮——
组内子形状的坐标是组内坐标系，直接当页面坐标用会亮错位置。

**2）段级讲稿（`agent.ppt_video_slide.script_segments`）**

```json
[{"text": "本页讲的是发酵工艺流程", "targets": ["s2"]},
 {"text": "收率从 82% 提升到 91%", "targets": ["s5.r3c2"]}]
```

- 硬约束：各段 `text` 拼起来必须等于 `script_text`。渲染前做一致性校验，不一致（用户手改、回滚、换源）
  就整体作废、退回字面匹配，**不会按旧绑定亮错**。
- `targets` 由讲稿生成阶段产出，只允许取自该页的元素清单；服务端按白名单二次校验，模型编的 id 直接丢弃。
- `script_text` 仍是唯一真相：编辑器、缓存指纹、TTS 输入全部读它，段结构只是它的附加注记。

**3）时间轴口径**

- 段数 > 1 且 `AGENT_PPT_VIDEO_SEGMENT_TTS_ENABLED=true` 时逐段合成：页音频 = 各段音频按序拼接，
  段间插入 `AGENT_PPT_VIDEO_SEGMENT_PAUSE_MS`；每段的 `start/end` 就是它在成片里的真实位置，
  不再按字数估算（末段吃掉取整余数，保证 `sum(段) + head + tail == 页音频时长`）。
- 单段高亮不足 `AGENT_PPT_VIDEO_HIGHLIGHT_MIN_DWELL_MS` 时并入相邻段（只合并帧时长与高亮框，不重合成音频）。

**4）样式档位（`AGENT_PPT_VIDEO_HIGHLIGHT_STYLE`）**

| 样式 | 效果 | 生效参数 |
|---|---|---|
| `text_recolor`（默认） | 命中**文字**染成主色、背景不压暗、**不画矩形框**；图片/图表/表格整表只叠淡色底，不染色也不描边 | `_COLOR` / `_FILL_ALPHA` / `_RECOLOR_STRENGTH` |
| `dim_outline` | 整页压暗 + 命中框还原亮度 + 描边 | `_COLOR` / `_DIM_ALPHA` / `_OUTLINE_PX` |
| `dim` | 仅压暗 | `_DIM_ALPHA` |
| `outline` | 仅描边 | `_COLOR` / `_OUTLINE_PX` |

文字染色在命中框内按亮度生成软遮罩，并以「占面积更小的一侧」判定前景，因此浅底深字与深底浅字都成立；
对比度太低（纯色块、照片）时自动放弃染色，不会把整块染红（`text_recolor` 档也不再补描边）。
分流依据是元素类型（`highlight.HighlightBox.kind`），所以同一段里「文字变红 + 图片淡色底」可以并存。页级可在编辑区覆盖样式与颜色
（`agent.ppt_video_slide.highlight_style` / `highlight_color`，空 = 跟随模块设置），样式参数整体并入视觉指纹，
改颜色或强度会让旧片段失效重出。

**5）区域级配置（`agent.ppt_video_slide.highlight_regions`）**

整页一套样式不够用时逐个区域指定，优先级 **句级/区域级 > 页级 > 模块设置**：

```json
{
  "regions": [
    {"id": "s2", "mode": "text"},
    {"id": "s5.r3c2", "mode": "area", "color": "#FF3B30", "fill_alpha": 90},
    {"id": "s7", "mode": "off"},
    {"id": "rect:0", "mode": "area", "rect": {"x": 0.12, "y": 0.3, "w": 0.4, "h": 0.18}, "shape_sha": "9f3c…"}
  ],
  "sentences": [{"text": "本页讲的是发酵工艺流程", "targets": ["s2"], "mute": ["s7"]}]
}
```

| mode | 效果 |
|---|---|
| `text` | 只给该区域的文字染色（`color` 可覆盖页级主色） |
| `area` | 给整块区域铺底色，`fill_alpha`（0-255，默认 90）控制深浅，文字仍可读 |
| `off` | 该区域**永不**高亮，自动绑定上了也不亮 |

- 元素区域只存 id，坐标渲染时按 layout 现算，换分辨率不会偏；解析不出的地方用 `rect:N` 手绘矩形兜底，
  坐标是**相对整页的比例**，并记录画框时的页图 `shape_sha` —— 页图变了这条框会被标「待复核」，不会静默套到错位置。
- 手绘矩形默认整页常亮（画了就是希望它亮），某句 `mute` 里点名才跳过；它属于「人工指定」，不参与下面的自动兜底。
- 句级微调按「去空白去标点」的文本匹配，手改讲稿只动了别的句子或标点时规则仍在；整句被改没则退回自动绑定。
- 落库前按 layout 白名单校验：元素 id 查不到、mode 非法、矩形出界、颜色非 `#RRGGBB`、`fill_alpha` 越界，一律丢弃或夹紧。
- 区域三态/颜色/底色透明度全部并入视觉指纹，改任何一项都会让旧片段失效重出。

**兜底链（每句必有高亮）**

`highlight.boxes_for_segment_with_source()` 按顺序取第一个非空结果，并把来源写进
`HighlightStep.fallback`（只做标注与日志，**不进视觉指纹**，避免无意义的缓存失效）：

| 顺序 | 来源 | `fallback` | 说明 |
|---|---|---|---|
| 1 | 模型/人工绑定的元素 | `target` | 白名单校验，查不到的 id 直接丢弃 |
| 2 | 字面 bigram 覆盖率 ≥ 阈值 | `text` | 阈值 `AGENT_PPT_VIDEO_HIGHLIGHT_TEXT_MATCH_COVERAGE`（默认 0.6） |
| 3 | 本页未关闭元素中字面得分最高者（≥ 0.2） | `guess` | 允许猜错，但必须在面板里标「兜底」 |
| 4 | 整页框 + 极低透明度铺底（`fill_alpha=18`） | `page` | 纯图片页也能看到变化 |
| — | 句级 `mute` / 区域 `off` | 空 | 用户显式决定优先级最高，任何兜底不得覆盖 |

- `off` 只作用于被关掉的那个元素，**不会**让本页其它句子失去高亮；`guess` 候选也已排除 `off` 元素。
- 句级面板对 `guess` / `page` 打「兜底」标签，并提供「这句不亮」把整句写入 `mute: ["*"]` 立刻退出兜底。
- 讲稿生成后用 `script_ai._backfill_targets()` 本地补 targets（不额外调 LLM）；worker 出帧后按页记录兜底段数
  （`fallback usage` 日志），便于验收「兜底比例」。

**降级矩阵**

| 情况 | 行为 |
|---|---|
| 高亮关闭 / 逐段合成关闭 | 整页单段合成 + 旧的字数加权时间轴（与改造前完全一致） |
| 讲稿被手改（段结构与文本不一致） | 按标点重切、无绑定，退回字面匹配（覆盖率阈值 `AGENT_PPT_VIDEO_HIGHLIGHT_TEXT_MATCH_COVERAGE`） |
| 模型给了不存在的元素 id | 丢弃该 target；回落到字面匹配 → guess → page |
| 区域配置里的元素 id 在 layout 里查不到 | 保存时丢弃该条；渲染时再查不到就跳过，不亮也不报错 |
| 该页 layout 为空（纯图片页） | 只保留结构合法的配置，不因「校验不出」把人工设置清空 |
| 某一段合成/拼接失败 | `logger.exception` 后整页单段重新合成，单页问题不影响整条视频 |
| 一段都命中不了 | 该句走整页淡底（`fallback=page`），不再出现「读到却没反应」 |

---

## 3. 复用口径（TC-006 取证）

复用判定的唯一真相是**内容指纹**（`app/modules/agent/cache.py`），不是时间戳、不是「改没改」：

| 指纹 | 计算输入 |
|---|---|
| `script_key` | `语言 + 规范化讲稿`（行尾空白/全角空格/连续空行归一） |
| `voice_key` | `引擎@引擎版本 + 语言 + 音色 + 语速(2位小数)` |
| `audio_key` | `script_key + voice_key (+ 分段变体)` → wav 路径；分段变体 = 段边界 + 段间停顿，整页合成时为空（与改造前一致） |
| `segment_audio_key` | `语言 + 规范化段文本 + voice_key` → 段级 wav 路径（改一句只重合成那一句） |
| `segment_key` | `页图 sha256 + audio_key + ENCODER_KEY + 视觉指纹` → 页片段 mp4；视觉指纹含分段/时间轴/targets/高亮框/样式/表格行列几何 |
| `head_key` | 第 1 页的 `segment_key` |
| `body_key` | 第 2~N 页 `segment_key` 的**有序**哈希 |
| `slide_input_key` / `body_input_key` | 仅讲稿+语音参数（不含页图），用于渲染前判断 `body_stale` |

`ENCODER_KEY = "h264-1920x1080-30-yuv420p-aac48000-128k"`：任何编码参数变更必须同步改这个常量，
否则旧片段会被错误复用（画面/音轨参数不一致会导致 `-c copy` 拼接后花屏或静音）。

**「只改首页」为什么能证明片头/正文分离**：改首页讲稿 → 第 1 页 `segment_key` 变 → `head_key` 变；
第 2~N 页输入没变 → `body_key` 完全不变。因此：

- 版本详情里 `head_key` 不同、`body_key` 相同 ⇒ 只重渲了片头，正文全部复用；
- 反之 `body_key` 变了 ⇒ 正文有页真的重渲了。

### manifest 结构（写入 `ppt_video_version.manifest`）

```json
{
  "version": 1,
  "project_id": "…",
  "encoder_key": "h264-1920x1080-30-yuv420p-aac48000-128k",
  "head_key": "…",
  "body_key": "…",
  "total_duration_ms": 183420,
  "reuse": {
    "total_slides": 12, "reused_slides": 11, "rendered_slides": 1,
    "body_reused_slides": 11, "body_rendered_slides": 0, "head_reused": 0
  },
  "slides": [
    {
      "slide_no": 1,
      "image_sha256": "…", "audio_sha256": "…", "segment_sha256": "…",
      "duration_ms": 15300, "cache_hit": false
    }
  ]
}
```

**人工核对步骤（TC-006）**

1. 打开项目 → 生成 v1 → 在版本面板拉 manifest，记下 `head_key`、`body_key`、`slides[*].segment_sha256`。
2. 只改第 1 页讲稿（或只换第 1 页音色）→ 再生成 v2。
3. 对比 v2 manifest：`head_key` 变、`body_key` 不变、第 2~N 页 `segment_sha256` 与 `cache_hit=true` 全一致。
4. 若第 3 步不成立，先查：讲稿规范化是否被绕过（前端是否传了不同的空白/换行）、语音参数是否也变了、
   是否动过 `ENCODER_KEY`。

`body_stale`（详情接口返回的布尔）是「渲染前预判」：项目当前 `body_input_key` 与上次渲染时记录的不一致，
说明正文有页讲稿/语音参数变了但还没重渲。它只看输入，不看页图。

---

## 4. 运行方法

### 4.1 系统依赖（两个镜像都要，必须保持一致）

页图（编辑态底图）由 **backend 进程**（`core.jobs`）生成，成片由 **worker** 渲染 —— 两边字体或
转换参数不同，就会出现「预览和成片画面不一样」。所以 `backend/Dockerfile` 与 `backend/Dockerfile.worker`
都要装同一套依赖，且都在构建期做 `fc-match` 自检（不通过直接构建失败）：

| 依赖 | 用途 | 缺了会怎样 |
|---|---|---|
| `libreoffice-impress` + `libreoffice-core` | pptx → pdf | 上传后解析失败 |
| `poppler-utils`（`pdf2image` 调用） | pdf → PNG | 同上 |
| `ffmpeg` / `ffprobe` | 静帧+旁白 → mp4、拼接、探时长 | 渲染失败（仅 worker） |
| `fonts-noto-cjk` / `fonts-noto-cjk-extra` | 中文字体 | **整屏方块**（构建期 `fc-match` 自检会拦） |
| `fonts-liberation` / `fonts-crosextra-carlito` / `fonts-crosextra-caladea` | Arial / Times New Roman / Calibri / Cambria 的**度量兼容**替身 | 拉丁文本提前折行压住下方元素（见下） |
| `assets/fontconfig/69-ppt-font-alias.conf` | 把「微软雅黑 / 宋体 / 思源黑体」映射到 Noto | **文字重叠、表格跑位**（见下） |

#### 字体别名（`69-ppt-font-alias.conf`）

PPT 里声明的 `微软雅黑`、`宋体`、`思源黑体 CN` 等字体在容器里没有文件。不加别名时 fontconfig 会把它们
判给 `DejaVuSans.ttf`（**无中文字形**），渲染时再逐字形回退到 Noto：同一个文本框里中文走 Noto、英文与
数字走 DejaVu，两侧字宽度量不同 → 文字互相压住、表格列被挤跑。归因数据见
[`ppt-video-font-attribution.md`](ppt-video-font-attribution.md)。

- 只做**族名映射**，不 COPY 商业字体文件（雅黑/宋体授权不允许分发），Noto 为 SIL OFL 可再分发。
- 规则统一用 `qual="first"`：`qual="any"` 会连带匹配 `45-latin.conf` 展开的弱别名链
  （其中含 `Microsoft YaHei`），把 Arial / Calibri 也改写成 Noto，英文版式反而更差。
- 拉丁侧不靠 fontconfig 硬改，靠**装度量兼容字体包**（Liberation / Carlito / Caladea），
  fontconfig 自带的 `30-metric-aliases.conf` 会把 Arial→Liberation Sans、
  Times New Roman→Liberation Serif、Calibri→Carlito 自动接上。
- 构建期自检：中文族名必须命中 `Noto *`，且 `Arial`/`Times New Roman`/`Calibri` 必须分别命中
  `Liberation Sans`/`Liberation Serif`/`Carlito`；不满足即构建失败。

#### 渲染管线指纹与缓存失效

改字体或拆图参数后，旧 PDF 与旧页图在画面上已经不对，必须判过期：

- `app/modules/agent/render.py` 的 `RENDERER_KEY`（当前 `r2-noto-liberation-v1`）= 版本号 + 字体档位；
  **改字体映射或拆图参数时必须递增**。
- 中间 PDF 的 key 带有这个指纹：`ppt-video/pdf/{RENDERER_KEY}/{sha256}.pdf`，旧对象自然不再命中
  （不删旧对象，MinIO 删除不可回滚，历史成片仍依赖旧页图尺寸）。
- `ppt_video_project.page_images_renderer` 记录页图是哪个指纹渲染的；与 `RENDERER_KEY` 不一致即视为
  过期。过期后的重出图入口有三个：换源/页内编辑（`apply_source_replace` 自动投递）、页图失败态里的
  「重试」、渲染成片（worker 用同一个 `page_images_fresh` 判断，所以不会出现「预览旧字体、成片新字体」）。
  单纯打开老项目不会自动重出图，左栏保持「待渲染」占位。
- 页图任务与 worker 的 `_resolve_slide_images` 共用 `ensure_source_pdf` + `render_pdf_pages`，
  字体与转换参数天然一致。

#### 页图进度语义

进度写在项目行上（`page_images_status/progress/done/total/error/job_id`），由页图任务用独立会话单条
`UPDATE` 写入，不参与调用方事务：

| 阶段 | `progress` | `done` |
|---|---|---|
| 投递（`mark_page_images_queued`，随请求事务提交） | 0 | 0 |
| soffice 转 PDF | 0 → 40 | 0 |
| 逐页拆图 | 40 → 85 | 1 → total |
| 编码上传（PNG/preview/thumb） | 85 → 99 | 保持 total |
| 落库收尾（`_commit`） | 100 | total |

- `done` 只增不减。上传段只推进百分比、不回写计数：若按「已上传页数」写，前端会看到
  `53 → 1` 的倒退（2026-11-03 真机实测 88% 时 `done` 从 53 掉到 11），已有用例
  `test_progress_done_never_regresses_across_upload_phase` 守住。
- `queued` 在**投递前**由请求自己的事务写（`mark_page_images_queued`）：上传返回的详情、换源/重试后的
  首次状态查询都能看到「排队中」，前端据此立刻开始轮询。不能放到后台会话里写——那时调用方事务还没
  提交，独立会话的 `UPDATE` 会命中 0 行。
- `queued` 超过 2 分钟、`running` 超过 30 分钟没有推进，读接口按 `failed` 返回并提示重试
  （`PAGE_IMAGES_QUEUE_STALE_SECONDS` / `PAGE_IMAGES_STALE_SECONDS`），避免进度条永远转。
- 成片渲染自己产出一套页图时（`worker._resolve_slide_images`）会顺带把状态置为 `done/100`，
  避免并发的页图任务被杀后左栏一直转。

### 4.2 启动 worker

```bash
# 必须限资源（本机是共用服务器）
cd backend
docker buildx build --memory=4g --cpu-quota=200000 -f Dockerfile.worker -t erp-backend-worker .

# 或直接用 compose（服务名 ppt-video-worker / 容器 erp-ppt-video-worker）
docker compose up -d ppt-video-worker
docker logs -f erp-ppt-video-worker
```

worker 启动时自检 `ffmpeg`/`ffprobe`/`soffice` 是否在 PATH，缺了立刻报
「渲染环境缺少必要工具：…请使用 Dockerfile.worker 构建的 worker 镜像」。

### 4.3 数据库与配置

```bash
cd backend
uv run alembic upgrade head   # 至少到 0096（agent schema + AI 初稿字段）
```

运行时配置在 `core.module_settings`（模块 `agent`），Web 端改完**下一个任务即生效**（每个任务
`load_settings()` 重新读库），不用重启容器。

| 键 | 默认 | 说明 |
|---|---|---|
| `AGENT_PPT_VIDEO_DEFAULT_LANGUAGE` | `zh` | 新建项目默认语言 |
| `AGENT_PPT_VIDEO_DEFAULT_VOICE_ZH` | `zf_001` | 中文默认音色 |
| `AGENT_PPT_VIDEO_DEFAULT_VOICE_EN` | `af_bella` | 英文默认音色 |
| `AGENT_PPT_VIDEO_DEFAULT_SPEED` | `1.0` | 默认语速（0.5~2.0，越界被夹回） |
| `AGENT_PPT_VIDEO_HEAD_PADDING_MS` | `300` | 页首静音（留白） |
| `AGENT_PPT_VIDEO_TAIL_PADDING_MS` | `500` | 页尾静音（读完再切页） |
| `AGENT_PPT_VIDEO_MAX_SLIDES` | `60` | 最大页数 |
| `AGENT_PPT_VIDEO_JOB_TIMEOUT_SECONDS` | `1800` | 单任务超时 |
| `AGENT_PPT_VIDEO_TTS_ENGINE` | `kokoro` | `kokoro` / `melo` |
| `AGENT_PPT_VIDEO_FFMPEG_THREADS` | `2` | 单页编码线程（共用服务器别调大） |
| `AGENT_PPT_VIDEO_RENDER_DPI` | `150` | PDF 转图 DPI |
| `AGENT_PPT_VIDEO_MAX_ATTEMPTS` | `3` | 失败重试上限 |
| `AGENT_PPT_VIDEO_SCRIPT_AI_ENABLED` | `true` | 上传后是否自动生成逐页讲稿初稿 |
| `AGENT_PPT_VIDEO_SCRIPT_AI_BATCH_SIZE` | `6` | 每批页数（一次 LLM 调用），夹在 1~20 |
| `AGENT_PPT_VIDEO_SCRIPT_AI_TIMEOUT_SECONDS` | `90` | 单批硬超时（`asyncio.wait_for`），最小 10 |
| `AGENT_PPT_VIDEO_SCRIPT_AI_MAX_PAGE_TEXT_CHARS` | `2000` | 喂给模型的单页文字截断长度，最小 200 |
| `AGENT_PPT_VIDEO_PAGE_CONCURRENCY` | `2` | 渲染时同时处理的页数，夹在 1~3（共用服务器，别超过 3） |
| `AGENT_PPT_VIDEO_TTS_CONCURRENCY` | `2` | 同页内并发合成的段数，夹在 1~4；任一段失败仍回退整页合成 |
| `AGENT_PPT_VIDEO_PDF_SPLIT_BATCH` | `8` | 页图拆图每批页数，夹在 1~32；越大进程越少、内存越高 |

种子脚本：`backend/scripts/seed/seed_module_settings.py`。

### 4.4 TTS 权重

- 模型下载默认走 `HF_ENDPOINT`（compose 里默认 `https://hf-mirror.com`，**huggingface.co 在厂区内网不可达**）。
- 需要完全离线：构建时加 `--build-arg PRELOAD_TTS_MODELS=true`，权重烤进镜像 `/opt/tts-models`（`HF_HOME`）。
  预下载脚本 `scripts/ci/preload_tts_models.py` 会按固定 revision 拉取并**逐文件校验 sha256**，
  任何一个不符即构建失败。
- 运行时 `KPipeline(repo_id=…)` 不带 revision 参数，命中本地缓存即为钉住的版本；
  若要求「运行时也绝不联网」，在 worker 上额外设 `HF_HUB_OFFLINE=1`（当前默认未设）。

### 4.5 英文 G2P（spaCy 模型）

Kokoro 的英文 G2P 依赖 spaCy 的 `en_core_web_sm`，它**不在 PyPI 上**。构建期由
`scripts/ci/install_spacy_en_model.py` 装好：优先 GitHub Release 的 3.8.0 wheel（sha256 钉死），
失败回退 hf-mirror 上的 3.7.1 wheel（sha256 钉死）。两条都失败 → **构建失败**，
不会产出「英文配音静默不可用」的镜像。

### 4.6 并发与耗时

共用服务器，峰值按 **2-3 核** 设计，所有并发度都可回退到 1（等价于改造前的串行路径）。

| 位置 | 做法 | 控制项 |
|---|---|---|
| 成片渲染 | 页级流水线：并发做「合成音频 + 出帧编码 + 上传」（纯计算/网络，不碰 DB），回到主协程串行查缓存、落库 | `AGENT_PPT_VIDEO_PAGE_CONCURRENCY` |
| 页内旁白 | 段级并发合成，任一段失败回退整页单段合成 | `AGENT_PPT_VIDEO_TTS_CONCURRENCY` |
| 帧编码 | 高亮帧 PNG `compress_level=1`（原来是 `optimize=True` 的 zlib 9），concat 只认 `duration` 指令，与帧格式无关 | 常量 `FRAME_PNG_COMPRESS_LEVEL` |
| 底图 | 同页多帧只解码一次（`compose_highlight_frame(base_image=...)`） | — |
| 页图拆图 | `pdftoppm` 分批调用（53 页从 53 个进程降到约 7 个），每批上报一次进度 | `AGENT_PPT_VIDEO_PDF_SPLIT_BATCH` |
| 页图产物 | 原图 PNG `compress_level=3`（无损）；预览 JPEG 关 `optimize/progressive`；三份产物 + 多页上传并发 | `AGENT_PPT_VIDEO_PAGE_CONCURRENCY` |

**并发安全**：`AsyncSession` 严禁并发使用 —— 所有 DB 读写留在主协程串行，并发只包住纯计算与存储 IO；
MinIO 客户端线程安全，上传走线程池。任一页并发任务异常即回退串行重跑该页，不让整条视频失败。

**缓存口径不变**：`ENCODER_KEY` / `RENDERER_KEY` 均不改动 —— PNG 压缩级别不改变像素，不构成画面变化；
只有字体或拆图参数变了才需要递增。

**耗时怎么量**（同一份 53 页样本，`AGENT_PPT_VIDEO_PAGE_CONCURRENCY=1` 与 `2` 各跑一次）：

```bash
# 1) 页图阶段：上传后到 page-images/status=done 的墙钟时间，并采样峰值 CPU
docker stats --no-stream erp-ppt-video-worker
# 2) 成片阶段：render 提交到 job=success 的墙钟时间，按页看耗时与兜底统计
docker logs -f erp-ppt-video-worker 2>&1 | grep -E "页渲染完成|高亮兜底命中"
```

对比时只看**同一台机、同一份样本、同一 DPI** 的墙钟时间与 `docker stats` 的 CPU% 峰值；
并发 2 的墙钟应明显低于并发 1，CPU 峰值不得持续超过 3 核。

---

## 5. 版本、来源与商用许可

版本为构建时的实际口径（Debian bookworm 当前候选版本；以镜像内 `ffmpeg -version` / `soffice --version` 为准）。

| 组件 | 版本 | 来源 | 许可 | 商用注意 |
|---|---|---|---|---|
| ffmpeg | 5.1.9 | Debian bookworm（`mirrors.ustc.edu.cn`） | 主体 LGPL-2.1+；本镜像启用 `libx264`（GPL-2.0+） | 内部使用无义务；若把镜像/二进制对外分发，需按 GPL 提供对应源码 |
| LibreOffice Impress | 7.4.7 | Debian bookworm | MPL-2.0 | 可用于闭源产品，修改其源码才需开源修改部分 |
| poppler-utils | 22.12.0 | Debian bookworm | GPL-2.0/3.0 | 以独立可执行文件调用（`pdftoppm`），不链接，不触发传染；对外分发镜像需附许可声明 |
| pdf2image | 随主锁文件 | PyPI | MIT | 无 |
| fonts-noto-cjk | 20220127 | Debian bookworm | SIL OFL 1.1 | 允许随成品视频嵌入与再分发 |
| Kokoro-82M（en，v1.0） | rev `f3ff3571791e39611d31c381e3a41a3af07b4987` | huggingface.co/hexgrad/Kokoro-82M | Apache-2.0 | 可商用；保留 NOTICE/许可文本 |
| Kokoro-82M（zh，v1.1-zh） | rev `01e7505bd6a7a2ac4975463114c3a7650a9f7218` | huggingface.co/hexgrad/Kokoro-82M-v1.1-zh | Apache-2.0 | 同上 |
| kokoro (pip) | 0.9.4 | PyPI | Apache-2.0 | 无 |
| misaki | 0.9.4 | PyPI | Apache-2.0 | 无 |
| soundfile | 0.13.1 | PyPI | BSD-3-Clause | 无 |
| torch | 由 kokoro 求解（CPU 轮子） | PyPI | BSD-3-Clause | 无 |
| spaCy / en_core_web_sm | 3.8.18 / 3.8.0 | PyPI / GitHub Release | MIT | 无 |
| jieba | 随 misaki[zh] | PyPI | MIT | 无 |
| espeak-ng | 随 misaki[en]（`espeakng-loader`） | PyPI wheel | GPL-3.0 | 仅作 OOD 词回退，未修改；内部使用无义务，对外分发镜像需附 GPL 声明 |
| MeloTTS（可选兜底） | 未装（`tts_engine=melo` 时才需要） | GitHub | MIT | 无 |

权重文件 sha256（前 8 位，完整值见 `app/modules/agent/tts_assets.py`）：

| 文件 | sha256 前缀 |
|---|---|
| `kokoro-v1_0.pth` | `496dba11` |
| `kokoro-v1_1-zh.pth` | `b1d8410f` |
| `voices/af_bella.pt` | `8cb64e02` |
| `voices/zf_001.pt` | `9bdc9a87` |

音色与许可：`GET /voices` 直接返回每条音色的语言与许可字段；9 条目录见 `app/modules/agent/voices.py`
（中文 `zf_001/002/003/017`、`zm_010`；英文 `af_bella`、`bf_emma`、`am_michael`、`bm_george`）。

---

## 6. 已知限制 / 踩过的坑

1. **`Dockerfile.dev` 没有 LibreOffice**：在后端 dev 容器里调渲染接口一定失败，别拿它验证 TC-003。
2. **中文讲稿里的英文缩写**：不加 `en_callable` 时 misaki 的拼音 G2P 会把 `GMP`/`HPLC`/`API`
   直接丢成占位符（实测音素串里是 `❓`）。`tts.py` 已注入英文 G2P（`_english_g2p()`），
   缺 `en_core_web_sm` 时降级为「跳过英文」并打 WARNING，不阻塞中文合成。
3. **首块延迟 ≈ 整段合成耗时**：当前按整段文本合成后一次性写 wav，`KPipeline` 对短讲稿只返回一个 chunk，
   没有流式切片，所以「首块」不等于「更低延迟」。单页长讲稿的进度只能靠任务级轮询。
4. **大 MP4 走 `proxy.ts`（`NextResponse.rewrite`）**：后端 `.../file` 与 `.../audio` 都支持 Range，
   播放器拖动依赖 rewrite 的流式转发。若出现拖动失败/无法续传，先用 nginx 直连后端复测，
   再考虑在代理层显式透传 `Range`/`Content-Range`（本轮未改 `proxy.ts`）。
5. **磁盘**：页片段与音频是内容寻址、跨项目复用，但会持续增长；共用服务器上仍需定期
   `docker system prune` + 清理 MinIO 中已删项目的对象。
6. **单任务并发为 1**（`PPT_VIDEO_WORKER_CONCURRENCY=1`）：多个项目同时点生成会排队，
   不要靠「多开 worker」提吞吐，先看 CPU 与内存。
7. **样例数据清理**：本地验证若建了临时库（如 `erp_test_agent`），用完记得 drop。
8. **AI 初稿只认全局激活的文本模型**：`llm_client` 没有「按调用选模型」的能力，所以初稿质量与
   `AI_MODEL_*` 里激活的那套配置一致，不要指望在 agent 模块单独配模型名。
9. **初稿是后台任务，服务重启会中断**：状态可能停在 `running`（横幅一直显示生成中）；点
   「重新生成剩余页」会带 `force=true` 重新投递——只填空页，已写入的内容不会被覆盖。
10. **AI 只依据页内文字与备注**：纯图片/扫描页没有文字，不会生成（时间轴标「本页无文字」）；
    若需要这类页也有初稿，得先加 OCR，属于后续需求。

---

## 7. 自检 / 测试

```bash
cd backend
FEISHU__PLATFORM__APP_ID=test FEISHU__PLATFORM__APP_SECRET=test FRONTEND_URL=http://localhost:3000 \
  uv run pytest tests/modules/agent -q          # 含 test_script_ai.py（纯函数用例不需要数据库）
uv run ruff check app tests
uv run mypy app
uv run python scripts/ci/check_permissions.py
uv run python scripts/ci/export_openapi.py      # 之后重生成前端类型
```

数据库相关用例需要可连接的 PostgreSQL（默认读 `DATABASE_URL`）。若某环境的
`alembic_version` 停在 `0094_sync_doc_gen_cache_comments`（该迁移只存在于未合并的
`feature/liujunguang_R&D` 分支，main 里没有这个文件），从 main 升级会报
`Can't locate revision identified by '0094_sync_doc_gen_cache_comments'`，处理方式：

```bash
uv run alembic current                          # 确认停在 0094
uv run alembic stamp 0093_quality_qms_deviation_flow_tables
uv run alembic upgrade head                     # 0093 → 0096
```

（该路径已在独立临时库上从零验证：0001 → 0095 全程通过，单 head；0096 为单列新增。）

TTS 主观听感与耗时数据见 `backend/docs/ppt-video-tts-poc.md`。