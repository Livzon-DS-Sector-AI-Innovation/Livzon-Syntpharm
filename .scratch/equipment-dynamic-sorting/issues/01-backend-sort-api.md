# 01 — [Backend] 排序契约返工（自然序 + 白名单 + 稳定分页）

**What to build:** 把已上线的设备列表排序接口收敛到仓库既有契约（`order` → `sort_order`），并修掉两处会直接产出错误结果的缺陷：部门按 UUID 排序、`asset_no` 词法序错误。同时把「静默兜底」换成显式失败，并为 offset 分页补上确定性 tiebreak。

**Blocked by:** None — 但**必须早于 02 合入**：02 的可点列集合以本票白名单生成的 `EquipmentSortBy` 类型为基准做校验。

**Status:** ready-for-human（代码完成，待人工验收）

已提交基线 `775ff0a3`：`sort_by`/`order` 接收、`SORT_MAP` 4 字段、`nulls_last` 均已实现。下列条目全部是返工。

- [x] **D1** 参数改名 `order` → `sort_order`，对齐 `hr`/`production`。受影响：`api/equipment.py:254`、`service/equipment.py:239,244`、`repository/equipment.py:384`（`public_api.py:34,51` 不传排序参数，不受影响）
- [x] **D2** 白名单由 4 项扩到 8 项：`asset_no`、`name`、`commissioning_date`、`current_cost`、`book_value`、`department_name`、`status`、`created_at`
- [x] **D3** `asset_no` 采用 Spec 定义的完整自然序表达式（见 spec D3，可直接粘贴）：
  ```sql
  (CASE WHEN equipments.asset_no ~ '[0-9]$' THEN 0 ELSE 1 END) ASC,
  coalesce((regexp_match(equipments.asset_no, '^[A-Za-z]*'))[1], '') ASC,
  lpad(coalesce((regexp_match(equipments.asset_no, '[0-9]+$'))[1], ''), 12, '0') ASC,
  equipments.asset_no COLLATE "C" ASC,
  equipments.id ASC
  ```
  两个坑：`regexp_match(...)[1]` 必须带括号（裸下标是 PG 语法错误）；列名带 `equipments.` 限定（D4 join 后 `id` 会 ambiguous）。DESC 时前四段各自反转，末尾 `equipments.id ASC` 恒定。确保 `0001 < 0000002 < Z0100001` 且异常编号不抛错。
- [x] **D4** 部门排序键改为部门名称。现状 `department_id` 映射到 UUID 列，与界面「归属部门」文字顺序无关
- [x] **D5** `status` 按业务序映射，非中文字典序（优先级待业务确认，见 spec R4）
- [x] **D6** 每个 `ORDER BY` 末尾追加 `Equipment.id`，保证行序确定
- [x] **D12** `sort_by`/`sort_order` 用 `Literal` 声明（非法值 FastAPI 自动 422，且 OpenAPI 反映为 enum——02 的类型对齐依赖此项，见 spec D2/D12）；移除 `SORT_MAP.get(sort_by, asset_no)` 静默兜底，未知字段显式失败
- [x] 空值语义改为按列声明：撤销 `asset_no` 上的 `nulls_last`。仅在以下 4 列应用 `NULLS LAST`：`commissioning_date`, `current_cost`, `book_value`, `department_name`。
- [x] 重写 `tests/modules/equipment/test_sorting.py`：当前测试在函数内重新内联了一遍 `order_by`、从未调用 `repo.get_equipments`，上述任何返工它都是绿的
- [x] 收尾：执行 `pnpm generate:api`。`src/types/generated/openapi.json` 中该接口 GET 参数仍是返工前的 7 个、不含排序参数，02 依赖该产物；生成后须确认 `sort_by` 是 8 值 `enum` 而非裸 `string`

若需拆两次合入：D1 + D12 + 生成物为契约组，D2–D5 为语义组；但 D6 与测试重写必须随任一次合入。

## Comments

**验证**：`docker exec -i erp-backend uv run pytest tests/modules/equipment/test_sorting.py` → 34 passed。
`sort_by`/`sort_order` 在 `backend/openapi.json` 已是 8 值 / 2 值 enum；NULLS LAST 仅作用于
`commissioning_date`、`current_cost`、`book_value`、`department_name`（`repository/equipment.py:408`）；
`asset_no` 自然序四段 + `equipments.id` tiebreak 已按 spec D3 落地。
**遗留**：该模块 `api/batch_import_v4.py` 等 6 个文件仍有 28 条 ruff 违规（E501/E701/W291），属既有债务，未随本票处理。
