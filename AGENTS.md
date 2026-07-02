# dazah-backend AI 编程规范

本文档定义 AI 编码助手必须遵守的规则。违反这些规则会导致代码被拒绝。

## 架构原则

本项目采用**模块化单体架构**，不是微服务。禁止引入微服务、消息队列或其他复杂架构。

技术栈：Python 3.12+、FastAPI、SQLAlchemy 2.0 async、PostgreSQL 17、Redis、Alembic、Pydantic v2、uv、pytest、ruff、mypy、MinIO。

遇到不确定的 API 或库用法时，先查阅官方文档或 Context7，再进行实现。

## 目录结构

```
app/
├── core/              # 基础设施：配置、数据库、Redis、异常、响应、事件总线
├── shared/            # 跨模块契约：ORM 基类、模块注册表、通用 schema
├── platform/          # 平台能力：审计、身份、用户档案、外部集成
├── modules/           # 业务模块（每个模块独立维护 API、Schema、Service、Repository、Model）
└── api/router.py      # 全局路由装配
```

**禁止**：在 `app/models/`、`app/schemas/`、`app/integrations/` 等已废弃的横向目录中放置新业务代码。

## 模块所有权

**全局模块**（`app/core/`、`app/shared/`、`app/platform/`、`app/api/router.py`、`alembic/`）由架构负责人维护。其他模块只能通过公共 API 调用它们。

**跨模块协作**：通过目标模块的 `public_api.py` 或模块注册表完成。如需修改其他模块的内部实现，必须先说明影响范围、原因和验证方式，并由对应负责人处理。

**禁止**：
- 借需求重构其他模块、移动目录、调整公共抽象或改变架构边界
- 直接 import 其他模块的 `repository.py`、`service.py` 或 `models.py`（只能通过 `public_api.py`）
- 循环依赖（A 调用 B，B 又调用 A）

**环境变量**：按模块前缀组织（如 `SAFETY_AI_TEXT_MODEL`、`ENERGY_AUTO_COLLECT_ENABLED`）。

**全局层 vs 模块层**：全局层（如 `app/core/llm/`）只提供通用基础设施 API。业务功能代码（prompt、业务逻辑、错误处理）必须在模块内部，不得放到全局层。

## API 规范

所有路由挂载在 `/api/v1` 下，按模块组织：`/api/v1/<module>/<resource>`。

标准形式：
```
GET    /api/v1/{module}/
POST   /api/v1/{module}/{resource}
GET    /api/v1/{module}/{resource}
GET    /api/v1/{module}/{resource}/{id}
PUT    /api/v1/{module}/{resource}/{id}
DELETE /api/v1/{module}/{resource}/{id}
```

**必须**：
- 入参和出参使用本模块 `schemas.py`
- 返回格式使用 `app/core/response.py`
- 业务异常使用 `app/core/exceptions.py`
- 删除业务数据默认软删除（`is_deleted`），不做物理删除（除非需求明确要求）

**前端访问方式**：
- 开发环境：浏览器 → Next.js (3000) → `src/proxy.ts` → 后端 (8000)
- 生产环境：浏览器 → nginx → Next.js (3000) 或后端 (8000)
- 前端服务器端：通过 `API_BASE_URL` 环境变量访问后端（Docker 内部网络，地址为 `http://dazah-backend-app-1:8000`）

## 认证与权限

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

认证来源：`Authorization: Bearer <jwt>` header 或 `auth_token` cookie（飞书 SSO）。JWT payload 包含 `open_id`，通过 `UserRepository.get_by_feishu_open_id()` 解析用户。

**注意**：当前为 Phase 1（预留接口），`current_user` 可能为 `None`。但默认规则如下：

**默认规则**：
- 所有业务 API 默认需要登录
- 只有明确标记为 public 的接口可以允许 `current_user` 为 `None`
- 新增业务接口时必须显式选择 `require_user` / `optional_user` / `public`
- 未声明的业务接口按 `require_user` 处理

## 数据库规范

使用 PostgreSQL schema 做模块隔离：
- `identity`：本地用户档案（后续关联飞书 SSO）
- `audit`：审计日志和操作追踪
- `core`：平台级配置（如 LLM 配置）
- 每个业务模块一个 schema（如 `production`、`quality`、`equipment`）

### ORM 规则

**必须**：
- 业务模型继承 `app/shared/base_model.py` 中的 `BaseModel`
- 每张表必须有 `__tablename__` 和 `__table_args__ = {"schema": "<module_schema>"}`
- 字段命名使用英文 `snake_case`
- 显式声明唯一约束、索引
- 新增 schema 时同步更新 `app/shared/module_registry.py`
- 新增/修改 env 文件时同步修改 env example

**Schema 管理**：
- 所有数据库 schema 变更必须通过 Alembic 迁移管理
- 禁止使用 `Base.metadata.create_all()` 或 `create_all()` 创建表
- 新增/修改模型后必须运行 `alembic revision --autogenerate` 生成迁移
- 迁移必须遵守单模块原则（每个迁移只修改一个 schema）
- CI 通过 `alembic check` 检测模型与数据库的漂移

**外键约束规范**：
- 允许外键约束（包括跨模块），但必须避免级联删除（CASCADE DELETE）跨模块使用
- 跨模块关系必须明确记录在设计文档中
- 模块边界是组织结构，不是数据库约束边界
- 禁止循环外键依赖
- 对高风险删除操作必须使用软删除或应用层控制

**禁止**：修改已合并或执行过的历史 migration（除非用户明确要求）。

### 迁移规范

**初始基线例外**：`0001_baseline_full_schema` 迁移允许跨所有 schema，因为它建立了完整的数据库基线。这是唯一允许跨模块的迁移。

**单模块原则**：基线之后的每个迁移文件只能修改一个模块的 schema。这样多人并行开发时合并冲突最小。

**例外**：跨模块外键、`platform`/`core`/`shared` 级变更可以跨 schema，但必须由架构负责人审批，并在 migration 注释中说明原因。

示例：
- `abc123_safety_add_hazard_table.py`
- `def456_equipment_add_inspection_route.py`

CI 会自动检查（`scripts/check_migration_scope.py`），违反会导致 PR 无法合并。

如果 `alembic revision --autogenerate` 生成了多个模块的变更：
1. 删除该迁移文件
2. 使用 `--include-object` 过滤，或手动编辑移除其他模块的变更

**CREATE SCHEMA**：Alembic 配置了自动钩子，会为新的 schema 自动生成 `CREATE SCHEMA IF NOT EXISTS`。无需手动添加。

**检查命令**：
```bash
python scripts/check_migration_scope.py alembic/versions/abc123_safety_add_table.py
```

### Model 与 Migration 绑定规则

任何 SQLAlchemy Model 的新增、删除、字段修改、索引修改、约束修改，都必须在同一个 PR/commit 中包含对应 Alembic migration。

**禁止**：
- 只改 model，不生成 migration
- 只改数据库，不改 model
- 在生产环境运行 `alembic revision --autogenerate`
- 直接执行 SQL 修改生产 schema
- 执行包含无关 `DROP TABLE` / `DROP COLUMN` 的自动生成 migration

如果 autogenerate 生成了跨多个模块或包含无关 DROP 操作的 migration，必须停止，不得执行。应创建目标明确的小 migration。

### Orphan Table 处理规则

数据库中存在但当前代码没有 model 的表，不得自动删除。

**处理步骤**：
1. 查询 row count 和表大小
2. 检查是否仍有代码引用
3. 确认业务负责人是否需要保留
4. 完成备份
5. 明确批准后，才允许创建 DROP migration

## LLM 调用规范

使用全局单例 `llm_client`（`app/core/llm/`），不要手动构造客户端。

**配置分层**：
- **API keys** → 加密存储在 `core.llm_configs` 表，加密密钥 `LLM_ENCRYPTION_KEY` 在环境变量中
- **模型名称、参数** → 通过管理界面配置，存储在数据库
- **本地开发** → 可回退到环境变量 `LLM_API_KEY`

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

**异常处理**：
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

### LLM_ENCRYPTION_KEY 安全规则

`LLM_ENCRYPTION_KEY` 必须存放在部署环境变量中，不进入数据库，不进入 Git，不进入 `.env.example`。

Admin UI 保存 API key 后，只允许显示脱敏值，例如 `sk-****abcd`。

**禁止**在日志、异常、API 响应中输出明文 API key。

## 配置管理规范

配置分两层：

**1. 部署配置**（Deployment Settings）
- 位置：`.env` 文件 + `core/config.py`
- 内容：非 LLM 的 API keys、数据库连接、飞书凭证等敏感信息
- 管理：平台管理员在部署时配置
- 变更频率：很少变更

**2. 运行时配置**（Runtime Settings）
- 位置：数据库 `core.module_settings` 表 + 各模块的 settings 页面
- 内容：模型名称、功能开关、调度参数等运营配置
- 管理：模块负责人通过 Web UI 管理
- 变更频率：经常变更

**读取配置**：
```python
# 运行时配置（从数据库）
from app.shared.config_reader import get_module_setting, get_module_setting_bool

model = await get_module_setting("safety", "SAFETY_AI_TEXT_MODEL", "deepseek-v4-flash")
enabled = await get_module_setting_bool("energy", "ENERGY_AUTO_COLLECT_ENABLED", False)

# 部署配置（从环境变量）
from app.core.config import get_settings
settings = get_settings()
api_key = settings.SAFETY_AI_TEXT_API_KEY
```

**新增配置**：
- LLM API keys → 通过管理界面配置，加密存储在 `core.llm_configs` 表（使用 Fernet 加密，密钥在环境变量）
- 其他 API key / 凭证 → 加到 `core/config.py` 的 `Settings` 类
- 模型名称 / 功能开关 / 运营参数 → 加到 `scripts/seed_module_settings.py` 并通过 Web UI 管理

**禁止**：
- 在模块代码中使用 `os.getenv()` 读取运行时配置
  - **允许例外**：为 subprocess 设置环境变量（如 Playwright、LibreOffice、wkhtmltopdf 等工具运行参数）
  - **禁止**：用 `os.getenv()`/`os.environ` 读取业务配置、运行时配置、API key、模型名称或功能开关
- 将 API key 等凭证**明文**存入数据库（必须使用加密）
- 在 `core/config.py` 中存放模型名称等频繁变更的配置

## 文件存储

使用 `app/core/storage.py`（MinIO/S3 兼容），每个模块拥有独立 bucket（`{prefix}-{module}`）：

```python
from app.core.storage import upload_object, get_object, delete_object, is_enabled

if is_enabled():
    upload_object("equipment", "inspection/abc.jpg", data, len(data), "image/jpeg")
    result = get_object("equipment", "inspection/abc.jpg")  # (bytes, content_type) | None
    delete_object("equipment", "inspection/abc.jpg")
```

所有文件访问通过后端代理，浏览器不直连 MinIO。

## OCR 服务

应用启动时自动初始化 OCR 服务（PaddleOCR），所有模块共享同一实例。**禁止**在模块内自行实现 OCR 逻辑。

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
- 重复实现 OCR 逻辑（如调用外部 OCR API）
- 在测试中初始化真实 OCR 服务（必须 mock `get_ocr_service`）


## 跨模块通信

**默认方式**：通过目标模块的 `public_api.py` 直接调用（适用于所有需要返回值的场景）。

**事件总线**（`app/core/events.py`）：仅用于"通知"场景——生产者不需要知道谁在监听。
- 适用：审计日志、通知分发、缓存失效
- 不适用：数据查询、校验、任何需要返回值的操作
- 事件命名：`{module}.{entity}.{action}`（如 `employee.created`、`batch.status_changed`）
- 事件处理器应该是轻量的，不要执行耗时操作

## 异步任务

**长运行进程**（WebSocket 客户端、事件监听、后台守护进程）：
使用 `register_background_worker()` 注册，由应用生命周期管理。

**周期性任务**（定时同步、数据采集、报表生成）：
使用 `SchedulerEngine` + `TaskDefinition`（静态任务）或 `TaskGenerator`（DB 驱动动态任务）。

**一次性异步任务**（用户触发的耗时操作，如生成报告、批量导入）：
使用任务队列（`app/core/jobs.py`，DB 驱动的任务表）。

**禁止**：
- 直接使用 APScheduler（必须用 SchedulerEngine）
- 自定义 `asyncio` 循环（必须用 BackgroundWorker）
- `asyncio.create_task()` 处理业务逻辑（无法重试、无法监控、重启后丢失）
  - **允许例外**：长运行后台工作进程（WebSocket 客户端、事件监听守护进程）内部的心跳、事件分发等基础设施任务
- 在 HTTP 请求中执行超过 5 秒的操作（应改为异步任务 + 轮询状态）

## 错误处理与容错

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

**禁止**：
- 吞掉异常（`except: pass` 或 `except Exception: pass`）
- 无限重试（必须设置 `max_retries`）
- 在循环中不处理异常（会导致整个后台任务崩溃）
- 在后台任务中抛出未捕获异常（必须 `try/except` + `logger.exception`）

## 日志规范

- 每个模块使用 `logger = logging.getLogger(__name__)`
- 级别：`ERROR`（失败）、`WARNING`（降级/重试）、`INFO`（业务事件）、`DEBUG`（开发调试）
- 始终包含上下文：`logger.info("batch created", extra={"batch_id": id, "module": "production"})`
- 异常处理用 `logger.exception()`（自动附带 traceback）
- **禁止**记录 API key、token、密码等敏感信息

## 测试规范

测试文件放在 `tests/modules/<module>/`，与模块一一对应。

**框架**：pytest + pytest-asyncio，异步测试用 `@pytest.mark.asyncio`。

**覆盖优先级**：service 层业务逻辑 > API 端点契约 > repository 查询。

**外部服务**：LLM、飞书、MinIO 等外部依赖必须 mock，不要在测试中调用真实服务。

**运行**：
```bash
uv run pytest                                    # 全量
uv run pytest tests/modules/<module>/            # 单模块
uv run pytest tests/modules/<module>/ -k "test_create_batch"  # 单个用例
```

## 模块结构

详见 [examples/module-structure.md](examples/module-structure.md)。

常用命令见 [examples/commands.md](examples/commands.md)。
