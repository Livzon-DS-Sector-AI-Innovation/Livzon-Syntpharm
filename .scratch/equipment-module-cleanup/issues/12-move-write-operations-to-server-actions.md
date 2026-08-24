# 12: Move write operations to Server Actions

**What to build:** Batch delete and import operations go through Server Actions with proper authentication

**Blocked by:** 01: Add authentication to all equipment API endpoints

**Status:** ready-for-agent

- [ ] Batch delete operation implemented as Server Action
- [ ] Import operation implemented as Server Action
- [ ] Server Actions use authentication middleware
- [ ] Server Actions call backend API with auth headers
- [ ] Tests verify Server Actions work with authentication
