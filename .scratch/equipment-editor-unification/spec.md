# 设备台账编辑器统一与交互修复 Spec

## Problem Statement

用户在设备台账页面点击“新增分类”按钮时无任何反应，且“新增位置”的逻辑与分类不一致（一套用轻量级 Editor，一套用重型 Drawer），导致代码维护困难且用户体验割裂。用户希望采用统一的轻量级录入方式，并确保功能可用。

## Solution

弃用原有的 Store 驱动的全屏/抽屉式编辑器（Drawer），全面转向组件内状态管理的轻量级编辑器（Editor）。通过重构 `CategoryTree` 和 `LocationTree` 的状态管理逻辑，确保点击触发器能正确弹出录入框，并补全缺失的 `LocationEditor` 组件。

## User Stories

1. As a 设备管理员, I want to click the "New Category" button and see an inline editor immediately, so that I can quickly add a classification without context switching.
2. As a 设备管理员, I want the "New Location" button to behave identically to the category button, so that my interaction model is consistent across the page.
3. As a developer, I want to remove the unused Drawer logic from the global store, so that the codebase remains clean and free of dead code.
4. As a user, I want to see clear validation errors if I try to create a category/location with a duplicate name, so that I don't create messy data.
5. As a user, I want the editor to close automatically after a successful creation, so that I can continue browsing the tree.

## Implementation Decisions

### 架构决策：状态上移 (State Lifting)
- **决策**：放弃 `CategoryEditor` 组件内部的 `trigger` 属性模式。
- **理由**：在复杂的树形结构中，将 `open` 状态放在父组件（`CategoryTree`/`LocationTree`）中更易于调试和控制事件冒泡。
- **实现**：在 `CategoryTree` 中使用 `useState` 控制 `CategoryEditor` 的显隐。

### 组件复用与新建
- **决策**：为位置管理新建专用的 `LocationEditor` 组件，而不是强行复用 `CategoryEditor`。
- **理由**：位置和分类的业务字段（如层级路径、坐标备注）差异较大，专用组件能提供更好的类型安全和扩展性。

### Store 清理策略
- **决策**：分阶段清理。先实现新 Editor 并确保其稳定运行，再删除 Store 中的 `categoryDrawerOpen` 等旧状态。
- **理由**：避免在解决“点击无反应”的核心 Bug 时引入额外的回归风险。

### API 对接
- **决策**：直接使用现有的 `createCategory` 和 `createLocation` Actions。
- **理由**：后端 API (`POST /api/v1/equipment/categories` 和 `locations`) 已验证可用，无需修改接口契约。

## Testing Decisions

### 测试重点
- **交互测试**：验证点击“新增”按钮后，编辑器是否正确弹出且焦点自动落入输入框。
- **边界测试**：验证在空树状态下点击 CTA 按钮是否能正常触发创建流程。
- **一致性测试**：对比分类和位置的录入体验，确保视觉和行为完全对齐。

### 测试工具
- 使用 Playwright 进行 E2E 测试，模拟从点击按钮到提交成功的全过程。
- 参考 `.scratch/equipment-import-v3/issues/05-e2e-validation.md` 中的测试模式。

## Out of Scope

- **批量编辑**：本次仅关注单条记录的快速新增。
- **拖拽排序**：分类/位置的层级调整仍通过手动选择父级完成，不涉及拖拽交互。
- **后端 Schema 变更**：不修改现有的数据库表结构。

## Further Notes

- **视觉反馈**：在提交过程中，按钮应显示 Loading 状态，防止用户重复点击。
- **错误处理**：如果后端返回 409 (Conflict)，前端应在编辑器内部显示红色的错误提示，而不是通用的 Toast。
