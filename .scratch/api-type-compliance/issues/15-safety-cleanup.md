# 15 — Safety frontend type definition cleanup

**What to build:** All hand-written API types removed from `safety.ts`. Only backend spec gaps remain, clearly documented. All API calls use generated types.

**Blocked by:** 14

**Status:** ready-for-agent

- [ ] Hand-written API types removed from `safety.ts` (except backend spec gaps)
- [ ] Type aliases added for generated types where needed
- [ ] All API calls in `lib/api/server/safety.ts` use generated types
- [ ] Backend spec gaps documented with JSDoc comments explaining which types need backend work
- [ ] TypeScript compilation passes
- [ ] No audit findings for "API 类型来源/必须从 generated schema 导入" in safety module
