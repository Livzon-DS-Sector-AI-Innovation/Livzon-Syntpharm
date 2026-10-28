# 业务模块权限接入 Runbook

> 首个试点：research（2026-10-15 完成）。后续模块照本流程执行。
> 建议模型分工：强推理模型（kimi-k3）做粒度裁决与复核，代码模型（kimi-k2.7-code）做批量机械改动。

## 前置：框架能力（已就绪，勿重复建设）

- `config.py`：`PERMISSION_ENFORCE_ENABLED`（总开关）+ `PERMISSION_ENFORCE_MODULES`（灰度模块集合，逗号分隔模块码；空=全部强制）。
- `registry.py`：`module_for_path()` / `is_enforced_route()` 按模块灰度判定；`ENFORCE_READY_MODULES` 声明已完成接入的模块。
- `middleware.py`：fail-closed 兜底——受保护前缀下未登记绑定的请求一律 403（仅对灰度集合内模块生效）。
- `scripts/ci/check_permissions.py`：CI 门禁。对 `ENFORCE_READY_MODULES` 中的模块强制：每路由有绑定、每个 `require_permission` 码存在、前后端权限码表对齐。

## 接入步骤（以 research 为样板）

### 1. 盘点路由

```bash
uv run python -c "
import re, pathlib
text = pathlib.Path('app/modules/<MODULE>/api.py').read_text(encoding='utf-8')
pat = re.compile(r'@router\.(get|post|put|delete|patch)\(\s*[\"\']([^\"\']*)[\"\']')
for m, p in pat.findall(text): print(m.upper(), p)
"
```

注意：装饰器可能跨多行，正则要容忍 `\(\s*`。路由可能在多个 api 文件里（如 quality），需 `rglob("*.py")` 全扫。

### 2. 定细码粒度（需人工/强模型裁决）

- 资源码按业务域划分，新旧并存路由（如 `projects` / `rd-projects`）通常合并为同一资源。
- 动作只用 `BUSINESS_ACTIONS` 既有值：read/create/update/delete/submit/approve/export。
- AI 分析类端点归该资源 `create`。阶段流转=start/transition→`submit`，审批→`approve`。
- 导出端点（`/export/*`）归对应资源的 `export` 动作。

### 3. registry 登记

- `RESEARCH_PERMISSIONS` 式地新增 `<MODULE>_PERMISSIONS`，合并进 `ALL_PERMISSIONS`。
- `API_BINDINGS` 追加全部路由绑定（含 `create_module_router` 自动注册的 `GET /api/v1/<module>` 与 `/api/v1/<module>/` 两个模板——中间件在 FastAPI 尾斜杠重定向之前执行，两个都要登记）。
- `RESOURCE_LABELS` 加资源中文名。
- 生成方式参考本次：先脚本生成映射表 `/tmp/*_route_perm_map.json`，断言全覆盖后再生成代码块，杜绝笔误。

### 4. 端点挂 `require_permission`

统一签名模式（保留 `current_user: RequiredUser`，ctx 在后）：

```python
async def xxx(
    ...,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("<module>:<resource>:<action>")),
    db: AsyncSession = Depends(get_db),
):
```

**坑**：`ctx`（有默认值）必须放在所有无默认值参数之后；单行签名（`async def f(a, b):`）里的端点要单独处理。批量注入后必须 `ruff check` + `ast.parse` 双重验证。

### 5. 前端 codes.ts + 按钮级权限

- `codes.ts` 新增 `<MODULE>_PERM` 常量组并合并进 `PERM`（CI 校验项 2 会对齐前后端，缺码即红）。
- 按钮用 `<PermissionGate code={PERM.xxx}>...</PermissionGate>` 包裹；优先接：新建/删除/审批/导出按钮。

### 6. 角色模板

新建 `scripts/seed/seed_<module>_roles.py`（参照 `seed_research_roles.py`），四档：admin / editor / approver / viewer。**每个角色都必须含 `<module>:module:read`**（模块菜单准入码），否则角色看不到模块。

落库：`DATABASE_URL="$(grep -E '^DATABASE_URL=' ../.env | cut -d= -f2-)" uv run python scripts/seed/seed_<module>_roles.py`（本地开发统一用仓库根目录的 `.env`，由 `scripts/dev.sh` 从 `.env.dev.example` 复制）。

### 7. 标记就绪 + 开灰度

1. `registry.ENFORCE_READY_MODULES` 加入模块码 → `uv run python scripts/ci/check_permissions.py` 必须全绿。
2. `.env` 的 `PERMISSION_ENFORCE_MODULES` 追加模块码。
3. `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --force-recreate backend`（env 变更必须 force-recreate，仅重启不生效）。
4. 验证矩阵（用脚本签 JWT 测，勿用真实账号）：
   - 超管：读/写均 200
   - 无权限账号：读/写均 403，报错文案为「缺少权限：<code>」
   - viewer 角色：读 200、写/审批/导出 403
   - 未灰度模块：不受影响（200）
   - 未登录：401

## 验证工具速查

```bash
# 签测试 JWT（宿主机执行）
DATABASE_URL=... SECRET_KEY=... uv run python -c "见 scripts/test/ 或本次会话脚本"
# 授权测试
INSERT INTO permission.user_role_grants ...
```

## 已知边界

- 数据范围（scope）过滤本次未接入：research 25 个模型仅 2 个有 `owner_id`、无 `department_code`。要做需先补归属字段 + 迁移 + 回填，单独立项。
- 模块信息接口（`GET /api/v1/<module>/`）只要求登录态（`require_current_user`），不挂 `require_permission`——该依赖端点级立即生效，挂粗码会让未灰度模块的无权限用户立刻 403。绑定仍登记在 registry 供中间件兜底。
- DB 中残留旧版内置角色（如 `research:admin`/`research:viewer` 冒号码），注册表已下线但数据未清，不影响新模板（下划线码）。
