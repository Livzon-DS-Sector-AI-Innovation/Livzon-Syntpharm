# 05 — 工业色彩主题扩展

**What to build:** 在现有 Ant Design 主题基础上，添加工业风格的色彩令牌和排版系统。

**Blocked by:** 01 (需要先完成基础交互优化)

**Blocking:** None

**Status:** ready-for-agent

## Acceptance Criteria

- [ ] 在 `lib/antd-theme.ts` 中添加 `industrialPalette` 色彩对象
- [ ] 定义以下色彩令牌：
  - deepSteel: #1e293b（深蓝灰，用于标题和重点文字）
  - machineBlue: #0ea5e9（机械蓝，用于链接和强调）
  - safetyOrange: #f97316（安全橙，用于警示和操作按钮）
  - signalGreen: #10b981（信号绿，用于成功状态）
- [ ] 更新全局 CSS 变量，使新色彩可在组件中使用
- [ ] 在 `EquipmentPage` 的标题和副标题中应用新色彩
- [ ] 确保新色彩与现有 Ant Design 组件兼容（不破坏原有样式）

## Implementation Notes

- 使用 CSS custom properties (--color-deep-steel 等) 定义色彩令牌
- 在 `global.css` 或 `layout.tsx` 中注入变量
- 保持向后兼容：旧组件仍可使用原有 Ant Design 色彩
- 文件修改：
  - `frontend/src/lib/antd-theme.ts`
  - `frontend/src/app/(dashboard)/equipment/assets/page.tsx` 或全局样式文件

## Testing

- [ ] 手动测试：验证新色彩在页面上正确应用
- [ ] 手动测试：验证旧组件样式未被破坏
- [ ] 手动测试：在不同浏览器中验证 CSS 变量兼容性
