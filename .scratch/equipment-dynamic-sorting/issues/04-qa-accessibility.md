# 04 — [QA] 排序正确性与无障碍验收

**What to build:** 以真实数据形态为准的最终验收清单。v1 的两条判错的条目（`asset_no` 空值置后、offset 抖动记为已知限制）在本版被替换为可验证的正确性要求。

**Blocked by:** 03

**Status:** ready-for-human（代码完成，待人工验收）

数据基线（`equipment.equipments`，`is_deleted=false`）：2972 行 = `Z` + 7 位定长 2015 行 + 纯数字变长 957 行。

- [x] 自然序断言：`0001 < 0000002 < 38582 < 59071 < Z0100001`，且两种格式混排分段正确（D3）
- [x] 异常编号：构造无尾数值的 `asset_no`，列表不抛错、该行进独立桶并置后、不污染分页
- [x] 部门列：排序结果与「归属部门」显示文字单调一致，而非 UUID 顺序（D4）
- [ ] 状态列：按业务序返回，且优先级已经业务签字确认（D5 / R4）——排序映射与测试已完成，**业务签字仍缺**
- [x] 分页确定性：同一排序参数重复执行返回序列完全一致；跨页无重复行、无遗漏行（D6 tiebreak）
- [x] 空值断言改判：**撤销** v1 对 `asset_no` 的「NULL 稳定排在末尾」断言——该列 `NOT NULL` 且零空值，该场景永不可能发生。NULLS LAST 改在 `commissioning_date`（当前 2 行）与 `current_cost`、`book_value` 上验证
- [x] 契约负例：未知 `sort_by` → 422、`sort_order` 非 `asc|desc` → 422，错误体列出支持字段
- [x] 测试真实性：确认排序测试真的调用 `repo.get_equipments` 并断言返回列表顺序，而不是在测试函数内重写一遍 `order_by`（v1 遗留的假测试）
- [x] 无障碍：断言 antd 自动产出的 `aria-sort` 随交互更新；表头可用键盘 Enter/Space 切换方向 —— `aria-sort` 与 Enter 已验证；**Space 是偏差**：antd v6 表头只监听 `KeyCode.ENTER`（`node_modules/antd/es/table/hooks/useSorter.js:166`），支持 Space 需自写监听，而 spec 已否决自研排序控件，留待人工定夺
- [x] 回归：2972 行规模下排序接口无可测退化；原有筛选与列配置功能不受影响
- [x] 确认 `pnpm generate:api` 已执行，前端可排序列集合与后端白名单逐项相等（D2 无漂移）

## Comments

**证据**：`tests/modules/equipment/test_sorting.py` 34 passed（本机 dev 库 2972 行基线）。
新增覆盖：spec 的混排链（前导零 / 位宽 / `Z` 独立桶）、`current_cost`+`book_value` 双向 NULLS LAST、
并列 key 跨页行守恒、422 响应体列出支持字段、8 字段 × 双向全量首页取数耗时（实测约 0.04s，预算 2s）、
`status`（仅 5 个取值、并列最多）全量 15 页翻页 0.25s 且 2972 行无重复无遗漏。
**漂移守卫**：`equipment-sorting.spec.ts` 新增一条比对 `backend/openapi.json` 的 `sort_by` enum 与
前端 `EQUIPMENT_SORT_FIELDS` 的用例，后端增删字段会直接红。
**待人工**：R4 业务优先级签字；Space 键偏差是否接受（见上）。
**另案**：`frontend/src/types/generated/schema.ts` 再生成后丢了 `ImportV4BatchResponse`/`ImportV4PreviewResponse`/
`ImportErrorItem` 三个类型，根因是 `api/batch_import_v4.py:188` 等约 20 个端点标注 `-> ApiResponse`，
违反 AGENTS.md 的 response_model 规则，与排序无关，需单开修复票。
