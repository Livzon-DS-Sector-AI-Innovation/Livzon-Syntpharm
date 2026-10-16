# Livzon-Syntpharm

Livzon-Syntpharm 是一个模块化单体（modular monolith）应用：后端 FastAPI 按业务模块划分，前端 Next.js 通过 OpenAPI 契约与后端交互。

## Language

### API 契约 (API Contract)

**API Response Envelope** (API 响应信封):
所有后端 API 成功响应遵循的统一结构 `{ code, message, data, meta? }`，由 `ApiResponse` 模型定义；`meta` 承载分页等附加信息。
_Avoid_: API 包装器, response wrapper, 响应壳

**Generated Types** (生成类型):
由后端 OpenAPI 规范自动生成的 TypeScript 类型，是前后端 API 契约的唯一真实来源，位于 `frontend/src/types/generated/schema.ts`。
_Avoid_: 手写 API 类型, OpenAPI 类型, schema 类型

### 模块边界 (Module Boundaries)

**模块** (Module):
按业务域划分的后端单元，注册于模块注册表，拥有一个 code 与一个同名主 schema。一个模块可以拥有多个 schema——例如 `quality` 模块同时拥有 `quality` 与 `qms`。迁移的「单模块原则」按模块判定，不是按 schema。
_Avoid_: schema（当指代模块时）, 服务, 子系统

**Public API**:
模块对外暴露的唯一入口 `public_api.py`；跨模块调用必须经由它，禁止直接引用其他模块的 `repository.py`、`service.py` 或 `models.py`。
_Avoid_: 内部接口, 跨模块导入

**模块注册表** (Module Registry):
记录模块与其数据库 schema 对应关系的注册表 `app/shared/module_registry.py`；新增模块时必须同步更新。
_Avoid_: 模块清单, 模块列表

### 数据与认证 (Data and Auth)

**软删除** (Soft Delete):
删除业务数据的默认方式，通过 `is_deleted` 标记而非物理删除；仅当需求明确要求时才做物理删除。
_Avoid_: 逻辑删除, 标记删除

**RequiredUser**:
必须登录的接口所使用的依赖注入参数；未登录返回 401，是所有业务 API 的默认选择。
_Avoid_: CurrentUser, 必选用户

**OptionalUser**:
允许未登录访问的接口所使用的依赖注入参数；仍会解析 JWT/cookie，端点可据其做条件逻辑。
_Avoid_: 可选用户, 匿名用户

## Relationships

- **Backend → Frontend**: 后端导出 OpenAPI 规范；前端据此生成 `Generated Types`。契约变更先于前端消费。
- **Module → Module**: 模块之间只经 `Public API` 协作；`API Response Envelope` 是所有模块对外的统一响应形状。
