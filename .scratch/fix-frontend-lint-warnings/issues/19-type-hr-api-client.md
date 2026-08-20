# 19 — Type hr API client

**What to build:** Replace all `any` types in hr API client with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All `any` types replaced with proper types in hr API client
- [ ] Types sourced from `@/types/hr` or `@/types/generated/schema`
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in hr API)
