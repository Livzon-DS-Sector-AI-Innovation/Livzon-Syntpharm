# 15: Server API types - contract

**What to build:** `data: any` removed from all server API functions. This is the final step of an expand-contract pattern. All untyped versions of server API functions should be removed now that all code uses typed versions.

**Blocked by:** 13, 14

**Status:** ready-for-agent

- [ ] All `data: any` parameters removed from server API functions
- [ ] Untyped function versions removed
- [ ] Only typed versions remain
- [ ] TypeScript compilation succeeds
- [ ] Tests still pass
