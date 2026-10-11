# 07 — 前端交互 UI 与警示设计

**What to build:** 在导入预览界面添加一个具有工业警示风格的“强制覆盖”开关。该组件需包含二次确认逻辑，防止用户误触导致历史数据丢失。严格遵循 `/frontend-design` 技能中的“琥珀色警示开关”方案。

**Blocked by:** 06 — 后端 API 与核心逻辑支持

**Status:** ready-for-agent

### 🎨 设计规范 (Design Brief)
- **视觉令牌**: 
  - 警示色: `#F59E0B` (Amber 500)
  - 中性色: `#475569` (Slate 600)
  - 字体: Label 使用 `Inter` Medium, Warning 使用 `JetBrains Mono`
- **标志性元素**: “重力开关” (The Gravity Toggle)，拨动时背景从 Slate 渐变为 Amber。

### 💻 核心组件实现参考
请基于以下原型开发 `components/equipment/ForceOverrideToggle.tsx`：
```tsx
// 原型代码片段 (来自 frontend-design 会话)
import { useState } from 'react';
import { AlertTriangle, ShieldCheck } from 'lucide-react';

export const ForceOverrideToggle = ({ onToggle }: { onToggle: (enabled: boolean) => void }) => {
  const [isEnabled, setIsEnabled] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleToggle = () => {
    if (!isEnabled) setShowConfirm(true);
    else { setIsEnabled(false); onToggle(false); }
  };

  return (
    <div className="flex items-center gap-4 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
      <div className="flex flex-col">
        <span className="text-sm font-medium text-slate-200 flex items-center gap-2">
          {isEnabled ? <AlertTriangle className="h-4 w-4 text-amber-500" /> : <ShieldCheck className="h-4 w-4 text-slate-400" />}
          强制覆盖业务字段
        </span>
        <span className="text-xs text-slate-500 mt-1 font-mono">
          {isEnabled ? "⚠️ 系统将忽略现有数据，以 Excel 为准" : "✅ 保护已手动修正的部门与位置信息"}
        </span>
      </div>
      <button onClick={handleToggle} className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${isEnabled ? 'bg-amber-500' : 'bg-slate-600'}`}>
        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
      </button>
      {/* 模态确认弹窗逻辑此处省略，需实现二次确认 */}
    </div>
  );
};
```

### 📝 验收标准
- [ ] 实现 `ForceOverrideToggle` 组件，采用琥珀色警示色调
- [ ] 添加 Tooltip 说明：“系统将忽略现有数据，以 Excel 为准”
- [ ] 实现二次确认模态框，文案需明确告知风险（“我已知晓风险，继续”）
- [ ] 将用户选择的状态传递给后端导入接口
