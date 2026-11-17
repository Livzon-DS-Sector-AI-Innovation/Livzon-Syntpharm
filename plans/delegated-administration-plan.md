# 委派式权限管理与模块配置页 — 实施计划

> 需求文档：https://j0eukrlohu.feishu.cn/wiki/X6Dxw2Ubyi27X8kWTnFc7wShnIe
> 设计记录：docs/adr/0008-delegated-administration.md、GLOSSARY.md
> 原型（一次性）：http://localhost:8931/delegation-logic.html 、http://localhost:8931/module-settings-all.html
> （原型文件在 ~/tmp/prototypes/，不入库）

## 设计要点（已锁定）

- **三级角色**：超管（内置）→ 模块负责人 `{module}:owner`（级别 2，仅超管指派）→ 模块代表 `{module}:delegate`（级别 1，超管或负责人指派）→ 模块自定义角色（级别 0，负责人与代表均可创建/编辑）。
- **级别守卫**：创建/修改/移除某级别角色的授权，操作者必须持有同模块**更高级别**角色（或超管）。代表不能碰代表；负责人之间不能互相移除；多负责人并存。
- **角色编码自由格式**（如 `quality:deviation-reviewer`），`owner`/`delegate` 为保留字；模块角色只含 `{module}:*` 权限码（后端拒绝跨模块）。
- **负责人/代表角色由注册表自动生成**（每业务模块两个），随新权限码自动扩量（同步只增不减）；自定义角色不自动扩量。
- **角色删除时其授权行一并停用**（可恢复）。
- **模块配置页**：每个模块统一 `/{module}/settings`，侧边栏可见；权限管理为第一个页签（复用现有角色/授权组件按模块过滤）；各模块零散设置页迁移合并进来；页面归模块权限管，不再用 `platform:config:read` 守卫。
- **菜单灰显**：无权限菜单项/模块 Tab 灰显 + 锁图标，可见；点击进无权限页。后端 API 仍 fail-closed。
- **超管兜底**：模块角色出现在全局角色管理；负责人/代表的 API 视图按模块过滤。

## 实施清单（执行顺序）

### 后端

1. `permission.roles` 表加 `level` 列 + Alembic 迁移（单模块原则：permission schema）
2. 注册表自动生成 `{module}:owner` / `{module}:delegate` / `{module}:admin:read`；启动同步时自动扩量
3. 级别守卫：授权操作时校验操作者同模块级别严格大于目标角色级别（超管放行）
4. 角色/授权 API 按模块过滤（负责人/代表视图）；创建模块角色时拒绝非本模块权限码
5. 角色删除 → 其授权行置为 disabled
6. 模块 settings API 改用模块级权限码（弃用 `platform:config:read` 守卫）

### 前端 — 菜单灰显

7. `lib/menu/resolve.ts`：无权限项保留并标 `noAccess`，不再过滤
8. `TopNav.tsx`：灰显模块 Tab + 锁图标，点击照常跳转（layout 守卫兜底）
9. `Sidebar.tsx`：灰显菜单项 + 锁图标，点击进无权限页

### 前端 — 角色与页面

10. 角色表单移除「角色档位」下拉，编码改自由格式
11. 系统管理增加负责人指派入口（超管指派 `{module}:owner`）
12. 每模块建 `/{module}/settings` 模块配置页，权限管理为首页签（复用 RoleManagementClient / GrantManagementClient 加 module 过滤）
13. 迁移既有设置页为页签：quality（仪器/稳定性提醒）、hr（system/settings 两处）、energy（孤立页）、safety/equipment（既有模块配置）
14. 12 个模块侧边栏统一加「模块配置」入口，`{module}:admin:read` 控制灰显
15. `codes.ts` 增加 `{module}:admin:read` 等权限码常量

### 契约与质量

16. 重新导出 OpenAPI + 前端生成类型同步
17. 单测：级别守卫（代表互斥/负责人平级/局外人/跨模块/保留字）、角色删除停用授权、API 模块过滤
18. E2E：灰显菜单渲染与点击、模块配置页负责人/代表准入
19. CI：`check_permissions.py` 等权限注册表校验通过

### 文档收尾

20. 需求文档「三、测试用例」表格填充
21. 需求文档标题 XXX 占位替换为真实事项编号
