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

### 权限体系 (Permission System)

**权限码** (Permission Code):
三段式字符串 `模块:资源:动作`（如 `quality:deviation:approve`），代码注册表（`backend/app/platform/permission/registry.py`）是唯一权威，数据库只作只读镜像。权限码一经发布不可删除，只能标记 deprecated。
_Avoid_: 权限点, 权限字符串

**角色** (Role):
一组权限码的命名集合（`permission.roles`），授权的最小单位。用户不直接持有权限码，而是通过角色授权间接获得。
_Avoid_: 权限组, 用户组

**授权** (Grant):
把角色指派给用户的记录（`permission.user_role_grants`），是「单条授权判定」的最小单元——动作权限与数据范围必须落在同一条授权内。
_Avoid_: 赋权, 权限分配

**超级管理员** (Super Admin):
持有 `super_admin` 角色的用户；权限判定时直接放行（`is_superuser` 标志），拥有全部权限码。
_Avoid_: 超管账号（作为角色名以外的泛指）, 系统管理员

**模块负责人** (Module Owner):
某模块的受托管理员（角色 `{module}:owner`，级别 2），拥有该模块全部权限并可在模块内创建角色、授权用户、指派模块代表。由超级管理员指派；仅超级管理员能移除。
_Avoid_: 模块管理员（旧称，已废弃）, 模块 owner（中英混用）

**模块代表** (Module Delegate):
某模块的次级受托管理员（角色 `{module}:delegate`，级别 1），拥有该模块全部权限并可创建模块角色、授权普通用户，但不能指派、编辑或移除其他模块代表。
_Avoid_: errant（旧称，已废弃）, 模块代理人

**角色级别** (Role Level):
角色上的整数等级（`roles.level`）：模块负责人 = 2，模块代表 = 1，普通角色 = 0。授权守卫规则：授予/修改/移除某级别角色的授权，操作者必须持有同模块更高级别的角色（或超管）。
_Avoid_: 角色层级, 角色档位（旧称，已废弃——原「角色档位」只是角色编码后缀，无任何语义）

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

### 设备台账 (Equipment Ledger)

**增量更新策略** (Incremental Update Strategy):
设备批量导入 v4 的选择性更新机制：A 类字段（`current_cost`、`book_value` 等财务数据）每次导入都更新；B 类字段（部门、位置、负责人、位号等业务配置）仅在库中为空或开启强制覆盖时更新，以保护人工修正过的数据。
_Avoid_: 部分更新, 选择性覆盖

**设备位号** (Equipment Tag):
按「车间-类型-序号」命名的设备标识符，如 `101-L-001`。在未删除记录范围内全局唯一（部分唯一索引），可作为资产编号之外的备选匹配键。
_Avoid_: 设备编号（与 `asset_no` 混淆）

**固定资产标记** (Fixed Asset Flag):
`is_fixed_asset` 布尔字段，区分固定资产与非固定资产，判定规则为 `asset_no IS NOT NULL`。仅用于财务分类统计，工单、巡检等业务不据此区别对待。

**导入审计日志** (Import Audit Log):
`import_audit_logs` 表按行记录批量导入的批次 ID、操作类型、匹配策略、字段变更前后值与警告信息，用于财务合规与数据追溯。

## Relationships

- **Backend → Frontend**: 后端导出 OpenAPI 规范；前端据此生成 `Generated Types`。契约变更先于前端消费。
- **Module → Module**: 模块之间只经 `Public API` 协作；`API Response Envelope` 是所有模块对外的统一响应形状。
- **导入策略 → ADR**：设备导入的匹配与更新决策记录在 `backend/docs/adr/001-equipment-import-v3.md` 与 `backend/docs/adr/002-equipment-import-v4-incremental-update.md`；Excel 部门名称映射的真实来源是 `backend/app/modules/equipment/config/dept_mapping.py`。
