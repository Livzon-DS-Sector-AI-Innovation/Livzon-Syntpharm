# 能源单耗分析功能 - TDD 测试清单

## ✅ 已完成的测试

### 1. 核心逻辑单元测试
- [x] `calculate_unit_consumption` - 单耗计算
- [x] `calculate_deviation_rate` - 偏差率计算  
- [x] `determine_deviation_status` - 偏差状态判定
- [x] 异常处理（产量为0、负数等）

**测试文件**: `backend/tests/modules/energy/test_unit_consumption.py`

### 2. E2E 测试框架
- [x] 基础页面加载测试
- [x] 目标设定流程
- [x] AI 分析触发

**测试文件**: `frontend/e2e/energy-unit-consumption.spec.ts`

## ❌ 缺失的测试

### 1. API 层集成测试
- [ ] POST `/api/v1/energy/targets` - 创建目标
- [ ] GET `/api/v1/energy/targets/{workshop_id}/{target_month}` - 查询目标
- [ ] PUT `/api/v1/energy/targets/{target_id}` - 更新目标
- [ ] POST `/api/v1/energy/ai-analysis-v2` - AI 分析

**需要补充**: `backend/tests/integration/test_energy_api.py`

### 2. Service 层测试
- [ ] `prepare_ai_analysis_data` - 数据准备
- [ ] `create_target` - 创建目标
- [ ] `get_target` - 查询目标
- [ ] `update_target` - 更新目标

**需要补充**: `backend/tests/modules/energy/test_service.py`

### 3. Repository 层测试
- [ ] `get_monthly_energy_total` - 月度能耗汇总
- [ ] 数据库查询正确性

**需要补充**: `backend/tests/modules/energy/test_repository.py`

### 4. E2E 完整流程测试
- [ ] 登录认证流程
- [ ] 完整的目标设定 → 输入产量 → AI 分析流程
- [ ] 错误场景处理（无数据、网络错误等）
- [ ] 单位显示验证（kg 而非件）

**需要修复**: `frontend/e2e/energy-unit-consumption.spec.ts`

### 5. 类型安全测试
- [ ] TypeScript 类型检查通过
- [ ] Pydantic schema 验证通过
- [ ] 前后端契约一致性验证

## 🔧 当前已知问题

1. **单位不一致**: 前端已修复为 kg，但 E2E 测试中仍使用"件"
2. **缺少登录逻辑**: E2E 测试中的登录步骤是 TODO
3. **选择器可能不准确**: 需要验证实际页面元素

## 📋 下一步行动

### 优先级 P0（必须完成）
1. 修复 E2E 测试中的单位问题
2. 添加登录逻辑到 E2E 测试
3. 运行 E2E 测试验证完整流程

### 优先级 P1（应该完成）
4. 补充 API 层集成测试
5. 补充 Service 层测试
6. 运行所有单元测试

### 优先级 P2（可以延后）
7. 补充 Repository 层测试
8. 添加性能测试
9. 添加安全测试

## 🎯 验收标准

- [ ] 所有单元测试通过（pytest）
- [ ] 所有 E2E 测试通过（Playwright）
- [ ] TypeScript 类型检查通过（tsc --noEmit）
- [ ] Python lint 检查通过（ruff check）
- [ ] 前端页面显示单位为 kg
- [ ] API 返回正确的错误码和消息
- [ ] 数据库表结构完整且正确
