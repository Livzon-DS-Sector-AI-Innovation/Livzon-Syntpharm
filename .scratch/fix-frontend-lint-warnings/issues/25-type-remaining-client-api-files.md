# 25 — Type remaining client API files

**What to build:** Replace all `any` types in remaining API client files (administration, warehouse, product, etc.) with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All `any` types replaced with proper types in remaining API client files
- [ ] Types sourced from appropriate `@/types/...` modules or `@/types/generated/schema`
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in remaining API clients)
