# 23 — Type static-data API client

**What to build:** Replace all `any` types in static-data API client with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All `any` types replaced with proper types in static-data API client
- [ ] Types sourced from `@/types/generated/schema` or appropriate type modules
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in static-data API)
