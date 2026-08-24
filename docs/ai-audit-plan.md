# AI Audit Plan

This document defines a fixed audit procedure for the Livzon-Syntpharm monorepo. The audit checks compliance with `AGENTS.md` using 15 fixed categories. Each category references specific AGENTS.md rules, defines exact directories to inspect, and specifies questions to answer.

No scanners, scripts, or automation. This document IS the procedure. Feed one category at a time to an AI auditor with the relevant source files.

---

## Audit categories

1. [Repository layout](#1-repository-layout)
2. [Secrets and hardcoded values](#2-secrets-and-hardcoded-values)
3. [Backend module boundaries](#3-backend-module-boundaries)
4. [API and authentication](#4-api-and-authentication)
5. [Models and migrations](#5-models-and-migrations)
6. [Configuration and logging](#6-configuration-and-logging)
7. [External services and background tasks](#7-external-services-and-background-tasks)
8. [Backend tests](#8-backend-tests)
9. [Frontend component boundaries](#9-frontend-component-boundaries)
10. [Frontend API and generated types](#10-frontend-api-and-generated-types)
11. [Proxy and routing](#11-proxy-and-routing)
12. [Cross-project OpenAPI](#12-cross-project-openapi)
13. [Docker and deployment](#13-docker-and-deployment)
14. [E2E](#14-e2e)
15. [SQL 注入与不安全查询](#15-sql-注入与不安全查询)

---


## 1. Repository layout

### Audit type
Full audit

### Rules (from AGENTS.md)

**仓库组织 / 测试:**
- 测试文件放在 `backend/tests/modules/<module>/`
- 测试 fixture 放在 `backend/tests/fixtures/`
- 单元测试放在 `backend/tests/unit/`，集成测试放在 `backend/tests/integration/`

**仓库组织 / 脚本:**
Scripts must be organized in these directories:

| Directory | Purpose |
|-----------|---------|
| `scripts/ci/` | CI orchestration, migration checks |
| `scripts/seed/` | DB seed data and module setup |
| `scripts/migration/` | One-time data migrations and backfills |
| `scripts/sync/` | Feishu sync and Bitable checks |
| `scripts/import/` | Excel/CSV data import |
| `scripts/test/` | Test helpers and debug scripts |
| `scripts/regulatory_poc/` | Regulatory tracking PoC |

**仓库组织 / 第三方代码:**
- 第三方库放在 `backend/vendor/`
- 禁止将外部仓库直接克隆到 `backend/` 根目录
- `backend/edbo_service/` 是 EDBO+ 封装服务
- `backend/vendor/edboplus-main/` 是 EDBO+ 库

**仓库组织 / 文档:**
- 后端文档放在 `backend/docs/`
- 禁止将 `.docx`、`.xlsx` 或 PDF 文件放在 `backend/` 根目录

**后端 / 目录结构:**
```
backend/app/
├── core/              # Infrastructure: config, database, Redis, exceptions, response, events
├── shared/            # Cross-module contracts: ORM base, module registry, common schema
├── platform/          # Platform capabilities: audit, identity, user profiles, external integrations
├── modules/           # Business modules
└── api/router.py      # Global route assembly
```

禁止在 `app/models/`、`app/schemas/`、`app/integrations/` 等已废弃的横向目录中放置新业务代码。

**前端 / 目录结构:**
```
frontend/src/
├── app/(dashboard)/<module>/
├── components/<module>/
├── components/shared/
├── actions/<module>.ts
├── stores/<module>.ts
├── types/<module>.ts
├── lib/api/client/
├── lib/api/server/
└── proxy.ts

**禁止修改的文件（治理文件）:**
- `AGENTS.md`
- `docs/ai-audit-plan.md`
- `docs/ai-audit-findings.md`
```

### Directories to inspect
- Repo root (`/`)
- `backend/app/`
- `backend/docs/`
- `backend/scripts/`
- `backend/tests/`
- `backend/vendor/`
- `backend/edbo_service/`
- `frontend/src/`

### Questions

1. Are there any `.docx`, `.xlsx`, or PDF files in `backend/` root?
2. Is there any code in deprecated `app/models/`, `app/schemas/`, or `app/integrations/` directories?
3. Are backend scripts in the correct directories per the table? (check for scripts outside the listed directories)
4. Are test files in the correct locations (`tests/modules/<module>/`, `tests/unit/`, `tests/integration/`)?
5. Are test fixtures in `backend/tests/fixtures/`?
6. Is there any cloned external repository directly in `backend/` root (not in `vendor/`)?
7. Does `backend/app/` follow the `core/` / `shared/` / `platform/` / `modules/` / `api/router.py` layout?
8. Does `frontend/src/` follow the defined directory structure?
9. Are backend documents in `backend/docs/`?
10. Is the training template directory `backend/docs/training/` present if referenced?

11. Have `AGENTS.md`, `docs/ai-audit-plan.md`, or `docs/ai-audit-findings.md` been modified in a way that requires architecture approval?
### Output format

| Stat | Count |
|------|-------|
| Files inspected | |
| Files not inspected | |
| Rules evaluated | |
| Rules not evaluated | |
| Confirmed findings | |
| Uncertain findings | |

Each finding:
```
file:line — rule reference — evidence — severity: blocking|high|medium|low
```

---


## 2. Secrets and hardcoded values

### Audit type
Full audit

### Rules (from AGENTS.md)

**仓库通用规则:**
- 禁止硬编码绝对文件路径（使用配置、环境变量或相对路径）
- 禁止在 URL 中硬编码 `localhost` / `127.0.0.1`（使用环境变量）
- 禁止在日志或异常中输出 API key、token、密码等敏感信息
- 禁止提交 `.env` 文件

**后端 / LLM_ENCRYPTION_KEY:**
- `LLM_ENCRYPTION_KEY` 必须存放在部署环境变量中，不进入数据库，不进入 Git，不进入 `.env.example`
- 禁止在日志、异常、API 响应中输出明文 API key

**前端 / API 调用架构 / 禁止:**
- 禁止硬编码后端地址或暴露后端端口
- 禁止使用 `NEXT_PUBLIC_API_BASE_URL`
- 禁止硬编码绝对文件路径（如 `D:/xxx`、`C:/xxx`）
- 禁止硬编码 `localhost:3000` 或其他固定地址生成跳转/分享链接

### Directories to inspect
- Entire repository (both backend and frontend)
- `.env` files
- `.env.example`
- Dockerfiles and compose files

### Questions

1. Is `.env` committed to git? (Only `.env.example` should be tracked. Check with `git ls-files .env`)
2. Are there hardcoded `localhost` or `127.0.0.1` URLs outside of:
   - Test fixtures
   - `proxy.ts` default fallback (`API_BASE_URL || 'http://localhost:8000'`)
   - CI configuration
   - Docker service discovery names (e.g., `http://backend:8000` in docker-compose.yml, Dockerfile)
3. Are there hardcoded absolute file paths (e.g. `D:/`, `C:/`, `/home/` as string literals)?
4. Is `NEXT_PUBLIC_API_BASE_URL` used anywhere in the frontend?
5. Does `LLM_ENCRYPTION_KEY` appear in `.env.example`, the database, or any git-tracked file?
6. Are there any API key patterns in source code or log statements? (Patterns: `sk-[a-zA-Z0-9]{20,}`, `api_key\s*=\s*'[^']{20,}'`, `token\s*=\s*'[^']{20,}'`)
7. Are there plaintext credentials in configuration files?
8. Are environment variable files (`.env`, `.env.local`) properly gitignored?
9. Are there `process.env.API_BASE_URL` reads or `getApiBaseUrl()` definitions outside of `lib/api/server/base.ts`?

### Output format

| Stat | Count |
|------|-------|
| Files inspected | |
| Files not inspected | |
| Rules evaluated | |
| Rules not evaluated | |
| Confirmed findings | |
| Uncertain findings | |

Each finding:
```
file:line — rule reference — evidence — severity: blocking|high|medium|low
```

---


## 3. Backend module boundaries

### Audit type
Full audit

### Rules (from AGENTS.md)

**模块所有权:**
- 全局模块（`app/core/`、`app/shared/`、`app/platform/`、`app/api/router.py`、`alembic/`）由架构负责人维护。其他模块只能通过公共 API 调用它们。
- 跨模块协作通过目标模块的 `public_api.py` 或模块注册表完成。如需修改其他模块的内部实现，必须先说明影响范围、原因和验证方式，并由对应负责人处理。

**模块所有权 / 禁止:**
- 借需求重构其他模块、移动目录、调整公共抽象或改变架构边界
- 直接 import 其他模块的 `repository.py`、`service.py` 或 `models.py`（只能通过 `public_api.py`）
- 循环依赖（A 调用 B，B 又调用 A）
- 未经用户明确指示，禁止创建新业务模块（`app/modules/<new_module>/`）

**模块所有权 / 环境变量:** 按模块前缀组织（如 `SAFETY_AI_TEXT_MODEL`、`ENERGY_AUTO_COLLECT_ENABLED`）。

**模块所有权 / 全局层 vs 模块层:** 全局层（如 `app/core/llm/`）只提供通用基础设施 API。业务功能代码（prompt、业务逻辑、错误处理）必须在模块内部，不得放到全局层。

**跨模块通信:**
- 默认方式：通过目标模块的 `public_api.py` 直接调用（适用于所有需要返回值的场景）。
- 事件总线（`app/core/events.py`）：仅用于"通知"场景——生产者不需要知道谁在监听。
  - 适用：审计日志、通知分发、缓存失效
  - 不适用：数据查询、校验、任何需要返回值的操作
  - 事件命名：`{module}.{entity}.{action}`（如 `employee.created`、`batch.status_changed`）

### Cross-module import rule (precise)

For code in `backend/app/modules/<source_module>/**/*.py`:

**Allowed:** imports from the same module or from `public_api.py` of another module:
```python
from app.modules.safety.repository import SafetyRepository  # same module
from app.modules.energy.public_api import fetch_summary      # public API
```

**Violation:** any import from another module that is NOT through `public_api.py`:
```python
from app.modules.energy.repository import EnergyRepository   # VIOLATION
from app.modules.energy.service import EnergyService         # VIOLATION
from app.modules.energy.models import EnergyRecord           # VIOLATION
from app.modules.energy.internal_util import calculate_cost  # VIOLATION
from app.modules.energy.schemas import EnergyResponse        # VIOLATION
from app.modules.energy.api import router                    # VIOLATION
import app.modules.energy.service as es                      # VIOLATION
```

**Candidate:** broad package import that may bypass boundary:
```python
from app.modules import energy  # candidate — later energy.service.X bypasses public_api
```

**Explicit exceptions** are documented in `docs/ai-audit-findings.md` under accepted exceptions.
Do NOT inspect what `public_api.py` exports to decide publicness. Other modules must import through `public_api.py`, not merely import things `public_api.py` also uses.

### Directories to inspect
- `backend/app/modules/` (all 12 modules)
- `backend/app/core/`
- `backend/app/shared/`
- `backend/app/platform/`

### Questions

1. Are there any cross-module imports NOT through `public_api.py`?
   (Scan every Python file in `backend/app/modules/` for imports from `app.modules.<other_module>.*` where `<other_module>` is different from the current module and `*` is not `public_api`. Note: imports within the same module do NOT need to go through `public_api.py`)
2. Are there any `from app.modules import <module>` broad package imports that enable boundary bypass?
3. Are there any circular imports between modules? (A imports from B, B imports from A)
4. Has any new module directory been created under `backend/app/modules/`? Is new functionality placed in existing modules as required (new modules only created with explicit user approval)?
5. Is there any business logic (prompts, business rules, domain-specific error handling) in `app/core/` or `app/shared/` that belongs in a module?
6. Do environment variable names follow the module prefix convention?
7. Do event names follow the `{module}.{entity}.{action}` format?
8. Is the event bus being used for data queries or validation (which require return values) instead of `public_api.py`?

### Output format

| Stat | Count |
|------|-------|
| Files inspected | |
| Files not inspected | |
| Rules evaluated | |
| Rules not evaluated | |
| Confirmed findings | |
| Uncertain findings | |

Each finding:
```
file:line — rule reference — evidence (import statement) — severity: blocking|high|medium|low
```

---


## 4. API and authentication

### Audit type
Full audit

### Rules (from AGENTS.md)

**API 规范:**
- 所有路由挂载在 `/api/v1` 下，按模块组织：`/api/v1/<module>/<resource>`
- 标准形式：
  ```
  GET    /api/v1/{module}/
  POST   /api/v1/{module}/{resource}
  GET    /api/v1/{module}/{resource}
  GET    /api/v1/{module}/{resource}/{id}
  PUT    /api/v1/{module}/{resource}/{id}
  DELETE /api/v1/{module}/{resource}/{id}
  ```

**API 规范 / 必须:**
- 入参和出参使用本模块 `schemas.py`
- 返回格式使用 `app/core/response.py`
- 业务异常使用 `app/core/exceptions.py`
- 删除业务数据默认软删除（`is_deleted`），不做物理删除（除非需求明确要求）

**禁止** `response_model=dict`：所有结构化 JSON 响应的 endpoint 必须使用具体的 Pydantic 响应模型，且该模型必须描述完整的实际响应体（包括 `code`、`data`、`message` 等实际返回字段），不能仅描述 `data`。具体业务响应模型定义在对应模块的 `schemas.py` 中。

`response_model=dict` 会生成缺乏具体字段类型的 OpenAPI schema（如 `{type: object}`），导致前端无法获得可靠的生成类型。

正常结构化 JSON 成功响应必须通过 `build_response()` 构建并直接返回 Pydantic 数据，由 FastAPI 根据声明的 `response_model` 负责响应校验、序列化和 OpenAPI schema 生成；不得通过 `success_response()` 返回 `JSONResponse` 绕过该流程。文件下载、流式响应、重定向等需要直接控制 HTTP Response 的场景除外。

**认证与权限:**

认证来源：`Authorization: Bearer <jwt>` header 或 `auth_token` cookie（飞书 SSO）。

**依赖注入** — 从 `app.core.deps` 导入。新增业务接口必须显式选择以下三者之一：

```python
from app.core.deps import RequiredUser, OptionalUser
```

| 选项 | 参数声明 | 类型 | 未登录行为 | 使用场景 |
|---|---|---|---|---|
| `RequiredUser` | `current_user: RequiredUser` | `User` | 返回 401 | **默认**。所有业务 API 必须使用 |
| `OptionalUser` | `current_user: OptionalUser` | `User \| None` | 返回 `None`（端点可判断） | 少数场景：AI 工具、公开参考数据等允许未登录访问的接口 |
| public（不注入） | 不声明 `current_user` 参数 | — | 不解析用户 | 仅 SSO 认证流程、飞书 webhook 回调、E2E 测试 |

`OptionalUser` 与 public 的区别：`OptionalUser` 仍然会解析 JWT/cookie，端点可以拿到用户信息做条件逻辑。public 完全不解析，适合无需用户上下文的端点。

**默认规则：**
- 所有业务 API 默认需要登录，使用 `RequiredUser`
- 新增业务接口时必须从 `RequiredUser` / `OptionalUser` / public（不声明参数）中显式选择
- 未声明的业务接口按 `RequiredUser` 处理

**公开接口（无需登录）：**

| 端点 | 原因 | 认证方式 |
|---|---|---|
| `GET /api/v1/identity/auth/login` | 飞书 SSO 登录入口 | 无 |
| `GET /api/v1/identity/auth/callback` | 飞书 SSO 回调 | 无 |
| `GET /api/v1/identity/auth/logout` | 登出 | 无 |
| `POST /api/v1/identity/auth/test-login` | E2E 测试专用 | `APP_ENV` 环境变量守卫 |
| `POST /api/v1/hr/webhook/feishu-approval` | 飞书审批回调 | 飞书验证 token + 签名 |

**Feishu Webhook 处理：**

飞书 HTTP 回调（webhook）**禁止**使用 `RequiredUser` —— 这是服务器到服务器的回调，没有用户会话。

**必须**按 Feishu 标准协议验证请求来源：
1. **验证 Token 检查**：飞书事件 payload 包含 `token` 字段，必须与 Feishu 应用配置的 Verification Token 比对
2. **签名验证**（如配置了 encrypt_key）：`SHA256(timestamp + nonce + encrypt_key + raw_body)`，通过 `hmac.compare_digest` 比对

验证函数复用 `app/platform/identity/service.py` 中的 `_verify_feishu_callback_signature()`。

**禁止**在 webhook 端点中：
- 使用 `RequiredUser` 或 `get_current_user`
- 不验证 token 直接处理 payload
- 在 `_verify_feishu_callback_signature` 缺少字段时放行

### Directories to inspect
- `backend/app/modules/**/api.py`
- `backend/app/modules/**/schemas.py`
- `backend/app/api/router.py`
- `backend/app/core/response.py`
- `backend/app/core/exceptions.py`
- `backend/app/core/deps.py`
- `backend/app/platform/identity/service.py`

### Questions

1. Are all routes prefixed with `/api/v1/<module>/` where `<module>` matches the module name?
2. Do all API endpoints use request/response schemas from their own module's `schemas.py`?
3. Are all responses using the standard response format from `app/core/response.py`?
4. Are business logic errors using `app/core/exceptions.py` (not generic HTTPException)?
5. Do DELETE operations use soft delete (`is_deleted` flag) instead of physical deletion?
6. Does each endpoint explicitly declare its auth requirement (`RequiredUser`, `OptionalUser`, or public)?
7. Are any business API endpoints using `OptionalUser` or public when they should use `RequiredUser`?
8. Do Feishu webhook endpoints verify the request using `_verify_feishu_callback_signature()` from `app/platform/identity/service.py`?
9. Are Feishu webhook endpoints free of `RequiredUser`, `get_current_user`, and missing token verification?
10. Do webhook handlers return the challenge response for Feishu URL verification?
11. Are there any endpoints using `response_model=dict`?
12. Do structured JSON endpoints return Pydantic data via `build_response()` instead of `success_response()` → `JSONResponse`?
13. For endpoints with typed response models, does the model describe the full response body (including `code`, `data`, `message` fields), not just the inner `data` type?

### Output format

| Stat | Count |
|------|-------|
| Files inspected | |
| Files not inspected | |
| Rules evaluated | |
| Rules not evaluated | |
| Confirmed findings | |
| Uncertain findings | |

Each finding:
```
file:line — rule reference — evidence — severity: blocking|high|medium|low
```

---


## 5. Models and migrations

### Audit type
Full audit

### Rules (from AGENTS.md)

**ORM 规则 / 必须:**
- 业务模型继承 `app/shared/base_model.py` 中的 `BaseModel`
- 每张表必须有 `__tablename__` 和 `__table_args__ = {"schema": "<module_schema>"}`
- 字段命名使用英文 `snake_case`，显式声明唯一约束、索引
- 新增 schema 时同步更新 `app/shared/module_registry.py`

**ORM 规则 / Schema 管理:**
- 所有数据库 schema 变更必须通过 Alembic 迁移管理
- 禁止使用 `Base.metadata.create_all()` 或 `create_all()` 创建表
- 新增/修改模型后必须运行 `alembic revision --autogenerate` 生成迁移
- 迁移必须遵守单模块原则（每个迁移只涉及一个模块的表）

**外键约束:**
- 允许外键约束（包括跨模块），但必须避免级联删除（CASCADE DELETE）跨模块使用
- 跨模块关系必须明确记录在设计文档中，禁止循环外键依赖
- 对高风险删除操作必须使用软删除或应用层控制
- 禁止修改已合并或执行过的历史 migration（除非用户明确要求）

**迁移规范 / 命名:**
- 迁移文件必须使用顺序编号格式 `NNNN_descriptive_name.py`，NNNN 是 4 位数字（如 `0001`、`0002`）
- Revision ID 也应遵循相同模式（如 `0001_baseline`、`0002_drop_product`）
- 禁止使用 Alembic 自动生成的哈希 ID（如 `3cb28d1e1ac7`）

**迁移规范 / 初始基线例外:**
- `0001_baseline_full_schema` 迁移允许跨所有 schema

**迁移规范 / 单模块原则:**
- 基线之后的每个迁移文件只能修改一个模块的 schema
- 跨模块外键、`platform`/`core`/`shared` 级变更可以跨 schema，但必须由架构负责人审批
- CI 会自动检查（`scripts/ci/check_migration_scope.py`）

**Model-Migration 绑定:**
- 任何 SQLAlchemy Model 的新增、删除、字段修改、索引修改、约束修改，都必须在同一个 PR/commit 中包含对应 Alembic migration

**Model-Migration 绑定 / 禁止:**
- 只改 model，不生成 migration
- 只改数据库，不改 model
- 在生产环境运行 `alembic revision --autogenerate`
- 执行包含无关 `DROP TABLE` / `DROP COLUMN` 的自动生成 migration

**Orphan Table:**
- 数据库中存在但当前代码没有 model 的表，不得自动删除
- 必须查询 row count、检查代码引用、确认业务负责人是否需要保留、完成备份后，明确批准才允许创建 DROP migration

### Directories to inspect
- `backend/app/modules/**/models.py`
- `backend/alembic/versions/`
- `backend/app/shared/base_model.py`
- `backend/app/shared/module_registry.py`

### Questions

1. Do all business models inherit `app/shared/base_model.py` BaseModel?
2. Do all model classes define `__tablename__` and `__table_args__ = {"schema": "..."}`?
3. Are there any `Base.metadata.create_all()` or `create_all()` calls in the codebase?
4. Do all migration filenames follow the `NNNN_descriptive_name.py` pattern? (flag any that start with a hash)
5. Do all migration `revision` IDs follow the NNNN pattern (not hash-based)?
6. Does each migration (after `0001`) touch only one module's schema tables?
7. Are there any model changes without a corresponding migration in the same commit?
8. Are there any `DROP TABLE` or `DROP COLUMN` operations in migrations without documented approval?
9. Are there any `CASCADE DELETE` foreign keys across module boundaries?
10. Are there any circular foreign key dependencies?
11. Is `module_registry.py` updated when a new schema is introduced?

### Output format

| Stat | Count |
|------|-------|
| Files inspected | |
| Files not inspected | |
| Rules evaluated | |
| Rules not evaluated | |
| Confirmed findings | |
| Uncertain findings | |

Each finding:
```
file:line — rule reference — evidence — severity: blocking|high|medium|low
```

---


## 6. Configuration and logging

### Audit type
Full audit

### Rules (from AGENTS.md)

**配置管理 / 两层:**
- 部署配置（Deployment Settings）: `.env` + `core/config.py` — API keys, database, Feishu credentials
- 运行时配置（Runtime Settings）: `core.module_settings` table + module settings pages — model names, feature flags, scheduling params

**配置管理 / 读取:**
```python
# 运行时配置（从数据库）
from app.shared.config_reader import get_module_setting, get_module_setting_bool

# 部署配置（从环境变量）
from app.core.config import get_settings
```

**配置管理 / 新增:**
- LLM API keys → Admin UI, encrypted in `core.llm_configs`
- Other API keys/credentials → `core/config.py` Settings class
- Model names/feature flags/operational params → `scripts/seed/seed_module_settings.py` + Web UI

**配置管理 / 禁止:**
- 在模块代码中使用 `os.getenv()` 读取运行时配置（允许例外：为 subprocess 设置环境变量）
- 将 API key 等凭证明文存入数据库（必须使用加密）
- 在 `core/config.py` 中存放模型名称等频繁变更的配置

**飞书凭证:**
- 嵌套结构，按模块分组在 `FeishuSettings` 类中
- 环境变量命名：双下划线分隔 `FEISHU__{MODULE}__{FIELD}` 或 `FEISHU__{MODULE}__CREDENTIALS__{FIELD}`

**环境变量同步:** 新增/修改 `.env` 文件时，必须同步修改 `.env.example`。

**日志规范:**
- 每个模块使用 `logger = logging.getLogger(__name__)`
- 级别：`ERROR`（失败）、`WARNING`（降级/重试）、`INFO`（业务事件）、`DEBUG`（开发调试）
- 始终包含上下文：`logger.info("batch created", extra={"batch_id": id, "module": "production"})`
- 异常处理用 `logger.exception()`（自动附带 traceback）
- 禁止记录 API key、token、密码等敏感信息

### Directories to inspect
- `backend/app/core/config.py`
- `backend/app/shared/config_reader.py`
- `backend/app/modules/` (all Python files)
- `.env`
- `.env.example`
- `backend/scripts/seed/seed_module_settings.py`

### Questions

1. Is `os.getenv()` used for runtime configuration in any module? (Allowed only in `core/config.py` or for subprocess env vars)
2. Are there any API keys or credentials stored in plaintext in the database or configuration files?
3. Are model names or frequently changed configuration values stored in `core/config.py` instead of `module_settings`?
4. Does every module use `logger = logging.getLogger(__name__)`?
5. Are log calls using `extra={}` for structured context?
6. Are exceptions logged with `logger.exception()`?
7. Are there any sensitive values (API keys, passwords, tokens) in log messages?
8. Do Feishu environment variables follow the `FEISHU__{MODULE}__{FIELD}` naming format?
9. Is `.env.example` in sync with `.env`? (Check for variables in `.env` missing from `.env.example`)

### Output format

| Stat | Count |
|------|-------|
| Files inspected | |
| Files not inspected | |
| Rules evaluated | |
| Rules not evaluated | |
| Confirmed findings | |
| Uncertain findings | |

Each finding:
```
file:line — rule reference — evidence — severity: blocking|high|medium|low
```

---


## 7. External services and background tasks

### Audit type
Full audit

### Rules (from AGENTS.md)

**LLM 调用规范:**
- 使用全局单例 `llm_client`（`app/core/llm/`），不要手动构造客户端
- API keys → 加密存储在 `core.llm_configs` 表，加密密钥 `LLM_ENCRYPTION_KEY` 在环境变量中
- 异常处理：使用 `LLMOutputError`、`LLMProviderError`、`LLMRateLimitError`

**文件存储与 OCR:**
- 文件存储：使用 `app/core/storage.py`（MinIO/S3 兼容），每个模块拥有独立 bucket
- OCR 服务：使用 `app/shared/ocr_service.py` 中的 `get_ocr_service()`

**文件存储与 OCR / 禁止:**
- 在模块中直接 import `paddleocr` 或自行初始化 OCR 引擎
- 在测试中初始化真实 OCR 服务（必须 mock `get_ocr_service`）

**异步任务:**
- 长运行进程（WebSocket 客户端、事件监听）：使用 `register_background_worker()`
- 周期性任务：使用 `SchedulerEngine` + `TaskDefinition`（静态任务）或 `TaskGenerator`（DB 驱动动态任务）
- 一次性异步任务：使用任务队列（`app/core/jobs.py`）

**异步任务 / 禁止:**
- 直接使用 APScheduler（必须用 SchedulerEngine）
- 自定义 `asyncio` 循环（必须用 BackgroundWorker）
- `asyncio.create_task()` 处理业务逻辑（例外：长运行后台工作进程内部的心跳、事件分发等基础设施任务）
- 在 HTTP 请求中执行超过 5 秒的操作（应改为异步任务 + 轮询状态）

**错误处理与容错:**
- 重试策略：外部调用（LLM、飞书、能耗平台等）最多 3 次重试，指数退避（1s, 2s, 4s）。所有重试操作必须是幂等的。

**错误处理 / 降级策略:**
- LLM 不可用 → 返回默认值 + 提示"AI 分析暂时不可用，请人工审核"
- 飞书 API 不可用 → 记录到待发送队列，后台重试
- 外部数据源不可用 → 显示"数据暂时不可用"，不阻塞其他功能
- 缓存失效 → 回源查询，不返回错误

**错误处理 / 禁止:**
- 吞掉异常（`except: pass` 或 `except Exception: pass`）
- 无限重试（必须设置 `max_retries`）
- 在循环中不处理异常（会导致整个后台任务崩溃）
- 在后台任务中抛出未捕获异常（必须 `try/except` + `logger.exception`）

### Directories to inspect
- `backend/app/modules/` (all Python files)
- `backend/app/core/llm/`
- `backend/app/core/storage.py`
- `backend/app/core/jobs.py`
- `backend/app/core/tasks.py`
- `backend/app/shared/ocr_service.py`

### Questions

1. Is there any direct LLM client construction (`openai.OpenAI(...)`, `AsyncOpenAI(...)`) instead of using the `llm_client` singleton?
2. Are there direct `import paddleocr` or `from paddleocr import ...` calls in module code?
3. Are there direct `import apscheduler` or `from apscheduler import ...` calls?
4. Are there `asyncio.create_task()` calls in business logic files (not in `core/`, `platform/`, or background worker infrastructure)?
5. Are there HTTP handler functions that perform operations taking longer than 5 seconds without offloading to a job queue?
6. Are there `except: pass` or `except Exception: pass` patterns (bare exception swallowing)?
7. Are retries implemented with bounded `max_retries` and exponential backoff?
8. Are there unhandled exceptions in background tasks or loops?
9. Are external service dependencies (LLM, Feishu, MinIO) properly mocked in tests?

### Output format

| Stat | Count |
|------|-------|
| Files inspected | |
| Files not inspected | |
| Rules evaluated | |
| Rules not evaluated | |
| Confirmed findings | |
| Uncertain findings | |

Each finding:
```
file:line — rule reference — evidence — severity: blocking|high|medium|low
```

---


## 8. Backend tests

### Audit type
Full audit

### Rules (from AGENTS.md)

**测试规范:**
- 框架：pytest + pytest-asyncio。`pyproject.toml` 中配置了 `asyncio_mode = "auto"`，`async def test_*` 函数会被自动识别为异步测试，不需要 `@pytest.mark.asyncio` 装饰器。
- 覆盖优先级：service 层业务逻辑 > API 端点契约 > repository 查询。
- 外部服务：LLM、飞书、MinIO 等外部依赖必须 mock，不要在测试中调用真实服务。
- 运行：
  ```bash
  uv run pytest                                    # 全量
  uv run pytest tests/modules/<module>/            # 单模块
  uv run pytest tests/modules/<module>/ -k "test_name"  # 单个用例
  ```

### Directories to inspect
- `backend/tests/`

### Questions

1. Are tests organized in the correct directories (`tests/modules/<module>/`, `tests/unit/`, `tests/integration/`)?
2. Are external services (LLM, Feishu, MinIO) mocked in tests?
3. Are async test functions using the auto asyncio mode correctly (no unnecessary `@pytest.mark.asyncio` decorator)?
4. Are OCR service calls mocked via `get_ocr_service`?
5. Do test files roughly follow the coverage priority (service > API > repository)?

### Output format

| Stat | Count |
|------|-------|
| Files inspected | |
| Files not inspected | |
| Rules evaluated | |
| Rules not evaluated | |
| Confirmed findings | |
| Uncertain findings | |

Each finding:
```
file:line — rule reference — evidence — severity: blocking|high|medium|low
```

---


## 9. Frontend component boundaries

### Audit type
Full audit

### Rules (from AGENTS.md)

**Server Component vs Client Component:**
- `page.tsx` 默认是 Server Component，**不加** `'use client'`
- 必须加 `'use client'`：使用了 hooks、浏览器 API、事件处理器、antd `App.useApp()`、Zustand store、直接在页面中使用 antd 组件
- 不需要 `'use client'`：页面只是导入并渲染 Client Component、导出 `generateMetadata`、`async function` 获取数据后传给 Client 组件
- 判断标准：如果页面 JSX 使用了 antd 组件 → 需要 `'use client'`；如果页面只是 `<ClientComponent />` → 不需要

**Barrel 文件规则:**
- 导出使用 Zustand store 或 React Context 的组件时，barrel 必须加 `'use client'`（否则构建报错）
- 其他 barrel 建议统一加 `'use client'`（最佳实践，防止未来引入 store 导入时构建失败）

**动态渲染:**
- Server Component 页面如果调用后端 API，必须在页面顶部添加 `export const dynamic = 'force-dynamic'`
- 原因：Next.js 默认静态预渲染，但后端 API 在构建时不可用

**模块边界:**
- 禁止跨模块直接 import 组件内部文件。只能从该模块的 `index.ts` 导入：
  ```
  ✗ import { BatchForm } from '@/components/production/BatchForm'
  ✓ import { BatchTable } from '@/components/production'
  ```

**命名规范:**
- 组件文件：PascalCase（`BatchTable.tsx`）
- 非组件文件：camelCase（`useBatch.ts`、`batchApi.ts`）
- Server Action 函数：动词开头（`createBatch`、`updateBatch`、`submitApproval`）
- API 请求函数：以 `fetch` 开头（`fetchBatches`、`fetchBatchById`）

**禁止修改的文件:**
- `src/proxy.ts`
- `src/components/shared/` 下所有文件
- `src/hooks/usePermission.ts`

### Directories to inspect
- `frontend/src/app/`
- `frontend/src/components/`
- `frontend/src/stores/`
- `frontend/src/hooks/`

### Questions

1. Are there page.tsx files using antd components (Card, Row, Col, Button, etc.) without `'use client'`?
2. Are there page.tsx files that call backend APIs (via `actions/`) without `export const dynamic = 'force-dynamic'`?
3a. Are there barrel `index.ts` files that export Zustand/Context components but are missing `'use client'`?
3b. Are there other barrel `index.ts` files missing `'use client'` (violates best practice, not a build error)?
4. Are there imports from a different module's component directory that bypass the target module's `index.ts` barrel? (Same-module sub-path imports are not violations — the rule only applies across module boundaries.)
5. Do component file names follow PascalCase? Do non-component file names follow camelCase?
6. Do Server Action function names start with a verb (`create`, `update`, `delete`, `submit`, etc.)?
7. Do API request function names start with `fetch`?
8. Has `proxy.ts`, `components/shared/`, or `hooks/usePermission.ts` been modified in a way that requires architecture approval?
9. Does every `page.tsx` have a semantic `<h1>` heading (using `<h1>` or `<Title level={1}>`) that is NOT provided via `<Card title="...">`?

### Output format

| Stat | Count |
|------|-------|
| Files inspected | |
| Files not inspected | |
| Rules evaluated | |
| Rules not evaluated | |
| Confirmed findings | |
| Uncertain findings | |

Each finding:
```
file:line — rule reference — evidence — severity: blocking|high|medium|low
```

---


## 10. Frontend API and generated types

### Audit type
Full audit

### Rules (from AGENTS.md)

**表单与数据校验:**
- 前端表单默认使用 Ant Design Form。使用 `Form.Item` 的 `rules` 属性进行 UI 校验。
- 禁止：在没有明确理由的情况下，将现有的 Ant Design Form 迁移到 React Hook Form 或 Zod。

**Zod 使用场景 (仅数据边界):**
1. Server Actions 的复杂输入
2. Excel/CSV 文件导入
3. LLM 结构化输出
4. 环境变量校验
5. 复杂的数据转换
- 不适用：普通表单字段校验（用 Ant Design Form rules）、简单 API 响应处理（用 TypeScript 类型）

**写操作必须用 Server Actions:**
- 所有 POST/PUT/DELETE 操作写在 `actions/` 目录
- 禁止在 Client 组件里直接 fetch 写接口
- 例外：流式响应（SSE/ReadableStream）或上传进度追踪，允许在 `lib/api/client/` 中直接 fetch
- **避免在 `'use server'` 文件中定义类型**（`export type` 或 `export interface`）。类型定义应集中在 `types/` 目录中，以防止重复定义和类型不一致。

**类型系统 / API 类型来源:**
- 所有 API 相关的类型（请求参数、响应数据）必须从 `@/types/generated/schema` 导入
- 禁止手写 API 类型
  ```
  ✗ export async function updateRoute(id: string, data: { name?: string; status?: string })
  ✓ import type { RouteUpdate } from '@/types/generated/schema'
  ```

- 判断标准：如果类型用在 `fetch()`、`apiGet()`、`apiPost()`、`apiFetch()` 或任何 API 调用中，就是 API 契约类型，必须使用生成类型。UI 类型（表单状态、组件 props、本地状态）可以手写。
**类型系统 / API 调用层级:**
- `frontend/src/types/generated/` ← 自动生成，禁止编辑
- `frontend/src/lib/api/client/*.ts` ← 浏览器 GET/list/search/detail，使用 `/api/v1/...`
- `frontend/src/lib/api/server/*.ts` ← Server Component / Server Action，使用 `API_BASE_URL`
- `frontend/src/actions/*.ts` ← Server Actions，调用 lib/api

**类型检查:**
- CI 检查：`bash scripts/ci.sh openapi`
- 生成命令：`cd ../frontend && pnpm generate:api`

### Directories to inspect
- `frontend/src/actions/`
- `frontend/src/lib/api/`
- `frontend/src/types/`
- `frontend/src/components/` (for component-internal fetch calls)

### Questions

1. Are there any handwritten API types (inline object type annotations as function parameters) in `actions/` or `lib/api/` instead of using `@/types/generated/schema`?
2. Are there any POST/PUT/DELETE fetch calls directly in Client Components (outside `actions/` directory)?
3. Are there server-side API calls (`lib/api/server/`) using relative paths (e.g. `/api/v1/...`) instead of `API_BASE_URL`?
4. Are there client-side API calls (`lib/api/client/`) using `API_BASE_URL` instead of relative paths?
5. Is Zod being used for simple form validation (where Ant Design Form `rules` would be appropriate)?
6. Are generated types (`@/types/generated/schema.ts`) committed and up to date with the backend?
7. Is the `types/generated/` directory free of manual edits?
8. Are there duplicate type definitions across `actions/` and `types/`? Are action return types consistent with the types that components import?
9. Are there any duplicate `getApiBaseUrl()` implementations in `lib/api/server/` files other than `base.ts`? (Only `base.ts` may define this function.)
10. Are there any custom `apiFetch` implementations (function named `apiFetch` with fetch logic) in `lib/api/server/` files other than `base.ts`? Note: `safeApiFetch` and `apiFetchPaginated` in `base.ts` are canonical first-class exports, not custom `apiFetch` violations.
11. Are there ad-hoc `.data` access patterns at call sites instead of using `unwrapResponse()`? (Patterns like `response.data`, `result?.data`, `(result as any)?.data`)

### Output format

| Stat | Count |
|------|-------|
| Files inspected | |
| Files not inspected | |
| Rules evaluated | |
| Rules not evaluated | |
| Confirmed findings | |
| Uncertain findings | |

Each finding:
```
file:line — rule reference — evidence — severity: blocking|high|medium|low
```

---


## 11. Proxy and routing

### Audit type
Full audit

### Rules (from AGENTS.md)

**proxy.ts 规则 / 允许:**
- 将 `/api/v1/*` 转发到后端
- 透传 HTTP method、body、headers 和 cookies
- 保持流式响应和 SSE 行为
- 仅判断 session cookie 或 token 是否存在
- 将明显未登录的页面请求重定向到 `/login`
- 通过 `matcher` 排除公开路由和静态资源

**proxy.ts 规则 / 禁止:**
- 调用数据库或 API 验证 token
- 角色、权限或模块访问判断
- 业务规则和模块专属逻辑
- 请求或响应数据转换
- LLM 调用
- 审计日志写入
- 数据库访问
- 将 proxy.ts 的检查视为正式授权结果

**路由转发:**
- 客户端代码使用相对路径 `/api/v1/...`
- 服务器端代码使用 `API_BASE_URL` 环境变量
- 禁止硬编码后端地址、`NEXT_PUBLIC_API_BASE_URL`、绝对文件路径、硬编码 `localhost:3000`

**新增 API 调用:**
1. 客户端调用：`lib/api/client/<module>.ts` + 相对路径 `/api/v1/...`
2. 服务器端调用：`lib/api/server/<module>.ts` + `API_BASE_URL`
3. 写操作：`actions/<module>.ts` 调用 `lib/api/server/` 函数

### Directories to inspect
- `frontend/src/proxy.ts`
- `frontend/src/lib/api/`
- `frontend/src/actions/`

### Questions

1. Does `proxy.ts` contain any of the prohibited operations (database access, auth validation, business logic, LLM calls, audit logging, data transformation)?
2. Does `proxy.ts` properly forward `/api/v1/*` to the backend using `API_BASE_URL` or its default?
3. Are there any hardcoded backend URLs in frontend source code?
4. Are all client-side API calls using relative paths (`/api/v1/...`)?
5. Are all server-side API calls using `API_BASE_URL` environment variable?
6. Do Server Actions call functions from `lib/api/server/` rather than directly fetching?

### Output format

| Stat | Count |
|------|-------|
| Files inspected | |
| Files not inspected | |
| Rules evaluated | |
| Rules not evaluated | |
| Confirmed findings | |
| Uncertain findings | |

Each finding:
```
file:line — rule reference — evidence — severity: blocking|high|medium|low
```

---


## 12. Cross-project OpenAPI

### Audit type
CI verification only — CI already enforces via `scripts/ci.sh openapi`

### Rules (from AGENTS.md)

**仓库通用规则:**
- 前后端之间的交叉引用必须通过公共契约（OpenAPI spec）

**跨项目 CI:**
- `openapi` — 后端导出 OpenAPI spec → 前端生成类型 → 检查漂移

**前端 / 类型检查:**
- CI 会检查生成的类型是否与后端同步，不同步的 PR 无法合并
- 生成脚本：`frontend/scripts/generate-api.mjs`
- 生成文件：`frontend/src/types/generated/schema.ts`、`frontend/src/types/generated/openapi.json`

### Directories to inspect
- `backend/openapi.json`
- `frontend/src/types/generated/`
- `scripts/ci.sh`

### Questions

1. Does `scripts/ci.sh openapi` pass in CI?
2. Is `frontend/src/types/generated/schema.ts` committed and up to date?
3. Is `frontend/src/types/generated/openapi.json` committed and matching `backend/openapi.json`?

### Output format

| Stat | Count |
|------|-------|
| Checks verified | |
| Checks failing | |

---


## 13. Docker and deployment

### Audit type
Full audit

### Rules (from AGENTS.md)

**Docker 开发环境:**
- 前端使用**单文件多阶段构建**（`frontend/Dockerfile`），包含四个阶段：
  - **base** — 共享基础：Node 22 Alpine、pnpm 10.33.0、依赖安装
  - **dev** — 开发阶段：复制源代码，运行 `pnpm dev`，支持热更新
  - **builder** — 生产构建阶段：运行 `pnpm build`
  - **runtime** — 生产运行阶段：仅包含 standalone 输出，运行 `node server.js`
- 三种 docker-compose 配置：
  - `docker-compose.yml` — 生产环境（`target: runtime`，无热更新）
  - `docker-compose.dev.yml` — 开发覆盖（`target: dev`，有热更新）
  - `docker-compose.ci.yml` — CI 环境（`target: runtime`，用于 E2E 测试）
- 开发时必须使用：
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
  ```

**基础设施文件审批**（见 AGENTS.md "仓库通用规则" 章节）:
- 以下文件修改前**必须**获得批准：
  - `frontend/Dockerfile`
  - `backend/Dockerfile`
  - `docker-compose.yml`
  - `docker-compose.dev.yml`
  - `docker-compose.ci.yml`

### Directories to inspect
- `frontend/Dockerfile`
- `backend/Dockerfile`
- `docker-compose.yml`
- `docker-compose.dev.yml`
- `docker-compose.ci.yml`
- `nginx/`

### Questions

1. Does `frontend/Dockerfile` use multi-stage build with correct stage names (base, dev, builder, runtime)?
2. Does `docker-compose.yml` specify `target: runtime` for the frontend service?
3. Does `docker-compose.dev.yml` specify `target: dev` for the frontend service?
4. Does `docker-compose.ci.yml` specify `target: runtime` for the ci-build service?
5. Are the docker-compose files consistent (service names, port mappings, volume mounts)?
6. Are there any hardcoded sensitive values in Docker or nginx configuration that should be environment variables?
7. Is `frontend/Dockerfile.dev` deleted (should not exist after consolidation)?
8. Are all Dockerfile and docker-compose changes documented with approval in the PR?

### Output format

| Stat | Count |
|------|-------|
| Files inspected | |
| Files not inspected | |
| Rules evaluated | |
| Rules not evaluated | |
| Confirmed findings | |
| Uncertain findings | |

---
## 14. E2E

### Audit type
CI verification only — CI already enforces via `scripts/ci.sh e2e`

### Rules (from AGENTS.md)

**跨项目 CI:**
- `e2e` — 启动服务（PostgreSQL + 后端 + 前端）→ 运行 Playwright → 清理

### Directories to inspect
- `frontend/e2e/`
- `frontend/playwright.config.ts`
- `scripts/ci.sh`

### Questions

1. Does `scripts/ci.sh e2e` pass in CI?
2. Are Playwright tests organized and maintained?
3. Is the CI service setup (PostgreSQL + backend + frontend) functioning?

### Output format

| Stat | Count |
|------|-------|
| Checks verified | |
| Checks failing | |

---


## Rules not directly auditable

These AGENTS.md sections are architectural guidance, procedural documentation, or already CI-enforced. They are noted but not audited.

| AGENTS.md section | Reason |
|---|---|
| 架构原则 (modular monolith, tech stack) | Architectural intent, not a pass/fail rule |
| 代码格式规范 (E501, ruff per-file-ignores) | CI-enforced by `ruff check` |
| 前端/技术栈 (Next.js 16, Ant Design v6) | Architectural intent |
| 前端/新增页面的步骤 | Procedural guidance |
| 模块结构 (see examples/) | Referenced documentation |
| 开发指南 (see backend/docs/) | Referenced documentation |
| 错误处理/降级策略 (LLM unavailable -> default) | Design guidance, implementation patterns vary |
| 前端/表单与数据校验 (Zod usage) | Procedural guidance, not a pass/fail rule |
| 后端/认证与权限 (Feishu Webhook 处理) | Architectural patterns, implementation varies by webhook endpoint |

---

## Explicit exceptions from AGENTS.md

AGENTS.md includes exception clauses that auditors must check before reporting a rule violation. A finding is NOT a violation if it matches one of these exceptions.

| Exception | Rule it modifies | Category |
|---|---|---|
| Prompt/knowledge base/test fixture files excluded from E501 line length check. Maintained in `pyproject.toml` `[tool.ruff.lint.per-file-ignores]`. | 代码格式规范 — 120 char limit | 3 |
| `0001_baseline_full_schema` migration allowed to span all schemas. | 迁移规范 — 单模块原则 | 5 |
| Cross-module FK, `platform`/`core`/`shared`-level changes can span schemas with architecture lead approval. | 迁移规范 — 单模块原则 | 5 |
| Historical migrations may be modified "除非用户明确要求" (only when user explicitly requires). | 迁移规范 — 禁止修改历史 migration | 5 |
| `os.getenv()` allowed for setting subprocess environment variables. | 配置管理 — 禁止 os.getenv() | 6 |
| `asyncio.create_task()` allowed in long-running background worker processes for heartbeats, event dispatch, and infrastructure tasks. | 异步任务 — 禁止 asyncio.create_task() | 7 |
| Soft delete default; physical delete allowed "除非需求明确要求" (when requirements explicitly require). | API 规范 — 强制软删除 | 4 |
| SSE/ReadableStream streaming responses and upload progress tracking allowed to use direct fetch in `lib/api/client/`. | 写操作必须用 Server Actions | 10 |
| `'use server'` files may re-export types from `types/` via `export type { ... } from '@/types/...'` (not defining types directly). | `'use server'` 文件禁止 export type/interface | 10 |
| `components/<module>/index.ts` barrel files — `'use client'` is "最佳实践" (best practice), not a hard requirement when components only use basic hooks. | Barrel 文件规则 | 9 |
| Birdirectional dependency: module may import from itself freely (same module = allowed). | 模块所有权 — 禁止直接 import 内部文件 | 3 |
| FormData / file upload may use custom `uploadFetch<T>()` (`apiFetch` sets `Content-Type: application/json`, breaking multipart). | apiFetch 一致性 — 自定义 apiFetch | 10 |
| Streaming responses (SSE/ReadableStream) may use `apiFetchRaw` or raw fetch. | apiFetch 一致性 — 自定义 apiFetch | 10 |
| Login API (`loginApi` in `auth.ts`) may use raw `fetch()` because no auth token exists before login and the caller must distinguish HTTP status codes (401 vs 500) from business errors. | apiFetch 一致性 — 自定义 apiFetch | 10 |
| File download, streaming responses, and redirects may return the HTTP Response object directly (e.g. `FileResponse`, `StreamingResponse`) instead of `build_response()`. | API 规范 — 禁止 response_model=dict / 禁止 success_response() for structured JSON | 4 |
| Docker service discovery names (e.g., `http://backend:8000`) in docker-compose.yml and Dockerfile are allowed, not hardcoded URLs. | 仓库通用规则 — 禁止硬编码 URL | 2, 13 |
| Dummy credentials (e.g., `POSTGRES_PASSWORD: postgres`) in CI/test configuration files are allowed. | 仓库通用规则 — 禁止硬编码凭据 | 2, 13 |

---

## 15. SQL 注入与不安全查询

### Audit type
Full audit

### Rules (from AGENTS.md)

**后端 / 安全规则 / SQL 查询:**
- **必须**使用参数化查询（`:param` 占位符 + 绑定参数）或 SQLAlchemy ORM 构建所有 SQL 查询
- **禁止**使用 f-string、字符串拼接（`+`）或 `.format()` 将运行时数据嵌入 SQL 语句
- 所有外部数据源（包括飞书多维表格等内部系统）均视为不可信，必须参数化

### Directories to inspect
- `backend/app/modules/`
- `backend/app/core/`
- `backend/app/platform/`
- `backend/scripts/`

### Questions

1. Are there any f-strings, string concatenation (`+`), or `.format()` calls used to build SQL query strings (including inside `text()` calls)?
2. Are all `text()` SQL queries using bound parameters (`:param` syntax) with a separate parameter dict?
3. Are there any raw SQL strings constructed from external data sources (Feishu Bitable, user input, file imports, API responses) without parameterization?
4. Are all ORM queries using SQLAlchemy constructs (`and_`, `or_`, column comparisons) rather than string interpolation?
5. Are there any dynamic `ORDER BY`, `LIMIT`, or table/column name references built via string interpolation?

### Output format

| Stat | Count |
|------|-------|
| Files inspected | |
| Files not inspected | |
| Rules evaluated | |
| Rules not evaluated | |
| Confirmed findings | |
| Uncertain findings | |

Each finding:
```
file:line — rule reference — evidence — severity: blocking|high|medium|low
```

---

## Audit procedure

### Baseline audit (run once for the full repository)

For each category 1–15 in sequence:
1. Read this category's section above
2. Read the referenced AGENTS.md sections (including any exception clauses)
3. Check the [Explicit exceptions](#explicit-exceptions-from-agentsmd) table for this category
4. Inspect all listed directories
5. Answer every question — if a candidate matches a listed exception, do NOT report it as a finding
6. Report counts: files inspected, not inspected, rules evaluated, not evaluated
7. Record findings in `docs/ai-audit-findings.md`

After all 15 categories:
- Fix confirmed violations that should be corrected immediately
- Mark accepted exceptions with reason, approver, and date
- Commit `docs/ai-audit-findings.md`

### PR audit (run per pull request)

**Changed file** = any file listed by `git diff origin/main...origin/<pr-branch> --name-only`.
Audit ALL lines in that file. Do NOT filter findings against line-level diffs.
If the file is in the changed-file list, every line in it is in scope.

1. Get changed files: `git diff origin/main...origin/<pr-branch> --name-only`
2. Map changed files to affected categories (one file may map to multiple)
3. For each affected category, feed AI:
   - The **full content** of each changed file that falls in this category's scope (do NOT feed line-level diffs — audit the entire file)
   - This category's section from this document (rules + questions)
   - The applicable AGENTS.md rules text (including exception clauses)
   - The [Explicit exceptions](#explicit-exceptions-from-agentsmd) table
   - The baseline findings for that category from `docs/ai-audit-findings.md`
4. Ask: "Do not skip a finding because the same pattern exists elsewhere in unchanged files — existing violations in other files are not exceptions. Only the [Explicit exceptions](#explicit-exceptions-from-agentsmd) table provides valid exceptions."
5. Append findings to `docs/ai-audit-findings.md` under a new PR section

### Second review (important PRs only)

Feed diff + first review findings to a second pass:
"Did the first reviewer miss any applicable rule, changed file, or affected category?
Do not repeat the full audit."
