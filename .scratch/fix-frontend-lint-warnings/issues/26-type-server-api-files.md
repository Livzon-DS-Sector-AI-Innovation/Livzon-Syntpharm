# 26 — Type server API files

**What to build:** Replace all `any` types in server-side API files (src/lib/api/server/) with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All `any` types replaced with proper types in server API files
- [ ] Types sourced from appropriate `@/types/...` modules or `@/types/generated/schema`
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in server API)
