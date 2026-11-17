## Problem Statement

Only the super admin can manage roles and grants today. Every module's day-to-day permission needs — a new hire needing deviation read access, a team lead needing approval rights — route through one person in 系统管理 → 权限管理. With 12 business modules (production, quality, safety, equipment, hr, research, registration, procurement, warehouse, energy, administration, environment), the super admin is a bottleneck.

Separately, users without permission can't see that features exist at all: menus and module tabs are filtered out of the navigation. Users don't know what to ask for, and permission requests turn into guesswork.

## Solution

Introduce **delegated administration**: the super admin appoints a **module owner** per module (full module power, including role and grant management inside the module). The owner can appoint **module delegates** (same module power, can grant permissions to regular users, but cannot appoint or remove other delegates). Both manage their module from a new **模块配置** page inside the module itself.

And change menu behavior from hide to show: items without permission render greyed out with a lock icon; clicking leads to the existing no-permission page.

## User Stories

1. As a super admin, I want to appoint a module owner for each module, so that module-level permission management no longer requires me.
2. As a super admin, I want to be the only one who can appoint or remove module owners, so that module control stays accountable.
3. As a super admin, I want to also be able to appoint module delegates directly, so that I can bootstrap a module before an owner is chosen.
4. As a super admin, I want module-created roles to appear in the global role management list, so that I retain oversight and can intervene.
5. As a super admin, I want to remove the last resort manually, so that the system never ends up without a super admin.
6. As a module owner, I want a 模块配置 page inside my module, so that I manage my module without entering global system settings.
7. As a module owner, I want to create custom roles containing only my module's permission codes, so that I can model my module's real jobs (e.g. 偏差审核员).
8. As a module owner, I want to edit custom roles I created, so that I can adjust them as work changes.
9. As a module owner, I want to grant and revoke custom roles to users, so that I control who can do what in my module.
10. As a module owner, I want to appoint and remove delegates, so that routine granting doesn't depend on me alone.
11. As a module owner, I want to be unable to remove a fellow owner, so that co-owners can't lock each other out (only the super admin arbitrate).
12. As a module owner, I want multiple owners per module to be possible, so that departments with co-managers are supported.
13. As a module delegate, I want all module permissions, so that I can do any operational work in the module.
14. As a module delegate, I want to create and edit custom module roles, so that I can adapt roles without waiting for the owner.
15. As a module delegate, I want to grant custom roles to users, so that I can handle day-to-day access requests.
16. As a module delegate, I want to be blocked from appointing, editing, or removing other delegates, so that delegate membership stays the owner's decision.
17. As a regular user, I want to see menu items I don't have permission for, greyed out with a lock icon, so that I know the feature exists.
18. As a regular user, I want clicking a greyed item to show a clear no-permission page, so that I know to ask an admin for access.
19. As a regular user, I want my permissions to come only through roles, so that access is explainable and auditable.
20. As a regular user holding multiple roles in a module, I want their permissions to accumulate, so that combining roles works as expected.
21. As any user, I want role permission changes to take effect at the next authorization check, so that access changes are prompt but don't kick me out of open pages.
22. As an admin, I want deleting a role to disable its grants (restorable), so that the grant list stays clean and mistakes are reversible.
23. As an admin, I want owner/delegate roles to automatically gain new module permissions as the registry grows, so that delegated admins never silently lose capability.
24. As an admin, I want custom roles to NOT change when new permission codes appear, so that role contents only change by explicit edit.
25. As a module owner or delegate, I want the grant/role APIs to only show my module's data, so that I can't see or touch other modules.
26. As a developer, I want reserved role codes (owner/delegate) protected per module, so that no one can fake a built-in role.
27. As a developer, I want module roles to reject cross-module permission codes at the API, so that UI bypass attempts fail closed.
28. As a developer, I want the 角色档位 (admin/operator/approver/viewer) dropdown removed, so that role codes are free-form and honest.
29. As a module owner, I want each module's scattered settings pages merged into my 模块配置 page as tabs, so that configuration lives in one predictable place.
30. As a module owner, I want the 模块配置 page guarded by a module-level permission code, so that access doesn't depend on platform-level permissions.

## Implementation Decisions

### Role model and levels

- Roles gain a `level` integer: owner = 2, delegate = 1, custom roles = 0. `super_admin` is unchanged (bypass flag, not a level).
- Per business module, the registry auto-generates three entries: `{module}:owner` (level 2), `{module}:delegate` (level 1), and the permission code `{module}:admin:read` (grants entry to the module's 模块配置 page, contained in both auto-roles).
- Auto-roles auto-widen on startup sync: when a new permission code is registered for a module, both auto-roles gain it. Sync only ever adds, never removes. Custom roles never auto-change.
- Module custom roles use free-form codes (`{module}:{name}`); `owner` and `delegate` are reserved suffixes per module. Role creation for a module-scoped role rejects permission codes outside `{module}:*`.

### Level guard (the core new rule)

- To create, modify, or remove a grant for a role of level N in a module, the actor must hold a role with level strictly greater than N in the same module — or be super admin.
- This single rule yields: delegate cannot touch delegate grants (1 ≯ 1); owner cannot touch fellow owners (2 ≯ 2); only super admin manages owner grants; owners manage delegates and custom roles; delegates manage only custom roles.
- The existing guards remain: no self-granting, last-superadmin protection, scope capping.

### Data scope

- Data scope (all/department/self) is a dormant feature — no module applies it today. No special handling: owner/delegate grants default to scope=all like everything else.

### Role deletion

- Deleting a role disables its grant rows (status=disabled), rather than leaving orphaned grants pointing at a soft-deleted role. Restorable.

### Module settings unification

- Every module gets `/{module}/settings` (模块配置) in the sidebar, tab-style layout. First tab is 权限管理 (roles + grants filtered to the module). Existing scattered settings pages migrate in as tabs: quality instrument/stability reminders, hr system settings + hr settings, energy's orphaned settings page, safety/equipment existing settings.
- The page is guarded by `{module}:admin:read`; module settings APIs move off `platform:config:read` to module-level codes.

### Greyed menus

- Menu resolution keeps inaccessible items marked (noAccess) instead of filtering them out. TopNav module tabs and Sidebar items render greyed with a lock icon; clicking navigates normally, and the existing module layout guard renders the no-permission page. Backend API protection is unchanged (fail-closed binding middleware).

### UI composition

- The 权限管理 tab reuses the existing role-management and grant-management components with a module filter prop; the same components serve the global settings page (unfiltered for super admin).
- The 角色档位 dropdown is removed from the role form; codes become free-form.

### Prototype-derived decisions

The logic prototype validated the guard as a single pure function:

```python
# canTouchGrant: actor's highest level in the module must strictly exceed
# the target role's level; super admin counts as infinity.
def can_touch_grant(state, actor_id, role_code):
    role = roles[role_code]
    actor_lvl = highest_level_in(actor_id, module)  # 99 if superuser
    if actor_lvl == 99: return True
    return actor_lvl > role.level
```

## Testing Decisions

Good tests here check external behavior: an HTTP request is allowed or denied; a role set appears or not; a menu item renders greyed or normal. No internal state poking.

- **Grant/role APIs at the HTTP layer** — level guard cases: delegate-vs-delegate denied, owner-vs-owner denied, owner-manages-delegate allowed, delegate-grants-custom allowed, bystander denied, cross-module role creation denied, reserved words denied. Prior art: `tests/unit/permission/test_admin_hierarchy.py`, `tests/unit/test_permission_batch.py`.
- **Registry sync** — auto-roles generated per module; auto-widen adds new codes to owner/delegate but not custom roles; sync never removes. Prior art: `tests/unit/test_permission_tree_description.py` (registry-level tests).
- **Role deletion** — grants become disabled, permissions stop flowing, re-enable path exists.
- **Menu resolution** — pure-function tests for the noAccess marking (no rendering).
- **E2E (one Playwright pass)** — greyed menu renders for a permissionless account; click-through lands on the no-permission page; an owner account sees and enters its module's 模块配置 page.

## Out of Scope

- Data-scope (department/self) filtering adoption by business modules — the machinery stays dormant.
- Role change notifications / approval flows (delegate edits a role the owner holds — recorded in audit log, accepted risk).
- Migrating historical custom roles to any new structure.
- Department-tree-aware scopes (`department_and_children` stays equivalent to `department`).

## Further Notes

- Requirement doc (Feishu wiki): https://j0eukrlohu.feishu.cn/wiki/X6Dxw2Ubyi27X8kWTnFc7wShnIe
- Design record: `docs/adr/0008-delegated-administration.md`; vocabulary in `GLOSSARY.md` (模块负责人 / 模块代表 / 角色级别 / 授权).
- Implementation plan with ordered tasks: `plans/delegated-administration-plan.md`.
- Throwaway prototypes (not in repo): logic walkthrough and 12-module settings-page mock.
