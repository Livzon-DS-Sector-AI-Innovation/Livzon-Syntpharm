# 07: Replace raw fetch with authenticated API helpers

**What to build:** All API calls automatically include auth headers. Client code should use apiGet()/apiFetch() helpers instead of raw fetch() calls, ensuring authentication headers are automatically included.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] fetchInspectionTemplateItemsClient uses apiGet() instead of raw fetch()
- [ ] batchDeleteEquipments uses apiFetch() instead of raw fetch()
- [ ] All other raw fetch() calls in client API files replaced with authenticated helpers
- [ ] Auth headers are automatically included in all API calls
- [ ] Existing functionality preserved
- [ ] Tests still pass
