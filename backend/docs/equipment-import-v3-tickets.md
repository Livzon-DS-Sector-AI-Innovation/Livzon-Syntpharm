# 设备导入 v3 - 任务拆解

**来源**: [equipment-import-v3-spec-final.md](./equipment-import-v3-spec-final.md)  
**创建日期**: 2026-08-18

---

## 垂直切片拆解原则

每个切片必须：
1. ✅ 包含完整的测试（TDD）
2. ✅ 可独立验证
3. ✅ 交付可用的功能增量
4. ❌ 不依赖其他未完成的切片

---

## 🎫 Ticket 1: 智能推断函数单元测试

**优先级**: P0 (阻塞后续所有切片)  
**预估工时**: 30 分钟  
**阻塞关系**: 无

### 验收标准
- [ ] `test_infer_equipment_class()` 覆盖 5 种资产类别
- [ ] `test_infer_importance()` 覆盖 3 档成本分级
- [ ] `test_infer_status()` 覆盖报废状态映射
- [ ] 所有测试通过

### 文件清单
- `backend/tests/modules/equipment/test_smart_inference.py` (新增)

### 实施步骤
1. 创建测试文件
2. 编写 3 个测试函数
3. 运行 `pytest` 验证（此时应失败，因为函数尚未实现）

---

## 🎫 Ticket 2: 部门映射增强与降级逻辑

**优先级**: P0  
**预估工时**: 45 分钟  
**阻塞关系**: 依赖 Ticket 1（需要 infer 函数）

### 验收标准
- [ ] `DEPT_MAPPING_V3` 包含溶剂回收车间各岗位
- [ ] `map_department_name_v3()` 实现降级逻辑
- [ ] 单元测试验证映射和降级行为
- [ ] 预览接口返回 warning 列表

### 文件清单
- `backend/app/modules/equipment/api/batch_import.py` (修改)
- `backend/tests/modules/equipment/test_department_mapping.py` (新增)

### 实施步骤
1. 扩展 `DEPT_MAPPING_V3`
2. 实现 `map_department_name_v3()`
3. 编写单元测试
4. 更新预览接口返回 warnings

---

## 🎫 Ticket 3: 预览接口集成智能推断

**优先级**: P1  
**预估工时**: 1 小时  
**阻塞关系**: 依赖 Ticket 1, Ticket 2

### 验收标准
- [ ] 预览接口调用 infer 函数
- [ ] 响应体包含 `equipment_class`, `importance`, `status`
- [ ] 响应体包含 `technical_params`（含"数量"）
- [ ] 使用真实 Excel 数据测试，valid_count = 2970

### 文件清单
- `backend/app/modules/equipment/api/batch_import.py` (修改 preview_import 函数)
- `backend/tests/modules/equipment/test_preview_integration.py` (新增)

### 实施步骤
1. 修改 `preview_import()` 调用 infer 函数
2. 构建 technical_params
3. 编写集成测试
4. 手动测试预览接口

---

## 🎫 Ticket 4: 批量导入接口集成智能推断

**优先级**: P1  
**预估工时**: 1 小时  
**阻塞关系**: 依赖 Ticket 3

### 验收标准
- [ ] 批量导入接口调用 infer 函数
- [ ] 部门映射失败不跳过数据（department_id = NULL）
- [ ] 导入成功后检查数据库中的 technical_params
- [ ] 导入成功率 > 95%

### 文件清单
- `backend/app/modules/equipment/api/batch_import.py` (修改 batch_import 函数)
- `backend/tests/modules/equipment/test_batch_import_integration.py` (新增)

### 实施步骤
1. 修改 `batch_import()` 调用 infer 函数
2. 调整部门映射失败的处理逻辑
3. 编写集成测试
4. 手动测试批量导入

---

## 🎫 Ticket 5: 前端表格显示数量列

**优先级**: P2  
**预估工时**: 30 分钟  
**阻塞关系**: 无（可并行）

### 验收标准
- [ ] `EquipmentTable.tsx` 新增"数量"列
- [ ] 从 `technical_params["数量"]` 读取并显示
- [ ] NULL 值显示 "-"
- [ ] TypeScript 类型检查通过

### 文件清单
- `frontend/src/components/equipment/EquipmentTable.tsx` (修改)

### 实施步骤
1. 在 columns 数组中新增数量列
2. 实现 render 函数
3. 运行 `tsc --noEmit` 验证

---

## 🎫 Ticket 6: 端到端测试与文档归档

**优先级**: P2  
**预估工时**: 1 小时  
**阻塞关系**: 依赖 Ticket 4, Ticket 5

### 验收标准
- [ ] 完整流程测试：上传 → 预览 → 导入 → 验证
- [ ] ADR 001 已归档
- [ ] CONTEXT.md 已更新
- [ ] 代码通过 `ruff check` 和 `tsc --noEmit`

### 文件清单
- `backend/docs/adr/001-equipment-import-v3.md` (已存在)
- `CONTEXT.md` (已存在，需更新)
- `backend/tests/modules/equipment/test_e2e_import.py` (新增)

### 实施步骤
1. 编写端到端测试
2. 更新 CONTEXT.md
3. 运行本地预检
4. 提交代码

---

## 执行顺序建议

```
Ticket 1 → Ticket 2 → Ticket 3 → Ticket 4 → Ticket 5 → Ticket 6
                                    ↑
                              Ticket 5 可并行
```

---

*任务拆解者: AI Assistant*  
*审核状态: Pending Review*
