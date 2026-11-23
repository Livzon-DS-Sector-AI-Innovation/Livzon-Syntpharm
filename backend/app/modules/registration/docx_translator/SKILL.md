---
name: docx-translator
description: 把 DOCX/DOC 文档翻译为中英/英中双语对照或纯译文文档，保留原文格式，在原文段落之后精确插入译文。支持表格与嵌套表格、合并单元格自动跳过、页眉页脚不翻译、.doc 自动转 .docx，并自动套用药品注册术语表。
---

# 文档翻译（DOCX 中英互译）

## 触发场景

注册团队有以下需求时使用本技能：

- 「把这份英文资料翻译成中文」/「生成中英对照版」
- 「把中文批记录翻成英文给客户」
- 「批量翻译这几个 docx」
- 「按术语表统一译名后再翻译」

平台入口：`/registration/docx-translator`（注册管理 → 文档翻译）。

## 能力边界

| 支持 | 说明 |
|---|---|
| `.docx` / `.doc` / `.wps` | `.doc`/`.wps` 由服务器上的 LibreOffice 自动转换 |
| 语言方向 | 英→中、中→英（双向） |
| 输出模式 | 双语对照（`bilingual`）、译文替换（`replace`）、两者都出（`both`） |
| 术语 | 自动套用术语表库中「启用」的术语，按语言方向取列 |
| 表格 | 普通表格与嵌套表格内文字都会翻译；合并单元格重复内容自动跳过 |
| 格式 | 保留原段落格式、字号；译文字体中文宋体 / 西文 Times New Roman |

不支持（已知限制）：

- 页眉、页脚不翻译
- 文本框 / 形状（VML）内文字不翻译
- 扫描版 PDF 不处理（需先转成可编辑 docx）
- 单文件 ≤ 50MB、单次 ≤ 10 个文件（运行时配置可调）

## 接口

任务为异步：提交后立刻返回 `job_id`，前端轮询状态，完成后按索引下载结果。

```text
POST /api/v1/registration/docx-translator/jobs                 # multipart: files[], source_lang, target_lang, mode, batch_size?
GET  /api/v1/registration/docx-translator/jobs/{job_id}        # 进度与逐文件结果
GET  /api/v1/registration/docx-translator/jobs/{job_id}/files/{file_index}   # 下载结果 docx
GET  /api/v1/registration/docx-translator/files                # 历史译文列表（keyword/page/page_size）
GET  /api/v1/registration/docx-translator/files/{file_id}/download   # 下载历史译文
DELETE /api/v1/registration/docx-translator/files/{file_id}    # 删除单条历史（软删 + 删对象）
GET  /api/v1/registration/docx-translator/glossary             # 术语列表（keyword/page/page_size）
POST /api/v1/registration/docx-translator/glossary             # 新增术语
PUT  /api/v1/registration/docx-translator/glossary/{term_id}   # 改术语 / 启停
DELETE /api/v1/registration/docx-translator/glossary/{term_id} # 软删除
POST /api/v1/registration/docx-translator/glossary/import      # 导入 xlsx（列名「英文」「中文」）
GET  /api/v1/registration/docx-translator/glossary/export      # 导出 xlsx
```

权限码：`registration:docx-translator:read|create|update|delete`。

## 处理流程

1. 校验扩展名 / 大小 / 数量，读入内存后立即建任务并返回 `job_id`（不在请求内解析文档）。
2. 逐文件：临时目录落盘 → 提取待译段落（正文 + 表格）→ 分批调用平台 LLM → 按模式回写。
3. 结果写入 MinIO `docx_translations/{yyyymmdd}/{job_id}/{n}_{文件名}`，接口按任务内索引下载，不接受外部 object key。
4. 每产出一份译文立即登记到 `registration.docx_translation_files`（独立会话、独立事务），
   刷新页面/重启服务后仍可在「历史翻译」页签下载；落库失败只记日志，不影响实时下载。
5. 单文件失败只标记该文件失败，不中断任务，也不进入历史列表（没有可下载产物）；失败文件可在页面「重试此文件」。

## 历史留存与清理

- **可见性**：有 `registration:docx-translator:read` 的人都能看到并下载全部历史。
- **删除**：只有该记录的创建人、或拥有 `registration:docx-translator:delete` 的人能删；
  删除 = 软删记录 + 尽力删除 MinIO 对象（对象删除失败只记日志，次日不再扫到）。
- **自动清理**：每日 03:30 由统一调度器执行 `docx_translator.expired_cleanup`，
  清理超过 `DOCX_TRANSLATOR_RETENTION_DAYS`（默认 30 天，<=0 关闭）的记录与文件；
  每次最多处理 200 条，失败次日重扫。

## 引擎行为

- 批次切分：默认每批 30 段（可在「高级参数」调整），并按估算 token 上限二次切分。
- 失败重试：单次 LLM 调用失败重试 3 次（指数退避）；批次失败后再做多轮补译，仍失败的段落计入成功率。
- 成功率 < 90% 时结果行给出「请人工复核」警告；模板会统计蓝段数 / 原文残留率做保存后校验。
- 批次间随机延迟 0.5–2 秒，防止触发上游限流。

## 术语表

- 数据表：`registration.docx_translation_terms`（英文去重键 `term_en_lower`）。
- 内置术语由 `assets/glossary_cleaned.xlsx` 在应用启动时幂等导入（表非空则跳过）。
- 页面支持搜索、行内编辑、启停、删除（行内二次确认）、xlsx 导入导出；导入按英文名去重更新。
- 导入失败会直接给出可读原因（缺「英文」「中文」列、文件不是 xlsx、内容为空）。

## 运行时配置

在模块配置中维护（`docx_translator` 前缀）：

| 配置项 | 默认 | 说明 |
|---|---|---|
| `DOCX_TRANSLATOR_MAX_FILE_MB` | 50 | 单文件大小上限 |
| `DOCX_TRANSLATOR_MAX_FILES` | 10 | 单次任务文件数上限 |
| `DOCX_TRANSLATOR_DEFAULT_BATCH_SIZE` | 30 | 每批段落数默认值 |
| `DOCX_TRANSLATOR_MIN_SUCCESS_RATE` | 90 | 成功率告警阈值（%） |
| `DOCX_TRANSLATOR_RETENTION_DAYS` | 30 | 译文保留天数（<=0 不自动清理） |

模型与 API Key 走平台统一 LLM 配置（系统设置 → 大模型配置），本模块不保存凭证。

## 排障

| 现象 | 原因与处理 |
|---|---|
| 页面提示「任务状态已过期」 | 任务状态存进程内，服务重启后丢失，重新提交即可 |
| 上传 `.doc` 报「服务器未安装 LibreOffice」 | 镜像缺少 libreoffice，需重新构建后端镜像 |
| 下载 404 | 结果文件不在 MinIO（已被清理/删除）或实时任务已过期；历史记录里能查到就重新提交 |
| 历史列表为空 | 任务失败不落库；或记录已超过保留天数被清理 |
| 成功率偏低 | 检查术语表冲突、模型是否被限流，或减小每批段落数 |
| 译文段落数少于预期 | 合并单元格去重导致（正常）；差异过大时看「保存后校验」告警 |
