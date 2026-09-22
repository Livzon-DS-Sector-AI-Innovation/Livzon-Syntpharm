# 14 — Safety actions file refactor

**What to build:** All safety actions use specific response types instead of generic `ApiResponse<T>`. TypeScript compilation passes with zero errors. This is a wide refactor affecting 391 references in `src/actions/safety/index.ts`.

**Blocked by:** 09, 10, 11, 12, 13

**Status:** ready-for-agent

- [ ] All `ApiResponse<T>` references in `src/actions/safety/index.ts` replaced with specific response types from generated schema
- [ ] Type aliases added for backward compatibility where needed
- [ ] All action functions return concrete response types
- [ ] TypeScript compilation passes with zero errors
- [ ] No `ApiResponse<T>` references remaining in safety actions
- [ ] Runtime behavior unchanged (verify a few actions in browser)
