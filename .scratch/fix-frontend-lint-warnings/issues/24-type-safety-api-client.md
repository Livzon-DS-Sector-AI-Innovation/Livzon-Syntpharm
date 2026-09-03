# 24 — Type safety API client

**What to build:** Replace all `any` types in safety API client with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** done

**Result:** Already completed. Zero `any` warnings in `src/lib/api/client/safety.ts`.

**Verification:**
- [x] All `any` types replaced with proper types in safety API client
- [x] Types sourced from `@/types/safety` or `@/types/generated/schema`
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in safety API)
