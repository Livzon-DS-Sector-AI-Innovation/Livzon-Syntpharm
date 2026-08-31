# 03 — 前端反馈与错误处理 (Frontend Feedback & Error Handling)

**What to build:** 
完善前端的交互体验，确保用户能清晰感知同步状态：
1. 增加 Loading 状态，防止重复提交。
2. 成功时展示详细的四类统计信息（Updated/Migrated/Inserted/Deleted）。
3. 失败时提供明确的错误提示（文件格式错误、解析失败、部分失败等）。

**Blocked by:** 01 — 端到端最小闭环 (可与 02 并行开发)

**Status:** ready-for-agent

- [ ] 实现文件上传前的格式校验（仅限 .xls/.xlsx）。
- [ ] 对接 API 响应，解析并展示统计面板。
- [ ] 处理网络错误或服务器异常，给出友好的用户提示。
- [ ] 确保各类异常输入下页面不白屏、不卡死。
