# 12: Move write operations to Server Actions

**What to build:** Batch delete and import operations go through Server Actions with proper authentication

**Blocked by:** 01: Add authentication to all equipment API endpoints

**Status:** completed

- [x] Batch delete operation implemented as Server Action
- [x] Import operation implemented as Server Action
- [x] Server Actions use authentication middleware
- [x] Server Actions call backend API with auth headers
- [x] Tests verify Server Actions work with authentication
