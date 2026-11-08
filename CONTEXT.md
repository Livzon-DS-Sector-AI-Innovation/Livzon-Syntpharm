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

### 报告生成 (Report Generation)

**槽位** (Slot):
交付物母本里「需要填写内容」的位置描述（`slot_key`、`label`、锚点、`is_enabled` 等），存于模板的 `template_structure` 缓存。停用的槽位既不下发给模型，也不写入生成结果。
_Avoid_: 字段, 占位符

**示例库** (Slot Example):
人工在任务详情页修正过的槽位值，沉淀为下次同模板生成的 few-shot 参照；以 `(template_id, slot_key)` 唯一，重复修正覆盖，人工清空即停用而不删除。示例只是措辞参考，不作为引用证据。
_Avoid_: few-shot 库, 训练集, 语料

**解析留痕** (Structure Run):
每次母本结构识别的记录，保存解析当时选中的槽位标识。「后补」（漏选）与「否掉」（多选）是这批标识与当前启用结构的集合差，跨多次人工编辑会混在一起，只作趋势看。
_Avoid_: 识别日志, 解析快照

**提示词覆盖与指纹** (Prompt Override / Fingerprint):
正文生成与母本识别各有一段 system prompt，库内 `REPORT_GEN_AGENT_PROMPT` / `REPORT_GEN_STRUCTURE_PROMPT` 可整段覆盖，留空则用 `report_gen/prompts.py` 的内置版本；变量用 `$name` 渲染。指纹是「生效文本 + 工具清单」的 sha256 前 8 位，用于判断提示词是否变过，不是版本号。
_Avoid_: 提示词版本, prompt 模板（当指可覆盖的生效文本时）

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
- **人工修正 → 示例库 → 下次生成**：人在详情页改槽位值即写 `Slot Example`；下次生成通过 `read_template_outline` 的 `manual_example` 下发，只影响措辞、不构成证据。
- **解析留痕 → 槽位结构**：`Structure Run` 记录解析当时的槽位集合，与当前 `Slot` 的启用状态做差得出「后补/否掉」，用于判断识别提示词是否该调。
