# 平台访问控制 / 菜单与导航 / 系统运维 —— 交接文档

> **日期**：2026-10-11 初稿；2026-10-12 更新（字典移除、测试角色改造、多 Tab 权限过滤）；**2026-10-13 更新**（12 个业务模块接入菜单级权限、菜单管理交互重构、统一边界页、系统运维新增数据库页、用户管理页调整）
> **分支**：`feature/permission-system-admin`
> **状态**：改动全部落库并实测通过；**111 个文件未提交 git**（60 个新增未跟踪 + 51 个修改）
> **环境**：本地开发（`local-backend` / `local-frontend` / `local-dev-postgres`，库 `dazah_local`）
> **完整流水**：`.codebuddy/memory/2026-10-11.md`（第一轮）+ `2026-10-12.md`（字典移除等）+ **`2026-10-13.md`（最新，本对话）**；长期约定见 `.codebuddy/memory/MEMORY.md`
>
> **文件命名约定**：本文档随对话持续更新，**内容有变动就同步改文件名里的日期**；主题名保持概括（`platform-access-and-ops` = 访问控制 + 平台运维），不随单次内容改动。

---

## 一、交付总览

| # | 工作包 | 状态 | 入口 |
|---|---|---|---|
| 1 | 日志管理：默认不自动刷新 + 倒序显示（最新在前） | ✅ | `/settings/ops` → 日志管理 |
| 2 | 字典配置管理 | ❌ **已移除**（2026-10-12，见 3.1） | — |
| 3 | 新建本地用户报错修复（Server Action 未解包信封 → 假 500） | ✅ | `/settings/users` |
| 4 | 用户管理：角色列修复 + 绑定/解绑飞书 + 资料禁改 | ✅ | `/settings/users` |
| 5 | 授权管理：文案人话化 + 数据范围收进"限制可见数据"复选框 | ✅ | `/settings/permission` |
| 6 | 飞书登录自动建号 + 自动补齐通讯录资料 | ✅ | 飞书 OAuth 登录 |
| 7 | 飞书部门/成员同步打通（47 部门、510 人） | ✅ | `/settings` → 飞书设置 |
| 8 | 前端权限控制（按钮级 + 页面级守卫 + 403 语义化 + CI 门禁） | ✅ | 全局 |
| **9** | **12 个业务模块接入「菜单级」权限**（模块访问码 `<module>:module:read`，菜单可见 + 页面准入成对） | ✅ | 全局导航 + 各模块 `layout.tsx` |
| **10** | 用户管理页：授权后自动刷新 + 编辑用户可跳转授权页 + 操作列精简 + 飞书只可解绑 | ✅ | `/settings/users` |
| **11** | 菜单管理：查看/编辑双模式 + 逐项立即提交 + 名称/权重/可见范围可编辑 + 父级锁定路径前缀 | ✅ | `/settings/menus` |
| **12** | 菜单「显示」关闭对超管失效修复 + 可见权限显示中文名称 | ✅ | `/settings/menus` |
| **13** | **统一边界页**：404 / 错误页 / 401 自动回跳 / 菜单死链校验 | ✅ | 全局 |
| **14** | 系统运维：服务健康加运行时长 + 新增「数据库」页（表清单 + 字段详情） | ✅ | `/settings/ops` |

> **当前权限规模**：**25 权限码**（13 平台码 + 12 业务模块访问码）/ **43 接口绑定** / 4 个活跃角色（1 内置 `super_admin` + 3 自建）。CI 自检命令见第七节（`check_permissions.py` 已修正为遍历 `ALL_PERMISSIONS`，业务码同样纳入校验）。

---

## 二、⚠️ 接手先看

### 2.1 111 个文件未提交 git

```bash
git status --short | wc -l   # 111（60 个新增未跟踪 + 51 个修改）
git branch --show-current    # feature/permission-system-admin
```

**建议先提交一次**（改动跨多个主题，可按主题拆 commit：权限基建 / 模块接入 / 菜单管理 / 边界页 / 运维页）。

### 2.2 飞书有两个权限在**等集团审核**（外部阻塞）

| 权限码 | 影响字段 |
|---|---|
| `contact:user.employee_id:readonly` | `user_id` |
| `contact:user.employee:readonly` | **工号 `employee_no`**、**职务 `job_title`**、企业邮箱 |

**现状**：这两个权限没开，但不影响姓名/英文名/头像/部门归属/union_id（用 `user_id_type=open_id` 绕开）。
**审核通过后**：不用改代码 —— 重跑一次「同步」或让员工重新登录，工号与职务会自动填充。

### 2.3 数据范围（scope）配了**不生效**（2026-10-13 复核，结论未变，量化如下）

- `app/platform/permission/service/data_scope.py::apply_scope_filter()` 已实现四档（fail-closed），但**全项目零调用方**；
- 设备模块还自建了一套 `modules/equipment/service/data_scope.py`（含 `verify_write_ownership` 写校验），**同样零调用方**；
- **数据底子不足**：236 张业务表里**只有 33 张**有部门类字段（safety 11 / hr 9 / quality 4 / identity 3 / equipment 2 / qms 2 / procurement 1 / permission 1）→ 86% 的表没有"部门归属"；
- `hr.departments` **没有父子字段**（只有 name/code/description + 时间戳，`hr.teams` 引用它）→ `department_and_children` 当前**等价于** `department`。

**要真正生效**：① 收敛两套实现（现在都是死代码，口径还不一致）；② 业务表补归属字段（`created_by` / `department_code`）；③ 查询里调 `apply_scope_filter`。**按模块立项**，不要在权限侧继续加配置项。

### 2.4 人员数据当前是"干净"的（9 个账号）

按需求清空过同步进来的 506 个账号，只保留 4 个登录过的飞书账号 + 5 个本地账号。同步能力完好，需要人员时在飞书设置页点「同步」即可（约 50 秒同步 500+ 人）。

### 2.5 全部 13 个模块已接入「菜单级」权限，且**已按"先全开"铺好授权**

- 12 个业务模块 + `settings`（系统管理）= 13 个模块都受控；
- **约定顺序：先铺授权、再启用守卫**（反过来会出现"一夜之间所有人看不到模块"）；
- 当前 3 个自建角色（`permisson_admin` / `readonly_tester` / `test_1`）各挂了 12 个模块访问码 → 现有用户能看到全部模块；
- **收紧方式：不改代码**，去「权限管理 → 角色管理」取消勾选对应模块码即可。

### 2.6 后端**没有热重载** —— 改后端代码必须重启容器

```bash
docker restart local-backend     # 否则你的改动不生效（会以为"改了没用"）
```

判断是否重启过：看日志里有没有 `Starting dazah-backend`（`docker inspect StartedAt` 只看容器，不代表进程）。

---

## 三、各工作包关键实现

### 3.1 字典配置（工作包 2）—— 已于 2026-10-12 整体移除
见 `.codebuddy/memory/2026-10-12.md`。要点：全项目零消费方 → 后端 4 文件 + 前端 5 文件 + 菜单 + 2 权限码 + 8 绑定全删；迁移 `0083_create_dictionary_tables` 未提交故直接删除文件并把本地库回滚到 `0082`。

### 3.2 用户管理（工作包 3、4、**10**）
- `PUT /identity/users/{id}` 对**已绑定飞书**的账号拒绝修改姓名/邮箱/手机/工号/部门/职位（403）；`username`、`status` 仍可改；
- 列表 `GET /identity/users` 返回 `roles: list[str]`（修复"角色列恒显示普通用户"）；
- 绑定/解绑飞书：`POST|DELETE /identity/users/{id}/bind-feishu`；
- **2026-10-13 调整**：
  - **授权后自动刷新**：`GrantManagementClient.save` 成功后追加 `queryClient.invalidateQueries({queryKey:['users']})` + `router.refresh()`（前者刷新用户管理页角色列，后者重新下发导航）；用户管理页查询补 `refetchOnMount:'always'`；
  - 编辑用户弹窗的「角色」处**加「前往授权管理」链接**（`/settings/permission?tab=grants`；`PermissionAdminClient` 改为受控 Tabs + 接收 `initialTab`）；
  - 列表操作列**只留「编辑」+「是否启用」**（Switch 带二次确认）；**重置密码 / 飞书解绑移进编辑弹窗**的「账号操作」区；
  - **飞书绑定入口整体移除**（管理员不能代绑）：后端 `POST /users/{id}/bind-feishu` **接口保留**（docstring 标注"管理端不再提供入口"），删除它会留下"本地账号与飞书账号重名并存时无法合并"的死角。

### 3.3 授权管理（工作包 5）
副标题、范围选项全部改人话；数据范围默认不限制（`limitScope` 复选框）；表格移除"数据范围/范围部门"两列。

### 3.4 飞书对接（工作包 6、7）
- 登录 `handle_oauth_callback`：自动建号/更新资料 + `enrich_user_from_feishu_contact()`；
- 同步 `sync_departments` / `sync_members`：`root_dept_id` / `target_dept_id` 可留空；
- 关键实现：`contact.py::get_scope_department_ids()`、`_raise_on_feishu_error()`、`_parse_feishu_user()`。

### 3.5 前端权限基础设施（工作包 8）

| 文件 | 作用 |
|---|---|
| `lib/permissions/codes.ts` | `PERM.*` 权限码常量（**含 12 个模块访问码 `MODULE_PERM`**）+ 统一文案 |
| `lib/permissions/modules.ts` | `MODULE_ACCESS_PERMS`（模块准入）/ `SUBMENU_ACCESS_PERMS`（子菜单准入）/ `canAccess` |
| `lib/permissions/server.ts` | `hasPermission` / `hasAnyPermission` / **`hasModuleAccess(moduleKey)`**（模块 layout 守卫）/ `resolveLandingPath` |
| `hooks/usePermission.ts` | React Query 共享缓存，`can(PERM.xxx)` / `loading` |
| `components/auth/{PermissionGate,RequirePermission}.tsx` | 按钮级 / 客户端页面级守卫 |
| `lib/api/errors.ts` | `PermissionDeniedError`（403 语义化） |

### 3.6 **模块级（菜单级）权限接入**（工作包 9）★

**模型：两层正交**

| 层 | 码形态 | 控制什么 | 状态 |
|---|---|---|---|
| 菜单/模块 | `<module>:module:read`（每模块 1 个） | 菜单可见 + 模块页面准入 | ✅ 已做 |
| 接口/功能 | `<module>:<resource>:<action>` | 具体操作 | 后续追加，**菜单配置不用改** |

**实现**：
- 后端 `registry.py`：新增 `BUSINESS_MODULE_PERMISSIONS`，**由 `BUSINESS_MODULES` 生成**（不手抄，避免与前端菜单漂移）；`ALL_PERMISSIONS = PLATFORM_PERMISSIONS + BUSINESS_MODULE_PERMISSIONS`；`PERMISSIONS_BY_CODE` 改用 `ALL_PERMISSIONS`；
- 前端 `modules.ts` 的 `MODULE_ACCESS_PERMS` 补齐 12 个业务模块（`settings` 沿用 5 个平台码并集）；
- **12 个 `app/(dashboard)/<module>/layout.tsx` 模块守卫**（`hasModuleAccess` + `ModuleNoAccess`）—— **菜单隐藏与页面准入必须成对做**，只做菜单可见性的话，手输 URL 仍能进页面；
- 授权铺设：给 3 个自建角色各补 12 个码（36 行 `permission.role_permissions`），超管靠 bypass。

### 3.7 菜单管理交互重构（工作包 11、12）

- **查看 / 编辑双模式**：顶部按钮由「保存」→「**编辑**」（进入）/「**完成**」（退出）；查看模式整表只读；操作列只在编辑模式出现；
- **逐项立即提交**：行编辑 / 新建 / 删除确认后立即 PUT 整份配置（`buildConfig(rows)`），**取消了草稿与全局保存**（顺带消除"新建后忘点保存"的坑）；
- **字段可编辑矩阵**：

| 字段 | 内置菜单项 | 自定义菜单项 |
|---|---|---|
| 菜单名称 | ✅（清空 = 恢复代码默认名，配置模型新增 `label` 覆盖字段） | ✅ |
| 跳转路径 | 🔒 只读（对应代码路由，改了会死链） | ✅ |
| 图标 | — | ✅ |
| 显示 | ✅（保护项置灰） | ✅ |
| 排列权重 | ✅ | ✅ |
| 可见范围 | ✅（tags 多选，名称/权限码都能搜） | ✅ |

- **可见权限显示中文名**（复用「权限目录」缓存，拿不到目录时回退显示权限码）；
- **父级锁定路径前缀**：新建时选了父级 → 路径输入框用 `addonBefore` 显示父级路径，只填名称段；粘贴完整路径不会重复拼接；
- **「显示」开关对超管同样生效**（原来 `resolve.ts` 里 `if (isSuperuser) return true` 导致超管看不到效果）；仅 `PROTECTED_MENU_KEYS`（`settings` / `settings-overview` / `settings-menus`）例外，防自锁；
- **模块 Tab 联动**：模块下子菜单被隐藏光时，顶部模块 Tab 一并隐藏。

### 3.8 统一边界页（工作包 13）★

| 落点 | 作用 |
|---|---|
| `components/common/BoundaryResult.tsx` | 统一边界容器（unauthorized / forbidden / notFound / error / maintenance），每类都给"下一步"动作 |
| `components/settings/NoAccessResult.tsx` | 页面级 403/未登录（11 处调用点无需改动，内部改用 BoundaryResult） |
| `components/layout/ModuleNoAccess.tsx` | 模块级 403 |
| `app/not-found.tsx` + `app/(dashboard)/not-found.tsx` + `app/(dashboard)/[...notFound]/page.tsx` | 404（catch-all 主动 `notFound()`） |
| `app/error.tsx` / `app/global-error.tsx` | 错误页（不再泄露 `error.message`，改展示 digest + 重试 + 返回首页） |
| `lib/api/client.ts` + `src/proxy.ts` | 401 统一：客户端记 `login_redirect` cookie → proxy 在 `/` 一次性消费并回跳（读后即删，防反复弹跳；只接受站内路径防开放重定向） |
| `lib/navigation/known-routes.ts`（生成）+ `scripts/gen-known-routes.py` | 已知页面清单（197 静态 + 27 动态模板），菜单编辑时校验路径是否存在（**提示不阻止**） |

### 3.9 系统运维增强（工作包 14）
- **服务健康加运行时长**：`ComponentHealth.uptime_seconds`（backend 进程 / postgres 实例 / redis 实例；minio 取不到）；`formatUptime` 支持秒级；
- **新增「数据库」页**（`/settings/ops` → 数据库）：概览（库大小/连接数/缓存命中率/表数量）+ 表清单（估算行数、体积、列数、最后分析时间，可搜索）+ 点「详情」用 Drawer 看**字段结构**（列名/类型/可空/默认值/注释，按需加载）；
  - **红线：只暴露结构，不返回任何数据行**；`schema`/`table` 全部走 SQL 参数绑定；
  - 新接口：`GET /api/v1/system/db/tables`、`GET /api/v1/system/db/tables/{schema}/{table}/columns`（已登记 `platform:ops:read` 绑定）。

---

## 四、待办

| 优先级 | 事项 | 说明 |
|---|---|---|
| **P0** | 提交 git | 111 个文件（60 新增 + 51 修改），建议按主题拆 commit |
| **P1** | 业务模块**接口级**权限 | 菜单级已做完（每模块 1 个码）；细化到 `<module>:<resource>:<action>` 需逐模块立项（现存 1,260 个方法级接口，量力而行） |
| **P1** | 业务模块**按钮级**权限 | 质量 / 注册 / 能源等模块的写操作按钮（做法同 3.5） |
| **P1** | 数据范围真正接入 | 见 2.3，按模块立项；试点建议 `equipment`（已有 `EquipmentAccessContext` 基础设施） |
| **P1** | 新增权限码时同步前端常量 | 忘了会被 CI 拦下（`check_permissions.py` 现已覆盖业务码） |
| **P2** | 404 页是否要侧栏 | 现在渲染全局 404（无侧栏，因 Next 对 catch-all 用根 boundary）；改带侧栏需 catch-all 直接渲染，代价是状态码变 200 |
| **P2** | 字典配置是否重做 | 2026-10-12 因"零消费方"整体移除 |
| 外部依赖 | 集团审核通过后补工号/职务 | 无需改代码，重跑同步或重新登录 |
| 可选 | 定时同步（部门/成员） | 现在只能手动点同步 |
| 可选 | 服务健康补"外部依赖"（飞书长连接 / LLM） | 见 2026-10-13 日更的运维盲区分析（系统级零告警、长连接无状态） |

---

## 五、必须遵守的约定

### 5.1 前端权限
1. 权限码**统一定义在** `lib/permissions/codes.ts` 的 `PERM`；**新增时前端 + 后端 registry 两边都要改**（CI 校验，现已覆盖业务码）
2. 取权限一律用 `usePermission()`；**hook 必须写在组件任何 early return 之前**
3. 按钮级隐藏：`!loading && can(...)` 或 `PermissionGate`；表格操作列 `...(canManage ? [操作列] : [])` **整列隐藏**
4. 页面级守卫：RSC 用 `hasPermission()`；**模块级用 `hasModuleAccess(moduleKey)` + `layout.tsx`**（口径必须与 `MODULE_ACCESS_PERMS` 一致，否则"看得到入口、点进去被拦"）
5. **前端隐藏只是体验层**：后端 `require_permission` 必须保留

### 5.2 后端
- 权限码与接口绑定登记在 `app/platform/permission/registry.py`；**新增接口必须登记绑定**（`scripts/ci/check_permissions.py` 门禁，已实测能拦住）
- **遍历权限码一律用 `ALL_PERMISSIONS`**，不要写 `PLATFORM_PERMISSIONS`（曾导致业务码同步不进 DB、门禁漏检）
- 软删用 `is_deleted`；"同步写入"类逻辑**只写非空值**
- **改完后端代码要 `docker restart local-backend`**（无热重载）

### 5.3 菜单与导航
- 菜单结构以 `lib/menu-config.ts` 为唯一权威；**模块清单以后端 `BUSINESS_MODULES` 为唯一权威**（权限码由它生成）
- **新增页面后要重跑** `cd frontend && python3 scripts/gen-known-routes.py`（否则菜单路径校验会误报"没有对应页面"）
- 菜单配置存在 `core.module_settings`（module=menu, key=CONFIG）；`items` 只存**偏离代码默认的覆盖**（`label` / `visible` / `sort` / `perms`），`custom` 存自定义项
- **边界页（404 / 错误页）必须用 RSC + Tailwind**，不要用 antd（见 6.x）

---

## 六、踩过的坑（可复用）

### 6.1 本轮（2026-10-13）新增

| 现象 | 原因 | 做法 |
|---|---|---|
| 整站路由全挂（404/500） | 项目是 **Next 16**，中间件只认 `src/proxy.ts`；新建 `src/middleware.ts` 后 Next 报"两个文件并存" | 逻辑合并进 `src/proxy.ts`；**删文件后还要重启前端**（dev 缓存残留 `Could not parse module ... file not found`） |
| 404 / 错误页**一片空白** | Next 的**边界渲染通道里客户端组件不输出 SSR 内容**（纯 div 的 RSC 能渲染，换 antd 就什么都没有） | 边界页用 **RSC + Tailwind + `next/link`**；`BoundaryResult`（antd 版）只用于页面内的 403 |
| 整站编译失败 | 生成文件头注释里写了 `src/app/**/page.tsx`，其中 `*/` **提前闭合块注释** | 生成脚本措辞避开 `*/`（TS 注释里别出现 `**/`） |
| 权限目录看不到新加的业务码 | `_sync_permissions` 遍历的是 `PLATFORM_PERMISSIONS` | 改遍历 `ALL_PERMISSIONS`（`check_permissions.py` 同源问题一并修） |
| 菜单"显示"关掉后仍然显示 | `resolve.ts` 的 `isVisible` 里 `if (isSuperuser) return true`（超管无条件可见） | 显隐对所有人生效，只保留 `PROTECTED_MENU_KEYS` 例外 |
| 菜单项名称改了但导航没变 | `MenuItemOverride` 没有 `label` 字段，**pydantic 静默丢弃**未知字段 | schema + 前端类型都要加字段，并在 `resolveLabel()` 里应用 |
| 新建自定义菜单报"父级不存在" | ① 后端只认"items 里出现过的 key"；② 前端补父级上下文的时机早于新项加入 | 后端把 `BUSINESS_MODULES` **∪ `PROTECTED_MENU_KEYS`** 作为合法父级；前端 push 新项后**再补一次** `ensureBuiltinParents` |
| `check_permissions.py` 漏检业务码 | 正则只匹配 `platform:` 前缀 | 改为匹配任意 `模块:资源:动作` |
| 改了后端"没生效" | 后端没有热重载 | `docker restart local-backend` |

### 6.2 第一轮（2026-10-11/12）

| 现象 | 原因 | 做法 |
|---|---|---|
| 飞书用户列表一个都拉不到 | `page_size=100` 超上限（**50**），报 `99992402` | `page_size <= 50` |
| 飞书接口报权限错但分不清 | `99991672` = 缺 scope；`40004` = 数据权限范围不足 | 看错误码；`GET /contact/v3/scopes` 查可见范围 |
| 部门拉不到（`40004`） | 硬编码从根部门 `"0"` 起 BFS，而根部门常不在可见范围内 | 从 `get_scope_department_ids()` 起 BFS |
| eslint: Hook 被条件调用 | 把 `usePermission()` 放在 early return 之后 | 移到组件顶部 |
| shell 变量被污染 | `psql -tAc "insert ... returning id"` 会把 `INSERT 0 1` 写进 stdout | `-tAq ... \| head -1` |
| Python 脚本崩溃看不到输出 | 非 tty 下 stdout 是块缓冲 | `python3 -u`；多行脚本用 heredoc |
| `docker exec ... <<SQL` 没效果 | heredoc 传不到 psql | 用 `-c` 或 `psql -f -` |

---

## 七、快速自检（命令）

```bash
# 后端
cd backend && uv run ruff check app/ scripts/          # lint
uv run python scripts/ci/check_permissions.py          # 期望：25 权限码 / 1 内置角色 / 43 接口绑定
uv run pytest tests/unit/permission -q                 # 权限单测

# 前端（容器在跑时）
docker exec -w /app local-frontend npx tsc --noEmit
docker exec -w /app local-frontend npx eslint src/     # 全量跑会带出既有告警
# 容器没跑时用宿主机：
cd frontend && npx tsc --noEmit && npx eslint src/

# 新增页面后（必须）
cd frontend && python3 scripts/gen-known-routes.py
```

```bash
# 模块级权限效果（只读测试账号：nomod_test / Qa@2026test，非超管）
# 1) 有权限 → 正常进；2) 撤掉该模块访问码 → 页面「无访问权限」且导航里该模块消失
docker exec local-dev-postgres psql -U postgres -d dazah_local -q -c \
  "update permission.role_permissions set is_deleted=true where permission_code='equipment:module:read';"
# …验证后恢复：
docker exec local-dev-postgres psql -U postgres -d dazah_local -q -c \
  "update permission.role_permissions set is_deleted=false where permission_code='equipment:module:read';"
```

```bash
# 404 与回跳
curl -s -o /dev/null -w 'status=%{http_code}\n' -b "auth_token=<token>" http://localhost:3000/settings/test   # 期望 404
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' \
  -b "auth_token=<token>; login_redirect=%2Fsettings%2Fusers" http://localhost:3000/                          # 期望 307 → /settings/users
```

---

## 八、关键文件索引

**后端**
- 用户/登录：`app/platform/identity/{api,service,repository,schemas}.py`、`models.py`
- 飞书集成：`app/platform/integrations/feishu/{contact,sync,oauth}.py`
- 权限：`app/platform/permission/{registry,api,models}.py`、`service/{authorization,management,data_scope}.py`（`management._sync_permissions` 遍历 `ALL_PERMISSIONS`）
- 菜单配置：`app/platform/system/{menu_api,menu_service,menu_schemas}.py`
- 系统运维：`app/platform/system/{ops_api,ops_service,ops_schemas}.py`（含数据库信息接口）
- 门禁：`backend/scripts/ci/check_permissions.py`

**前端**
- 权限基础设施：`src/lib/permissions/{codes,modules,server}.ts`、`src/hooks/usePermission.ts`、`src/lib/api/errors.ts`
- 菜单解析：`src/lib/menu/resolve.ts`（显隐/权重/权限/自定义项/label 覆盖）
- 边界页：`src/components/common/BoundaryResult.tsx`、`src/app/not-found.tsx`、`src/app/(dashboard)/{not-found.tsx,[...notFound]/page.tsx}`、`src/app/{error,global-error}.tsx`
- 中间件：`src/proxy.ts`（`/api` 反代 + `login_redirect` 一次性回跳）
- 路由清单：`src/lib/navigation/known-routes.ts`（生成自 `scripts/gen-known-routes.py`）
- 系统管理页：`src/components/settings/*`、`src/app/(dashboard)/settings/**`

**文档 / 记忆**
- 本文档（第三轮，2026-10-13 更新）
- `.codebuddy/memory/2026-10-13.md`（本对话完整流水，最新）
- `.codebuddy/memory/{2026-10-11,2026-10-12}.md`（前两轮）
- `.codebuddy/memory/MEMORY.md`（跨会话长期事实与约定）
- `backend/docs/alembic-guide.md`（迁移规范）

---

## 九、给下一个对话的提示词

直接说明要做什么即可（例如"继续做 P1：把某一批接口细化成 `<module>:<resource>:<action>` 权限码"）。建议我先读：

1. `.codebuddy/memory/MEMORY.md`（长期约定）
2. 本文档第二节「接手先看」（尤其是 2.5 模块权限已全开、2.6 后端要重启）
3. 需要细节时按时间倒序翻日更：`.codebuddy/memory/2026-10-13.md`（最新）→ `2026-10-12.md` → `2026-10-11.md`
