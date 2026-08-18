# AI 编程规范

本文档定义 AI 编码助手必须遵守的规则。违反这些规则会导致代码被拒绝。

## 目录
- [仓库通用规则](#仓库通用规则)
- [仓库组织](#仓库组织)
- [后端 — Python / FastAPI](#后端----python--fastapi)
- [前端 — Next.js / TypeScript](#前端----nextjs--typescript)

## 仓库通用规则

- 禁止硬编码绝对文件路径（使用配置、环境变量或相对路径）
- 禁止在 URL 中硬编码 `localhost` / `127.0.0.1`（使用环境变量）
- 禁止在日志或异常中输出 API key、token、密码等敏感信息
- 禁止提交 `.env` 文件 — 仅提交 `.env.example` 模板
- 前后端之间的交叉引用必须通过公共契约（OpenAPI spec）

**例外情况**：
- Docker 服务发现名称（如 `http://backend:8000`、`redis://erp-redis:6379`）不是硬编码 URL，而是 Docker 内部网络的服务名，仅在容器网络中有效
- CI/测试环境可以使用虚拟凭据（如 `POSTGRES_PASSWORD: postgres`），但这些文件不得用于生产环境



## 仓库组织

### 测试
- 测试文件放在 `backend/tests/modules/<module>/`
- 测试 fixture（样本文件、测试数据）放在 `backend/tests/fixtures/`
- 单元测试放在 `backend/tests/unit/`，集成测试放在 `backend/tests/integration/`

### 脚本 (`backend/scripts/`)
按用途组织：

| 目录 | 用途 |
|---|---|
| `scripts/ci/` | CI 编排、spec 生成、迁移检查 |
| `scripts/seed/` | 数据库种子数据与模块设置 |
| `scripts/migration/` | 一次性数据迁移与回填 |
| `scripts/sync/` | 飞书同步与多维表格检查 |
| `scripts/import/` | Excel/CSV 数据导入脚本 |
| `scripts/test/` | 测试辅助与调试脚本 |
| `scripts/regulatory_poc/` | 法规追踪概念验证 |

### 第三方代码
- 第三方库放在 `backend/vendor/`
- 禁止将外部仓库直接克隆到 `backend/` 根目录
- `backend/edbo_service/` 是 EDBO+ 封装服务
- `backend/vendor/edboplus-main/` 是 EDBO+ 库

### 文档
- 后端文档放在 `backend/docs/`
- 培训模板放在 `backend/docs/training/`
- 禁止将 `.docx`、`.xlsx` 或 PDF 文件放在 `backend/` 根目录

---

# 后端 — Python / FastAPI

## 架构原则

本项目采用**模块化单体架构**，不是微服务。禁止引入微服务、消息队列或其他复杂架构。 原因：当前团队规模和业务复杂度不需要微服务，模块化单体更易维护、部署和调试。

**技术栈**：Python 3.12+、FastAPI、SQLAlchemy 2.0 async、PostgreSQL 17、Redis、Alembic、Pydantic v2、uv、pytest、ruff（line-length=120）、mypy（strict）、MinIO。

遇到不确定的 API 或库用法时，先查阅官方文档或 Context7，再进行实现。

## 代码格式规范

- **行长度限制**: 120 字符（`pyproject.toml` 中 `tool.ruff.line-length = 120`）
- **E501 排除列表**: 以下内容类型文件因存储长字符串字面量（LLM prompt、知识库、法规文本、测试 fixture）被排除在 E501 检查之外。这些文件的**主要用途是存储内容文本**，按列断行会降低可读性。
  - 排除列表在 `pyproject.toml` 的 `[tool.ruff.lint.per-file-ignores]` 中维护
  - 新增 prompt/知识库/测试 fixture 文件时，若其长字符串行超过 120 字符，应添加到排除列表
  - 代码文件（service/repository/api）的 E501 必须修复，不得添加到排除列表

## 安全规则

### SQL 查询
- **必须**使用参数化查询（`:param` 占位符 + 绑定参数）或 SQLAlchemy ORM 构建所有 SQL 查询
- **禁止**使用 f-string、字符串拼接（`+`）或 `.format()` 将运行时数据嵌入 SQL 语句
- 所有外部数据源（包括飞书多维表格等内部系统）均视为不可信，必须参数化

## 目录结构

```
backend/app/
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


**禁止** `response_model=dict` 或 `response_model=ApiResponse`：所有结构化 JSON 响应的 endpoint 必须使用具体的 Pydantic 响应模型，且该模型必须描述完整的实际响应体（包括 `code`、`data`、`message` 等实际返回字段），不能仅描述 `data`。

`response_model=dict` 会生成缺乏具体字段类型的 OpenAPI schema（如 `{type: object}`），导致前端无法获得可靠的生成类型。`response_model=ApiResponse` 同样有问题，因为 `ApiResponse.data` 被定义为 `Any`，OpenAPI 无法推断实际的数据结构。

具体业务响应模型定义在对应模块的 `schemas.py` 中。例如：

```python
# ✅ 正确：使用具体的响应模型
@router.get("/employees", response_model=EmployeeListResponse)
async def list_employees(...):
    data = [EmployeeResponse.model_validate(e).model_dump(mode="json") for e in employees]
    return build_response(data=data, ...)

# ❌ 错误：使用通用模型
@router.get("/employees", response_model=ApiResponse)
async def list_employees(...):
    return build_response(data=employees)
```

`build_response()` 返回 `ApiResponse` 是可以的，因为 FastAPI 会优先使用路由声明的 `response_model` 进行 OpenAPI 生成和响应校验。文件下载、流式响应、重定向等需要直接控制 HTTP Response 的场景除外。
**前端访问方式**：
- 开发环境：浏览器 → Next.js (3000) → `src/proxy.ts` → 后端 (8000)
- 生产环境：浏览器 → nginx → Next.js (3000) 或后端 (8000)
- 前端服务器端：通过 `API_BASE_URL` 环境变量访问后端（Docker 内部网络）

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

CI 会自动检查（`scripts/ci/check_migration_scope.py`），违反会导致 PR 无法合并。

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

**新增配置**：
- LLM API keys → 通过管理界面配置，加密存储在 `core.llm_configs` 表
- 其他 API key / 凭证 → 加到 `core/config.py` 的 `Settings` 类
- 模型名称 / 功能开关 / 运营参数 → 加到 `scripts/seed/seed_module_settings.py` 并通过 Web UI 管理

**环境变量同步**：新增/修改 `.env` 文件时，必须同步修改 `.env.example`。

**禁止**：
- 在模块代码中使用 `os.getenv()` 读取运行时配置（允许例外：为 subprocess 设置环境变量）
- 将 API key 等凭证**明文**存入数据库（必须使用加密）
- 在 `core/config.py` 中存放模型名称等频繁变更的配置

代码示例详见 [backend/docs/development-guide.md](backend/docs/development-guide.md#配置管理)。

### 飞书凭证管理

所有飞书应用凭证采用嵌套结构管理，按模块分组。结构定义在 `app/core/config.py` 的 `FeishuSettings` 类中。

**环境变量命名规则**：使用双下划线 `__` 分隔层级，格式 `FEISHU__{MODULE}__{FIELD}` 或 `FEISHU__{MODULE}__CREDENTIALS__{FIELD}`。

**新增飞书应用**：
1. 在 `FeishuSettings` 中添加新的子模型
2. 如果新模块需要独立应用，包含 `credentials: FeishuAppCredentials` 字段
3. 如果使用平台应用凭证，只需添加表格配置字段
4. 在 `.env`、`.env.local`、`.env.example` 中添加对应的环境变量

## 文件存储与 OCR

**文件存储**：使用 `app/core/storage.py`（MinIO/S3 兼容），每个模块拥有独立 bucket。所有文件访问通过后端代理，浏览器不直连 MinIO。

**OCR 服务**：应用启动时自动初始化 OCR 服务（PaddleOCR），所有模块共享同一实例。使用 `app/shared/ocr_service.py` 中的 `get_ocr_service()`，参考 `app/modules/safety/service/hazard.py` 中的用法。

**禁止**：
- 在模块中直接 import `paddleocr` 或自行初始化 OCR 引擎（原因：OCR 服务是全局单例，重复初始化会浪费内存和启动时间）
- 在测试中初始化真实 OCR 服务（必须 mock `get_ocr_service`）

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

**框架**：pytest + pytest-asyncio。`pyproject.toml` 中配置了 `asyncio_mode = "auto"`，`async def test_*` 函数会被自动识别为异步测试，不需要 `@pytest.mark.asyncio` 装饰器。

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

详细的开发流程、代码示例和操作指南请参考 [backend/docs/development-guide.md](backend/docs/development-guide.md)。

---

# 前端 — Next.js / TypeScript

原料药厂管理系统前端，Next.js 16 App Router，TypeScript。后端为独立的 Python FastAPI 服务。

UI 和组件样式必须遵守 [frontend/DESIGN.md](frontend/DESIGN.md)。使用 antd 组件时，用 Context7 查询最新参数文档。

## 技术栈

- **Next.js 16** + React 19 + TypeScript + Tailwind CSS
- **组件库**：Ant Design V6（antd）
- **客户端状态**：Zustand（`stores/` 目录）
- **服务端数据**：Server Component 通过 `lib/api/server/` 获取数据
- **客户端数据**：React Query（`@tanstack/react-query`）
- **表单**：Ant Design Form（默认）
- **数据边界校验**：Zod（选择性使用）

## 表单与数据校验

### 表单系统

前端表单默认使用 **Ant Design Form**。使用 `Form.Item` 的 `rules` 属性进行简单的 UI 校验和用户反馈。

**禁止**：在没有明确理由的情况下，将现有的 Ant Design Form 迁移到 React Hook Form 或 Zod。

### Zod 的使用场景

Zod 仅用于**数据边界**的运行时校验，不用于普通表单。适用场景：

1. **Server Actions 的复杂输入**：当 Server Action 接收复杂、嵌套或不可信的输入时
2. **Excel/CSV 文件导入**：解析用户上传的文件时，校验数据结构
3. **LLM 结构化输出**：解析 LLM 返回的 JSON 数据时
4. **环境变量校验**：应用启动时校验关键环境变量
5. **复杂的数据转换**：跨系统数据转换前的校验

**不适用**：普通的表单字段校验（用 Ant Design Form rules）、简单的 API 响应处理（用 TypeScript 类型）。

后端 FastAPI/Pydantic 校验仍然是 API 输入的最终来源。

## 目录结构

```
frontend/src/
├── app/(dashboard)/<模块>/   # 路由页面（Server Component，只做数据获取和布局）
├── components/<模块>/        # 该模块所有 UI 组件
├── components/shared/        # 公共组件（禁止修改，需新增找架构负责人）
├── actions/<模块>.ts         # 该模块所有写操作（Server Actions）
├── stores/<模块>.ts          # 该模块客户端状态
├── types/<模块>.ts           # 该模块 TypeScript 类型
├── lib/                      # 基础设施（只允许修改自己负责模块的部分）
│   └── api/
│       ├── client/           # 浏览器只读 API（GET/list/search/detail）
│       └── server/           # 服务器端 API（Server Component / Server Action）
└── proxy.ts                  # API 代理（禁止修改）
```

## Server Component 与 Client Component

`page.tsx` 默认是 Server Component，**不加** `'use client'`。

**规则**：
- 使用了 React Hooks、浏览器 API、事件处理器、Zustand store 或直接使用 antd 组件 → 必须加 `'use client'`
- 页面只是导入并渲染 Client Component → 不需要 `'use client'`
- Client 组件放在 `components/<模块>/` 里，`page.tsx` 只负责获取数据然后传给 Client 组件

详见 [examples/server-component-pattern.md](examples/server-component-pattern.md)。

**Barrel 文件规则**：`components/<模块>/index.ts` 导出的组件如果使用了 Zustand store 或 React Context，barrel 文件**必须**加 `'use client'`（否则构建失败）。最佳实践：所有 barrel 文件统一加 `'use client'`。

### 动态渲染

Server Component 页面如果通过 `actions/` 获取运行时数据（调用后端 API），**必须**在页面顶部添加：

```typescript
export const dynamic = 'force-dynamic'
```

原因：Next.js 默认尝试静态预渲染 Server Component，但后端 API 在构建时不可用，会导致构建失败或返回过期数据。只有纯静态页面（不调用后端 API）才不需要此配置。

## 写操作必须用 Server Actions

所有 POST/PUT/DELETE 操作写在 `actions/` 目录。**禁止**在 Client 组件里直接 fetch 写接口。

**例外：** 需要流式响应（SSE/ReadableStream）或上传进度追踪时，允许在 `lib/api/client/` 中使用直接 fetch。

原因：Server Actions 自动处理 CSRF、revalidation 和错误边界，客户端 fetch 写操作会绕过这些安全机制。

详见 [examples/server-actions.md](examples/server-actions.md)。

## 模块边界

**禁止**跨模块直接 import 组件内部文件。如果需要用其他模块的东西，只能从该模块的 `index.ts` 导入：

```typescript
✗ import { BatchForm } from '@/components/production/BatchForm'
✓ import { BatchTable } from '@/components/production'
```

## 命名规范

- 组件文件：PascalCase（`BatchTable.tsx`）
- 非组件文件：camelCase（`useBatch.ts`、`batchApi.ts`）
- 类型名：PascalCase（`BatchStatus`、`CreateBatchInput`）
- Server Action 函数：动词开头（`createBatch`、`updateBatch`、`submitApproval`）
- API 请求函数：以 `fetch` 开头（`fetchBatches`、`fetchBatchById`）

## 新增页面的步骤

1. 在 `app/(dashboard)/<模块>/` 下新建目录和 `page.tsx`
2. `page.tsx` 里 fetch 数据，传给 `components/<模块>/` 里的组件
3. 组件写在 `components/<模块>/` 里，需要交互的加 `'use client'`
4. 如果有写操作，写在 `actions/<模块>.ts` 里
5. 类型定义更新到 `types/<模块>.ts`
6. 新增的对外组件记得在 `components/<模块>/index.ts` 里导出

## API 调用架构

### 路由转发

客户端代码使用相对路径 `/api/v1/...`，由 `src/proxy.ts` 转发到后端。服务器端代码使用 `API_BASE_URL` 环境变量。

**禁止**：硬编码后端地址、暴露后端端口、使用 `NEXT_PUBLIC_API_BASE_URL`、硬编码绝对文件路径或固定地址。

### proxy.ts 规则

`src/proxy.ts` 是 Next.js 请求中间层，仅负责 API 转发、流式响应处理和轻量登录状态判断。当前项目使用 Turbopack，因此不使用 `next.config.js` 的 `rewrites()`，而通过 `proxy.ts` 转发 `/api/v1/*`。

**允许：**
- 将 `/api/v1/*` 转发到后端
- 透传 HTTP method、body、headers 和 cookies
- 保持流式响应和 SSE 行为
- 仅判断 session cookie 或 token 是否存在
- 将明显未登录的页面请求重定向到 `/login`
- 通过 `matcher` 排除公开路由和静态资源

**禁止：**
- 调用数据库或 API 验证 token
- 角色、权限或模块访问判断
- 业务规则和模块专属逻辑
- 请求或响应数据转换
- LLM 调用
- 审计日志写入
- 数据库访问
- 将 `proxy.ts` 的检查视为正式授权结果

真实身份验证、权限判断、业务规则、审计和数据访问必须由 FastAPI 后端执行。Server Actions 可以调用后端，但不能替代后端授权。

### 新增 API 调用

1. **客户端调用**：在 `lib/api/client/<模块>.ts` 中使用相对路径 `/api/v1/...`
2. **服务器端调用**：在 `lib/api/server/<模块>.ts` 中使用 `API_BASE_URL` 环境变量
3. **写操作**：在 `actions/<模块>.ts` 中调用 `lib/api/server/` 的函数，不要直接 fetch

## 类型系统

### API 类型来源

所有 API 相关的类型（请求参数、响应数据）**必须**从 `@/types/generated/schema` 导入。**禁止**手写 API 类型。原因：OpenAPI spec 是前后端契约的唯一来源，手写类型会与后端漂移。


**禁止**：手写 API 响应类型、手写 API 请求类型、在 API 调用中使用手写类型。

### API 调用层级

```
frontend/src/types/generated/     ← 自动生成，禁止编辑
frontend/src/lib/api/client/*.ts     ← 浏览器 GET/list/search/detail，使用 /api/v1/...
frontend/src/lib/api/server/*.ts     ← Server Component / Server Action 使用，使用 API_BASE_URL
frontend/src/actions/*.ts         ← Server Actions，调用 lib/api
```

- **GET / list / search / detail**：浏览器调用放在 `src/lib/api/client/`，服务器调用放在 `src/lib/api/server/`
- **create / update / delete / upload**：必须通过 Server Actions

### 类型检查

后端 API 变化后，前端必须重新生成类型：`cd ../backend && uv run python scripts/ci/export_openapi.py` 然后 `cd ../frontend && pnpm generate:api`。CI 会检查类型同步。

## 禁止修改的文件

以下文件修改前**必须**获得批准（影响所有开发者和部署流程）：

**架构文件**（只有架构负责人可以修改）：
- `src/proxy.ts`
- `src/components/shared/` 下所有文件
- `src/hooks/usePermission.ts`

**治理文件**（影响 AI 审计和开发规范）：
- `AGENTS.md`
- `docs/ai-audit-plan.md`
- `docs/ai-audit-findings.md`

**部署文件**（影响所有环境）：
- `frontend/Dockerfile`
- `backend/Dockerfile`
- `docker-compose.yml`
- `docker-compose.dev.yml`
- `docker-compose.ci.yml`

修改这些文件前，请：
1. 在 PR 中说明修改原因
2. 验证所有三种环境（生产、开发、CI）均能正常工作
3. 确保不破坏现有工作流
## Docker 开发环境

前端使用**单文件多阶段构建**（`frontend/Dockerfile`），包含四个阶段：
- **base** — 共享基础：Node 22 Alpine、pnpm 10.33.0、依赖安装
- **dev** — 开发阶段：复制源代码，运行 `pnpm dev`，支持热更新
- **builder** — 生产构建阶段：运行 `pnpm build`
- **runtime** — 生产运行阶段：仅包含 standalone 输出，运行 `node server.js`

三种 docker-compose 配置：
- `docker-compose.yml` — 生产环境（`target: runtime`，无热更新）
- `docker-compose.dev.yml` — 开发覆盖（`target: dev`，有热更新，支持跨平台文件监听）
- `docker-compose.ci.yml` — CI 环境（`target: runtime`，用于 E2E 测试）

开发时**必须**使用：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

开发环境通过轮询实现跨平台文件监听（macOS/Windows Docker Desktop 需要）：
- `WATCHPACK_POLLING=true` — webpack 文件监听
- `CHOKIDAR_USEPOLLING=true` — chokidar 文件监听

