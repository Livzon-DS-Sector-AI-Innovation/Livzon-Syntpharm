# 22 — Type research API client

**What to build:** Replace all `any` types in research API client with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** done

**Result:** Fixed 4 `any` types in `src/lib/api/client/research/rd-project.ts`:
- `fetchAllTracks`: Changed return type from `Promise<any[]>` to `Promise<RdResearchTrack[]>`
- `fetchConclusionVersions`: Changed return type from `Promise<any[]>` to `Promise<RdTrackConclusionVersion[]>`
- Added `RdTrackConclusionVersion` to imports

**Verification:**
- [x] All `any` types replaced with proper types in research API client
- [x] Types sourced from `@/types/research` or `@/types/generated/schema`
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in research API)
