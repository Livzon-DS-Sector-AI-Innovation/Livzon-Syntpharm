# dazah-backend 开发指南

本文档提供详细的开发流程和操作指南。规则和约束请参考 [AGENTS.md](../AGENTS.md)。

## 目录

- [认证与权限使用](#认证与权限使用)
- [LLM 调用](#llm-调用)
- [配置管理](#配置管理)
- [文件存储](#文件存储)
- [OCR 服务](#ocr-服务)
- [数据库迁移操作](#数据库迁移操作)
- [错误处理策略](#错误处理策略)

---

## 认证与权限使用

通过 `app.core.deps.CurrentUser` 获取当前用户（FastAPI 依赖注入）：

```python
from app.core.deps import CurrentUser

@router.get("/batches")
async def list_batches(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    # current_user 可能是 None（未登录）或 User 对象
    if current_user is None:
        raise UnauthorizedError()
    ...
```

**认证来源**：`Authorization: Bearer <jwt>` header 或 `auth_token` cookie（飞书 SSO）。JWT payload 包含 `open_id`，通过 `UserRepository.get_by_feishu_open_id()` 解析用户。

**注意**：当前为 Phase 1（预留接口），`current_user` 可能为 `None`。

---

## LLM 调用

使用全局单例 `llm_client`（`app/core/llm/`），不要手动构造客户端。

### 基本用法

```python
from app.core.llm import llm_client

# 文本对话
result = await llm_client.chat([{"role": "user", "content": "分析这段文本"}])

# 结构化 JSON 输出
parsed = await llm_client.chat_json(messages, expected_keys=["risk_level", "summary"])

# 视觉（图片分析）
result = await llm_client.chat_vision_json("描述图片中的安全隐患", image_urls=[url])

# 流式输出
async for chunk in llm_client.stream_chat(messages):
    yield chunk  # {"type": "reasoning" | "content", "text": "..."}
```

### 异常处理

```python
from app.core.llm import LLMOutputError, LLMProviderError, LLMRateLimitError

try:
    result = await llm_client.chat_json(messages=messages)
except LLMOutputError:
    logger.error("LLM 输出格式错误")
except LLMProviderError:
    logger.error("LLM 服务调用失败")
except LLMRateLimitError:
    logger.warning("LLM 速率限制")
```

**参考实现**：`app/modules/safety/service/hazard.py`

---

## 配置管理

配置分两层——

**1. 部署配置（Deployment Settings）**：`.env` + `core/config.py`，存放 API keys、数据库连接、飞书凭证。

**2. 运行时配置（Runtime Settings）**：数据库 `core.module_settings` 表，存放模型名称、功能开关、调度参数。

### 读取配置

```python
# 运行时配置（从数据库）
from app.shared.config_reader import get_module_setting, get_module_setting_bool
model = await get_module_setting("safety", "SAFETY_AI_TEXT_MODEL", "deepseek-v4-flash")

# 部署配置（从环境变量）
from app.core.config import get_settings
settings = get_settings()
api_key = settings.SAFETY_AI_TEXT_API_KEY
```

### 读取飞书配置

```python
from app.core.config import get_settings
settings = get_settings()
app_id = settings.feishu.platform.app_id
safety_app_id = settings.feishu.safety.credentials.app_id
```

环境变量命名：`FEISHU__{MODULE}__{FIELD}` 或 `FEISHU__{MODULE}__CREDENTIALS__{FIELD}`。

### 新增配置

- LLM API keys → 通过管理界面配置，加密存储在 `core.llm_configs` 表
- 其他 API key / 凭证 → 加到 `core/config.py` 的 `Settings` 类
- 模型名称 / 功能开关 / 运营参数 → 加到 `scripts/seed/seed_module_settings.py` 并通过 Web UI 管理

**新增飞书应用**：
1. 在 `FeishuSettings` 中添加新的子模型
2. 如果新模块需要独立应用，包含 `credentials: FeishuAppCredentials` 字段
3. 如果使用平台应用凭证，只需添加表格配置字段
4. 在 `.env`、`.env.local`、`.env.example` 中添加对应的环境变量

**禁止**：
- 在模块代码中使用 `os.getenv()` 读取运行时配置
- 将 API key 等凭证明文存入数据库
- 在 `core/config.py` 中存放模型名称等频繁变更的配置

---

## 文件存储

使用 `app/core/storage.py`（MinIO/S3 兼容），每个模块拥有独立 bucket（`{prefix}-{module}`）：

```python
from app.core.storage import upload_object, get_object, delete_object, is_enabled

# 上传
await upload_object("equipment", "inspection/abc.jpg", data, len(data), "image/jpeg")

# 下载
result = await get_object("equipment", "inspection/abc.jpg")  # (bytes, content_type) | None

# 删除
await delete_object("equipment", "inspection/abc.jpg")
```

所有文件访问通过后端代理，浏览器不直连 MinIO。

---

## OCR 服务

应用启动时自动初始化 OCR 服务（PaddleOCR），所有模块共享同一实例。

### 基本用法

```python
from app.shared.ocr_service import get_ocr_service

ocr = get_ocr_service()

# 简单文本提取（PP-OCR，速度快）
text = ocr.extract_text(image_path)

# 带位置信息的文本提取
blocks = ocr.extract_with_positions(image_path)  # [{text, bbox, confidence}, ...]

# 结构化文档分析（PP-StructureV3，支持表格、公式、版面分析）
markdown = ocr.extract_markdown(pdf_path)
structure = ocr.extract_structure(image_path)  # {markdown, json, layout, tables}

# 混合接口（自动选择引擎）
result = ocr.extract(image_path, engine=None, output_format="text")
# engine: "pp_ocr" | "pp_structurev3" | None (自动检测：PDF 用 structure，图片用 ocr)
# output_format: "text" | "markdown" | "json" | "positions" | "structure"
```

**禁止**：
- 在模块中直接 import `paddleocr` 或自行初始化 OCR 引擎
- 在测试中初始化真实 OCR 服务（必须 mock `get_ocr_service`）

---

## 数据库迁移操作

### 迁移规范

**初始基线例外**：`0001_baseline_full_schema` 迁移允许跨所有 schema，因为它建立了完整的数据库基线。这是唯一允许跨模块的迁移。

**单模块原则**：基线之后的每个迁移文件只能修改一个模块的 schema。这样多人并行开发时合并冲突最小。

**例外**：跨模块外键、`platform`/`core`/`shared` 级变更可以跨 schema，但必须由架构负责人审批，并在 migration 注释中说明原因。

**示例**：
- `abc123_safety_add_hazard_table.py`
- `def456_equipment_add_inspection_route.py`

### 处理多模块变更

如果 `alembic revision --autogenerate` 生成了多个模块的变更：

1. 删除该迁移文件
2. 使用 `--include-object` 过滤，或手动编辑移除其他模块的变更

### CREATE SCHEMA

Alembic 配置了自动钩子，会为新的 schema 自动生成 `CREATE SCHEMA IF NOT EXISTS`。无需手动添加。

### 检查命令

```bash
# 检查迁移文件的 scope
python scripts/check_migration_scope.py alembic/versions/abc123_safety_add_table.py
```

CI 会自动检查（`scripts/check_migration_scope.py`），违反会导致 PR 无法合并。

### Orphan Table 处理规则

数据库中存在但当前代码没有 model 的表，不得自动删除。

**处理步骤**：
1. 查询 row count 和表大小
2. 检查是否仍有代码引用
3. 确认业务负责人是否需要保留
4. 完成备份
5. 明确批准后，才允许创建 DROP migration

---

## 错误处理策略

| 场景 | 策略 |
|------|------|
| LLM 调用 | 最多 3 次重试，指数退避（1s, 2s, 4s） |
| 外部 API（飞书、能耗平台等） | 最多 3 次重试，指数退避 |
| 数据库操作 | 不重试，依赖连接池（`pool_pre_ping=True`） |
| LLM 不可用 | 返回默认值 + 提示"AI 分析暂时不可用，请人工审核" |
| 飞书 API 不可用 | 记录到待发送队列，后台重试 |
| 外部数据源不可用 | 显示"数据暂时不可用"，不阻塞其他功能 |
| 缓存失效 | 回源查询，不返回错误 |

所有重试操作必须是幂等的（POST 请求用唯一键防止重复）。

---

## 相关文档

- [架构规范](architecture.md)
- [模块结构示例](../examples/module-structure.md)
- [常用命令](../examples/commands.md)
