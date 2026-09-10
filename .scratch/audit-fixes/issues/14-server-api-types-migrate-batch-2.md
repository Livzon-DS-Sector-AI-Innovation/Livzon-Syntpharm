# 14: Server API types - migrate batch 2 (remaining functions)

**What to build:** All server API functions use proper types. This is the third step of an expand-contract pattern. Remaining server API functions should be migrated to use proper types instead of `data: any`.

**Blocked by:** 12, 13

**Status:** ready-for-agent

- [ ] All remaining server API functions use proper types
- [ ] No `data: any` parameters remain
- [ ] Generated types from schema.ts used for request bodies
- [ ] No functionality broken
- [ ] TypeScript compilation succeeds
- [ ] Tests still pass
