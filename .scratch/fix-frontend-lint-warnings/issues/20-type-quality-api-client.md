# 20 — Type quality API client

**What to build:** Replace all `any` types in quality API client with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All `any` types replaced with proper types in quality API client
- [ ] Types sourced from `@/types/quality` or `@/types/generated/schema`
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in quality API)
