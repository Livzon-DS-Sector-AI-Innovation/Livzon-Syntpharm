# 12: Server API types - expand

**What to build:** Typed function signatures available alongside `data: any` versions (no breakage). This is the first step of an expand-contract pattern for server API type safety. Typed versions of server API functions should be made available alongside the existing `data: any` versions.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Typed function signatures created for server API functions
- [ ] Generated types from schema.ts used for request bodies
- [ ] Both typed and untyped versions coexist without conflicts
- [ ] No existing code broken
- [ ] TypeScript compilation succeeds
