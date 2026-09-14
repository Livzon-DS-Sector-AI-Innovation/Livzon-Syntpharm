# 02 — [Frontend] 表头交互 + URL 同步 + 视觉基线

**What to build:** 基于 Ant Design 受控模式实现表头排序，同步 URL 状态（切换排序时重置页码至 1），并应用“精密仪器”风格的视觉基线（56px 行高、等宽字体、方向性下划线）。

**Blocked by:** None (API Contract is frozen in spec)

**Status:** ready-for-agent

- [ ] 实现自定义 Sort Icon（方向性渐变下划线）并集成到 Antd Table
- [ ] 增加右上角“排序状态胶囊”标签
- [ ] 实现 URL Query Params 的读写同步及页码重置逻辑
- [ ] 优化表格视觉基线：行高 56px，ID 列应用 Monospace 字体
