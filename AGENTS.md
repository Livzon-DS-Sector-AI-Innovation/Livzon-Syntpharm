# dazah-backend AI 编程规范

本文档定义 AI 编码助手必须遵守的规则。违反这些规则会导致代码被拒绝。

## 架构原则

本项目采用**模块化单体架构**，不是微服务。禁止引入微服务、消息队列或其他复杂架构。

**技术栈**：Python 3.12+、FastAPI、SQLAlchemy 2.0 async、PostgreSQL 17、Redis、Alembic、Pydantic v2、uv、pytest、ruff（line-length=120）、mypy（strict）、MinIO。

遇到不确定的 API 或库用法时，先查阅官方文档或 Context7，再进行实现。

## 代码格式规范

- **行长度限制**: 120 字符（`pyproject.toml` 中 `tool.ruff.line-length = 120`）
- **E501 排除列表**: 以下内容类型文件因存储长字符串字面量（LLM prompt、知识库、法规文本、测试 fixture）被排除在 E501 检查之外。这些文件的**主要用途是存储内容文本**，按列断行会降低可读性。
  - 排除列表在 `pyproject.toml` 的 `[tool.ruff.lint.per-file-ignores]` 中维护
  - 新增 prompt/知识库/测试 fixture 文件时，若其长字符串行超过 120 字符，应添加到排除列表
  - 代码文件（service/repository/api）的 E501 必须修复，不得添加到排除列表

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
- 未经用户明确指示，禁止创建新业务模块（`app/modules/<new_module>/`）。新功能必须放入已有模块，只有用户显式要求时才能新建模块

**环境变量**：按模块前缀组织（如 `SAFETY_AI_TEXT_MODEL`、`ENERGY_AUTO_COLLECT_ENABLED`）。

**全局层 vs 模块层**：全局层（如 `app/core/llm/`）只提供通用基础设施 API。业务功能代码（prompt、业务逻辑、错误处理）必须在模块内部，不得放到全局层。

## API 规范

所有路由挂载在 `/api/v1` 下，按模块组织：`/api/v1/<module>/<resource>`。

**标准形式**：
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

通过 `app.core.deps.CurrentUser` 获取当前用户（FastAPI 依赖注入）。认证来源：`Authorization: Bearer <jwt>` header 或 `auth_token` cookie（飞书 SSO）。

**注意**：当前为 Phase 1（预留接口），`current_user` 可能为 `None`。

**默认规则**：
- 所有业务 API 默认需要登录
- 只有明确标记为 public 的接口可以允许 `current_user` 为 `None`
- 新增业务接口时必须显式选择 `require_user` / `optional_user` / `public`
- 未声明的业务接口按 `require_user` 处理

## 数据库规范

使用 PostgreSQL schema 做模块隔离：`identity`（用户档案）、`audit`（审计日志）、`core`（平台配置）、每个业务模块一个 schema。

### ORM 规则

**必须**：
- 业务模型继承 `app/shared/base_model.py` 中的 `BaseModel`
- 每张表必须有 `__tablename__` 和 `__table_args__ = {"schema": "<module_schema>"}`
- 字段命名使用英文 `snake_case`，显式声明唯一约束、索引
- 新增 schema 时同步更新 `app/shared/module_registry.py`

**Schema 管理**：
- 所有数据库 schema 变更必须通过 Alembic 迁移管理
- 禁止使用 `Base.metadata.create_all()` 或 `create_all()` 创建表
- 新增/修改模型后必须运行 `alembic revision --autogenerate` 生成迁移
- 迁移必须遵守单模块原则（每个迁移只涉及一个模块的表）

**外键约束规范**：
- 允许外键约束（包括跨模块），但必须避免级联删除（CASCADE DELETE）跨模块使用
- 跨模块关系必须明确记录在设计文档中，禁止循环外键依赖
- 对高风险删除操作必须使用软删除或应用层控制

**禁止**：修改已合并或执行过的历史 migration（除非用户明确要求）。

### 迁移规范

**命名规范**：迁移文件必须使用顺序编号格式 `NNNN_descriptive_name.py`，其中 NNNN 是 4 位数字（如 0001、0002）。Revision ID 也应遵循相同模式（如 `0001_baseline`、`0002_drop_product`）。禁止使用 Alembic 自动生成的哈希 ID（如 `3cb28d1e1ac7`）。

**初始基线例外**：`0001_baseline_full_schema` 迁移允许跨所有 schema，这是唯一允许跨模块的迁移。

**单模块原则**：基线之后的每个迁移文件只能修改一个模块的 schema。跨模块外键、`platform`/`core`/`shared` 级变更可以跨 schema，但必须由架构负责人审批。

CI 会自动检查（`scripts/check_migration_scope.py`），违反会导致 PR 无法合并。

### Model 与 Migration 绑定规则

任何 SQLAlchemy Model 的新增、删除、字段修改、索引修改、约束修改，都必须在同一个 PR/commit 中包含对应 Alembic migration。

**禁止**：
- 只改 model，不生成 migration
- 只改数据库，不改 model
- 在生产环境运行 `alembic revision --autogenerate`
- 执行包含无关 `DROP TABLE` / `DROP COLUMN` 的自动生成 migration

### Orphan Table 处理规则

数据库中存在但当前代码没有 model 的表，不得自动删除。必须查询 row count、检查代码引用、确认业务负责人是否需要保留、完成备份后，明确批准才允许创建 DROP migration。

## LLM 调用规范

使用全局单例 `llm_client`（`app/core/llm/`），不要手动构造客户端。参考 `app/modules/safety/service/hazard.py` 中的用法。

**配置分层**：
- **API keys** → 加密存储在 `core.llm_configs` 表，加密密钥 `LLM_ENCRYPTION_KEY` 在环境变量中
- **模型名称、参数** → 通过管理界面配置，存储在数据库
- **本地开发** → 可回退到环境变量 `LLM_API_KEY`

**异常处理**：使用 `LLMOutputError`、`LLMProviderError`、`LLMRateLimitError`（`app/core/llm/exceptions.py`）。

### LLM_ENCRYPTION_KEY 安全规则

`LLM_ENCRYPTION_KEY` 必须存放在部署环境变量中，不进入数据库，不进入 Git，不进入 `.env.example`。Admin UI 保存 API key 后，只允许显示脱敏值（如 `sk-****abcd`）。

**禁止**在日志、异常、API 响应中输出明文 API key。

## 配置管理规范

配置分两层：

**1. 部署配置**（Deployment Settings）
- 位置：`.env` 文件 + `core/config.py`
- 内容：API keys、数据库连接、飞书凭证等敏感信息
- 管理：平台管理员在部署时配置，变更频率低

**2. 运行时配置**（Runtime Settings）
- 位置：数据库 `core.module_settings` 表 + 各模块的 settings 页面
- 内容：模型名称、功能开关、调度参数等运营配置
- 管理：模块负责人通过 Web UI 管理，变更频率高

**读取配置**：
```python
# 运行时配置（从数据库）
from app.shared.config_reader import get_module_setting, get_module_setting_bool
model = await get_module_setting("safety", "SAFETY_AI_TEXT_MODEL", "deepseek-v4-flash")

# 部署配置（从环境变量）
from app.core.config import get_settings
settings = get_settings()
api_key = settings.SAFETY_AI_TEXT_API_KEY
```

**新增配置**：
- LLM API keys → 通过管理界面配置，加密存储在 `core.llm_configs` 表
- 其他 API key / 凭证 → 加到 `core/config.py` 的 `Settings` 类
- 模型名称 / 功能开关 / 运营参数 → 加到 `scripts/seed_module_settings.py` 并通过 Web UI 管理

**环境变量同步**：新增/修改 `.env` 文件时，必须同步修改 `.env.example`。

**禁止**：
- 在模块代码中使用 `os.getenv()` 读取运行时配置（允许例外：为 subprocess 设置环境变量）
- 将 API key 等凭证**明文**存入数据库（必须使用加密）
- 在 `core/config.py` 中存放模型名称等频繁变更的配置

### 飞书凭证管理

所有飞书应用凭证采用嵌套结构管理，按模块分组。结构定义在 `app/core/config.py`：

```python
class FeishuAppCredentials(BaseModel):
    app_id: str = ""
    app_secret: str = ""

class FeishuSettings(BaseModel):
    platform: FeishuPlatformConfig      # 平台应用（SSO、组织同步、IM、通用 Bitable）
    hr_bitable: FeishuHRBitableConfig   # HR 模块表格（使用平台应用凭证）
    safety: FeishuSafetyConfig          # 安全模块（独立应用 + 隐患表格）
    equipment: FeishuEquipmentConfig    # 设备模块（独立应用）
    vehicle: FeishuVehicleConfig        # 车辆模块（独立应用 + 申请表格）
    training: FeishuTrainingConfig      # 培训模块（独立应用 + 培训表格）
    product: FeishuProductConfig        # 产品模块（使用平台应用凭证）
    ai_query: FeishuAIQueryConfig       # AI 查询配置
```

**环境变量命名规则**：使用双下划线 `__` 分隔层级，格式 `FEISHU__{MODULE}__{FIELD}` 或 `FEISHU__{MODULE}__CREDENTIALS__{FIELD}`。

**代码中读取**：
```python
from app.core.config import get_settings
settings = get_settings()
app_id = settings.feishu.platform.app_id
safety_app_id = settings.feishu.safety.credentials.app_id
```

**新增飞书应用**：
1. 在 `FeishuSettings` 中添加新的子模型
2. 如果新模块需要独立应用，包含 `credentials: FeishuAppCredentials` 字段
3. 如果使用平台应用凭证，只需添加表格配置字段
4. 在 `.env`、`.env.local`、`.env.example` 中添加对应的环境变量

## 文件存储与 OCR

**文件存储**：使用 `app/core/storage.py`（MinIO/S3 兼容），每个模块拥有独立 bucket。所有文件访问通过后端代理，浏览器不直连 MinIO。

**OCR 服务**：应用启动时自动初始化 OCR 服务（PaddleOCR），所有模块共享同一实例。使用 `app/shared/ocr_service.py` 中的 `get_ocr_service()`，参考 `app/modules/safety/service/hazard.py` 中的用法。

**禁止**：
- 在模块中直接 import `paddleocr` 或自行初始化 OCR 引擎
- 在测试中初始化真实 OCR 服务（必须 mock `get_ocr_service`）

## 路径与地址规范

**禁止**：
- 硬编码绝对文件路径（如 `D:/xxx`、`/home/xxx`）。必须使用配置项、环境变量或相对路径
- 硬编码 `localhost` / `127.0.0.1` 生成跳转链接或回调地址。必须使用环境变量（如 `APP_BASE_URL`）

## 跨模块通信

**默认方式**：通过目标模块的 `public_api.py` 直接调用（适用于所有需要返回值的场景）。

**事件总线**（`app/core/events.py`）：仅用于"通知"场景——生产者不需要知道谁在监听。
- 适用：审计日志、通知分发、缓存失效
- 不适用：数据查询、校验、任何需要返回值的操作
- 事件命名：`{module}.{entity}.{action}`（如 `employee.created`、`batch.status_changed`）

## 异步任务

**长运行进程**（WebSocket 客户端、事件监听）：使用 `register_background_worker()` 注册。

**周期性任务**（定时同步、数据采集）：使用 `SchedulerEngine` + `TaskDefinition`（静态任务）或 `TaskGenerator`（DB 驱动动态任务）。

**一次性异步任务**（用户触发的耗时操作）：使用任务队列（`app/core/jobs.py`）。

**禁止**：
- 直接使用 APScheduler（必须用 SchedulerEngine）
- 自定义 `asyncio` 循环（必须用 BackgroundWorker）
- `asyncio.create_task()` 处理业务逻辑（无法重试、无法监控、重启后丢失）
  - **允许例外**：长运行后台工作进程内部的心跳、事件分发等基础设施任务
- 在 HTTP 请求中执行超过 5 秒的操作（应改为异步任务 + 轮询状态）

## 错误处理与容错

**重试策略**：外部调用（LLM、飞书、能耗平台等）最多 3 次重试，指数退避（1s, 2s, 4s）。所有重试操作必须是幂等的。

**降级策略**：
- LLM 不可用 → 返回默认值 + 提示"AI 分析暂时不可用，请人工审核"
- 飞书 API 不可用 → 记录到待发送队列，后台重试
- 外部数据源不可用 → 显示"数据暂时不可用"，不阻塞其他功能
- 缓存失效 → 回源查询，不返回错误

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
uv run pytest tests/modules/<module>/ -k "test_name"  # 单个用例
```

## 模块结构

详见 [examples/module-structure.md](examples/module-structure.md)。

常用命令见 [examples/commands.md](examples/commands.md)。

## 开发指南

详细的开发流程、代码示例和操作指南请参考 [docs/development-guide.md](docs/development-guide.md)。
