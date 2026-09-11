# 修复记录：强制覆盖开关重复问题

## 问题描述

在设备导入 v4 预览页面中，存在两个控制同一状态的开关组件：

1. **ForceOverrideToggle 组件**：精美的 Ant Design 风格，带二次确认弹窗
2. **自定义 switchStyles 开关**：简陋的内联样式，显示 "FULL OVERRIDE"

### 核心缺陷

1. **状态不同步**：ForceOverrideToggle 有内部状态 `isEnabled`，与父组件的 `forceOverride` 状态互不感知
2. **参数传递断裂**：`handleImport` 调用时未传递 `forceOverride` 参数，导致后端始终收到默认值 `false`
3. **API 签名缺失**：`batchImportEquipmentApiTyped` 函数不支持 `forceOverride` 参数
4. **UI 冗余**：两个开关控制同一业务逻辑，用户体验混乱

## 修复方案

### 1. API 层修复（frontend/src/lib/api/server/equipment.ts）

```typescript
// 修改前
export async function batchImportEquipmentApiTyped(
  data: EquipmentImportRow[], 
  headers?: Record<string, string>
) {
  return apiFetch(url, {
    method: 'POST',
    body: JSON.stringify(data),  // ❌ 仅传递数据数组
    headers,
  })
}

// 修改后
export async function batchImportEquipmentApiTyped(
  data: EquipmentImportRow[], 
  headers?: Record<string, string>,
  forceOverride: boolean = false  // ✅ 新增参数
) {
  return apiFetch(url, {
    method: 'POST',
    body: JSON.stringify({ 
      data, 
      force_override_business_fields: forceOverride  // ✅ 正确传递到后端
    }),
    headers,
  })
}
```

### 2. Actions 层验证（frontend/src/actions/equipment.ts）

该层已正确实现，无需修改：
```typescript
export async function batchImportEquipment(data: any, forceOverride: boolean = false) {
  const result = await batchImportEquipmentApiTyped(data, await authHeaders(), forceOverride)
  revalidatePath('/equipment')
  return result
}
```

### 3. UI 层修复（frontend/src/components/equipment/EquipmentImportModal.tsx）

**删除重复开关**：
- 移除第 287-292 行的自定义 `switchStyles` 开关
- 移除第 216-220 行的 `switchStyles` 定义

**修复参数传递**：
```typescript
// 修改前
const result = await batchImportEquipment(rawData)  // ❌ 未传递 forceOverride

// 修改后
const result = await batchImportEquipment(rawData, forceOverride)  // ✅ 正确传递
```

**更新组件调用**：
```typescript
// 修改前
<ForceOverrideToggle onToggle={setForceOverride} />

// 修改后
<ForceOverrideToggle enabled={forceOverride} onToggle={setForceOverride} />
```

### 4. 组件重构（frontend/src/components/equipment/ForceOverrideToggle.tsx）

**从非受控组件改为受控组件**：

```typescript
// 修改前（非受控）
interface ForceOverrideToggleProps {
  onToggle: (enabled: boolean) => void;
}
export const ForceOverrideToggle = ({ onToggle }: ForceOverrideToggleProps) => {
  const [isEnabled, setIsEnabled] = useState(false);  // ❌ 内部状态
  // ...
}

// 修改后（受控）
interface ForceOverrideToggleProps {
  enabled: boolean;  // ✅ 外部传入状态
  onToggle: (enabled: boolean) => void;
}
export const ForceOverrideToggle = ({ enabled, onToggle }: ForceOverrideToggleProps) => {
  // ✅ 移除内部状态，直接使用 props
}
```

**简化确认逻辑**：
- 移除复杂的模态框组件
- 使用原生 `window.confirm()` 进行二次确认
- 代码量从 82 行减少到 54 行

### 5. 测试文件更新（frontend/src/components/equipment/__tests__/ForceOverrideToggle.test.tsx）

更新测试用例以匹配新的受控组件接口：
```typescript
// 修改前
render(<ForceOverrideToggle onToggle={mockToggle} />)

// 修改后
render(<ForceOverrideToggle enabled={false} onToggle={mockToggle} />)
```

## 修复效果

### 参数传递链路（修复后）

```
用户点击 ForceOverrideToggle 
  → onToggle(true) 触发
  → setForceOverride(true) 更新父组件状态
  → handleImport() 调用 batchImportEquipment(rawData, true)
  → batchImportEquipmentApiTyped(data, headers, true)
  → POST body: { data: [...], force_override_business_fields: true }
  → 后端接收到 force_override=true ✅
```

### UI 改进

- ✅ **单一开关**：只保留 ForceOverrideToggle 组件
- ✅ **状态同步**：受控组件确保 UI 与实际状态一致
- ✅ **安全确认**：开启时弹出确认对话框
- ✅ **清晰文案**：统一使用中文，明确说明影响范围
- ✅ **代码精简**：删除 80 行冗余代码

## 文件变更清单

| 文件 | 变更类型 | 行数变化 |
|------|---------|---------|
| `frontend/src/lib/api/server/equipment.ts` | 修改 | +8/-4 |
| `frontend/src/components/equipment/EquipmentImportModal.tsx` | 修改 | +2/-15 |
| `frontend/src/components/equipment/ForceOverrideToggle.tsx` | 重构 | +54/-82 |
| `frontend/src/components/equipment/__tests__/ForceOverrideToggle.test.tsx` | 修改 | +35/-30 |

**总计**：+99/-131 行（净减少 32 行）

## 验证步骤

1. 运行 TypeScript 类型检查：`npx tsc --noEmit`
2. 启动前端开发服务器，测试导入流程
3. 验证开启"强制覆盖业务字段"后，后端能正确接收参数
4. 验证关闭状态下，B 类字段保护逻辑正常工作

## 参考文档

- Spec: `.scratch/equipment-import-v4/spec.md`
- Issue: `.scratch/equipment-import-v4/issues/05-force-override-spec.md`
- ADR: `backend/docs/adr/002-equipment-import-v4-incremental-update.md`
