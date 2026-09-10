# 03: Fix CORS configuration

**What to build:** Production requires explicit FRONTEND_URL, no silent localhost fallbacks

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] Production environment requires FRONTEND_URL to be set
- [x] No silent fallback to localhost:3000 in production
- [x] CORS configuration uses explicit allowed origins list
- [x] Development environment still allows localhost for local development
- [ ] Tests verify CORS behavior in different environments
