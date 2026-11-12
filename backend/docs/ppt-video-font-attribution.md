# PPT 页图渲染失真归因（字体 / 文字重叠 / 表格跑位）

本文件记录「PPT 配音视频」页图失真的归因过程、实测数据与修复结论。
归因工具：`backend/scripts/test/diagnose_ppt_fonts.py`（只读，不改库、不写对象存储）。

## 结论（先看这里）

1. **主因：中文族名没有映射。** PPT 里声明的「微软雅黑 / 宋体 / 华文细黑 / 黑体 / 思源黑体 CN /
   方正兰亭 / 新細明體 / MiSans」在容器里没有字体文件，fontconfig 一律判给 `DejaVuSans.ttf`——
   该文件**没有中文字形**，soffice 只能逐字形回退到 Noto CJK。结果是同一行里拉丁字符用 DejaVu 的
   度量、汉字用 Noto 的度量，字宽/行高不一致 → 文字互压、标题折行、表格列被挤跑。
   修复：`backend/assets/fontconfig/69-ppt-font-alias.conf` 做族名改写（只改映射，不分发商业字体）。
2. **次因：拉丁族名同样落到更宽的 DejaVu。** `Arial`→DejaVu Sans、`Times New Roman`→DejaVu Serif
   都比原字体宽，文本提前折行并压住下方元素。最直接的证据是同页标题：
   修复前 `公司组织架构图 Company Organization Chart` 折成两行、`Chart` 压住「法定代表人」方框；
   装上度量兼容字体后回到源 PPT 的单行版式。
   修复：两个镜像都装 `fonts-liberation` / `fonts-crosextra-carlito` / `fonts-crosextra-caladea`，
   由 fontconfig 自带的 `30-metric-aliases.conf` 接上 Arial→Liberation Sans、
   Times New Roman→Liberation Serif、Calibri→Carlito、Cambria→Caladea。
3. **例外：嵌入的 Visio 对象（EMF 回退图）无法靠字体修复。** 53 页项目的第 32 页是一张
   `progId="Visio.Drawing.11"` 的 OLE 对象，容器里没有 Visio，soffice 只能渲染它的
   **EMF 回退图**，EMF 内的文本记录按原字体度量定位，换字体后逐行挤在一起。该页仍有 80 处重叠，
   本轮不处理，规避办法见文末。

## 归因方法

脚本做四件事，全部只读：

1. 解析 pptx 里声明的字体：`ppt/slides|slideLayouts|slideMaster` 的 `a:latin/a:ea/a:cs typeface`，
   外加主题 `<a:font script="Hans|Hant">` 占位（`a:majorFont/a:ea` 常为空串，真实中文字体藏在
   script 映射里，漏掉它就会漏掉元凶）。
2. 逐字体 `fc-match -f "%{family}|%{file}"`，并用 `fc-list :lang=zh-cn` 判断命中文件是否真含中文字形。
3. 用与生产完全相同的 `soffice` invoke 方式（独立 `UserInstallation`）转 PDF，`pdfinfo` 记录页尺寸
   （验证没有被拉伸：16:9 均为 960×540pt → 150dpi 下 2000×1125px）。
4. `pdftoppm -singlefile -f n -l n` 逐页导出 PNG 供目视比对，并用 `pdftotext -bbox` 做同行词框
   重叠检测（判定阈值按字高比例，见脚本内注释）。

复现（容器内跑，字体环境必须与镜像一致）：

```bash
docker run --rm --network livzon-syntpharm_default --env-file /tmp/worker.env \
  -v /tmp/diag:/tmp/diag \
  -v "$PWD/backend/scripts/test/diagnose_ppt_fonts.py":/tmp/diag.py:ro \
  -v "$PWD/backend/app":/app/app:ro \
  -v "$PWD/backend/assets/fontconfig/69-ppt-font-alias.conf":/etc/fonts/conf.d/69-ppt-font-alias.conf:ro \
  livzon-syntpharm-ppt-video-worker:dev \
  sh -c 'fc-cache -f >/dev/null; cd /app && PYTHONPATH=/app .venv/bin/python /tmp/diag.py \
         --project-id <project-uuid> --out /tmp/diag > /tmp/diag/report.md'
```

被诊断的两个项目（同一套业务数据，16:9）：

| 项目 | id | 页数 | 特点 |
|---|---|---|---|
| 深圳致君（头孢呋辛钠…） | `4eefe2a8-c7a7-4c83-8a9e-6e44e75ce001` | 53 | 字体最杂（19 个族名），含 Visio OLE 页 |
| 有限空间作业安全培训 | `8174af86-c05e-4ed9-ab2c-7aeaffea7a60` | 32 | 版式层用 Calibri / Calibri Light，中文用 MiSans |

## 证据 1：声明字体 → 实际命中

### 修复前（基线镜像）

| PPT 声明字体 | 命中 family | 命中文件 | 含中文字形 | 需要中文 | 判定 |
|---|---|---|---|---|---|
| 微软雅黑 | DejaVu Sans | `DejaVuSans.ttf` | 否 | 是 | ✗ |
| 宋体 | DejaVu Sans | `DejaVuSans.ttf` | 否 | 是 | ✗ |
| 华文细黑 | DejaVu Sans | `DejaVuSans.ttf` | 否 | 是 | ✗ |
| 黑体 | DejaVu Sans | `DejaVuSans.ttf` | 否 | 是 | ✗ |
| 思源黑体 CN Regular | DejaVu Sans | `DejaVuSans.ttf` | 否 | 是 | ✗ |
| Songti SC | DejaVu Sans | `DejaVuSans.ttf` | 否 | 是 | ✗ |
| 新細明體（theme Hant） | DejaVu Sans | `DejaVuSans.ttf` | 否 | 是 | ✗ |
| MiSans Demibold / Normal | DejaVu Sans | `DejaVuSans.ttf` | 否 | 是 | ✗ |
| Arial / Times New Roman / Calibri | DejaVu Sans / Serif | `DejaVu*.ttf` | 否 | — | 宽度偏大 |

声明次数（53 页项目）：微软雅黑 97 处、宋体 89 处、华文细黑 22 处、方正兰亭系 5 处、思源黑体 2 处；
32 页项目：宋体 40 处、MiSans 34 处、Calibri 系 104 处。

### 修复后（本仓库镜像）

| PPT 声明字体 | 命中 family | 含中文字形 | 判定 |
|---|---|---|---|
| 微软雅黑 / Microsoft YaHei(UI) | Noto Sans CJK SC | 是 | ✓ |
| 华文细黑 / 黑体 / 思源黑体 CN / 方正兰亭* | Noto Sans CJK SC | 是 | ✓ |
| MiSans Demibold / MiSans Normal | Noto Sans CJK SC | 是 | ✓ |
| 宋体 / Songti SC | Noto Serif CJK SC | 是 | ✓ |
| 新細明體 | Noto Serif CJK TC | 是 | ✓ |
| Arial | Liberation Sans | 否 | ✓（度量兼容） |
| Times New Roman | Liberation Serif | 否 | ✓（度量兼容） |
| Calibri | Carlito | 否 | ✓（度量兼容） |
| Calibri Light | DejaVu Sans | 否 | 残余（Carlito 无 Light 字重） |

## 证据 2：文字重叠检测（同一套 PPT，三种字体环境）

| 运行 | 字体环境 | 53 页项目重叠 | 32 页项目重叠 |
|---|---|---|---|
| 基线 | 原镜像（无别名、无 Liberation） | 18 页×2、32 页×83、39 页×1 = 86 | 7 页×1 = 1 |
| 仅中文别名 | + `69-ppt-font-alias.conf` | 4 页×1、18 页×2、32 页×83、39 页×1 = 87 | 7 页×1 = 1 |
| 最终 | 别名 + Liberation/Carlito/Caladea + MiSans 规则 | 17 页×1、32 页×80、49 页×1 = 82 | **0** |

说明：

- 32 页项目清零，是「中文族名映射 + 拉丁度量兼容」共同作用的结果。
- 53 页项目的残差集中在第 32 页（Visio OLE/EMF，见下）；第 17/49 页各有 1 处 6.6pt / 9.3pt 的
  连字符换行边界重叠（`On-` ← `Mexico`、`6.` ← `Syntpharm`），属排版边界噪声，不影响可读性。
- 重叠数只能说明「有没有互压」，版式是否与源一致仍以目视 PNG 为准：`/tmp/diag/project-*/png/`。
- 该检测只比较**同一行**的词框，跨行的上下互压抓不到，需靠目视补位（见下）。

### 检测盲区与一例源文件版面问题（第 20 页）

目视 53 页项目第 20 页发现：「艾普拉唑/钠」折成两行，第 2 行压住英文副标题。`pdftotext -bbox` 实测：

| 文本 | yMin | yMax |
|---|---|---|
| `唑/钠`（中文标题第 2 行） | 156.4 | 185.0 |
| `Ilaprazole/`（英文副标题） | 170.8 | 194.2 |

纵向重叠 14.2pt。判定**与字体替换无关**：

- 把 `69-ppt-font-alias.conf` 从 fontconfig 里摘掉重转同一份 PPT，第 20 页这几行文字的 bbox 与当前
  产物一致（`艾普拉` x=132.009、y=129.99），替换前后是同一套排版；
- 标题止于第 3 字折行 → 文本框内宽约 80pt，而 5 个 22pt 汉字需 110pt。**源文件文本框本身装不下
  「艾普拉唑/钠」**，PowerPoint 里同样会折行；英文副标题框按单行高度摆放，于是被第 2 行压住。

处置：不属字体修复范围，业务侧改短标题或加宽文本框即可。同页其他条目（如「枸橼酸铋钾」5 字）单行
正常，可作对照。

### 4:3 版式回归

库里现存的实测项目都是 16:9，4:3 用一张合成版式回归（10×7.5in，标题用微软雅黑、正文用宋体、
拉丁段用 Times New Roman、外带一张 4×3 表格）：

- PDF 页尺寸 720×540pt → @150dpi **1500×1125px**，比例正确未被拉伸；
- 微软雅黑 → `NotoSansCJK-Regular.ttc`、宋体 → `NotoSerifCJK-Regular.ttc`、
  新細明體 → `NotoSerifCJK-Regular.ttc`、Calibri → Carlito、Times New Roman → Liberation Serif，全部 ✓；
- 重叠检测 0 处，目视表格列宽与文字基线正常（宋体走思源宋体，未被误映射成黑体）。

## 证据 3：目视对照（第 32 页）

- 基线/仅别名：标题折成 `公司组织架构图 Company Organization` + `Chart`，第二行压在
  「法定代表人 Legal Representative」方框上。
- 最终：标题单行，与源 PPT 一致；底部组织架构仍是 EMF 回退图（文字仍偏挤）。

## 例外：第 32 页是嵌入的 Visio 对象

`ppt/slides/slide32.xml` 里整张组织架构图是一个 `p:graphicFrame`：

```
<a:graphicData uri=".../presentationml/2006/ole">
  <p:oleObj progId="Visio.Drawing.11" r:id="rId2" imgW="15354300" imgH="9372600">
    <p:embed/>
    <p:pic> … r:embed="rId3"（image59.emf）… </p:pic>
```

- 页面上除标题外的文字（`注册部`、`安全部` 等）**不在 slide XML 里**，而是 EMF 里的文本记录，
  可印证：`pdftotext -f 32 -l 32` 能取到 `注册部`，而 `slide32.xml` 里搜不到该字符串。
- 容器里没有 Visio，soffice 只能渲染 EMF 回退图；EMF 的文本按原字体度量定位，
  换字体后字符互相压住，这部分**不可能靠字体映射修好**。
- 规避（不改代码）：业务侧在源 PPT 里对该对象「选择性粘贴 → 图片（增强型图元文件/PNG）」后再上传，
  渲染结果与 PowerPoint 所见一致；或直接删掉该页的视频需求。

如需在服务端处理（未实施，评估后再做）：上传时检测 `progId="Visio.*"` 且带 EMF 回退的 OLE，
把整页按高 dpi 栅格化为 PNG 参与成片——代价是文字不可搜索、页图体积变大。

## 修复落地（与代码的联动）

| 位置 | 改动 |
|---|---|
| `backend/assets/fontconfig/69-ppt-font-alias.conf` | 中文族名 → Noto CJK（`qual="first"`，避开 `45-latin.conf` 别名链）；MiSans/小米兰亭/HarmonyOS Sans 用 `compare="contains"` 覆盖字重后缀 |
| `backend/Dockerfile` / `backend/Dockerfile.worker` | 装 `fonts-liberation`/`fonts-crosextra-carlito`/`fonts-crosextra-caladea`；`COPY` 别名配置 + `fc-cache -f`；构建期自检：中文族名必须命中 `Noto *`，Arial/Times New Roman/Calibri 必须分别命中 `Liberation Sans`/`Liberation Serif`/`Carlito`，否则构建失败 |
| `backend/app/modules/agent/render.py` | `RENDERER_KEY = r2-noto-liberation-v2`（`RENDERER_VERSION` × `FONT_PROFILE`）；出图/合成前的运行时自检 `verify_font_environment()` |

> **v2 的由来（务必先读）**：v1 上线时 Dockerfile 已装字体，但镜像**没有重建**，
> 容器里 Arial 仍解析到 DejaVu，页图实际是「按 DejaVu 排版」的——指纹写着 v1，画面却不是 v1 的效果。
> 表现为第 4 页 6 条要点挤成 5 行、第 32 页标题折行压住下方方框。
> 现在两道闸同时兜住这类「改了但没生效」：
> 1. **构建期**：Dockerfile 里 `fc-match` 校验不过直接构建失败；
> 2. **运行期**：`render.verify_font_environment()` 在页图任务与渲染任务开始时校验，
>    不合格就带可读原因失败（`page_images_error` 会显示「Arial → DejaVu Sans（期望 Liberation Sans）」），
>    不再静默产出一批错图。
>
> 重建后的复核（53 页致君项目）：第 4 页重叠 1 → **0**、第 18 页 2 → **0**，
> 第 32 页标题恢复单行；仅剩该页 Visio OLE/EMF 的 80 处（字体救不了）。

两者都是**改任一处就必须递增 `FONT_PROFILE`**：旧 PDF 的内容寻址 key 里带指纹，页图行还记了
`page_images_renderer`，不等即视为过期，下次投递/重试自动重出（详见
[`ppt-video-generator.md`](ppt-video-generator.md) 4.1 节）。

## 遗留风险

1. `Calibri Light` 仍落到 DejaVu Sans（Carlito 只有 Regular/Bold）。若后续出现以 Light 为主字体的
   版式，需要另找度量兼容的 Light 字重，或接受偏差。
2. 嵌入型 OLE（Visio / MathType 等）只要没有原生渲染器，都只能走回退图，字体映射救不了。
3. 本报告数据来自上面两个项目；新增字体名请按同样方法先归因再改配置，不要盲调 DPI。