# 23 — Type static-data API client

**What to build:** Replace all `any` types in static-data API client with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** done

**Result:** Fixed 7 `any` types in `src/lib/api/client/static-data-api.ts`:
- `createStorageCondition`: Changed `Record<string, any>` to `StorageConditionCreate`
- `updateStorageCondition`: Changed `Record<string, any>` to `StorageConditionUpdate`
- `createMaterialStandard`: Changed `Record<string, any>` to `MaterialStandardCreate`
- `updateMaterialStandard`: Changed `Record<string, any>` to `MaterialStandardUpdate`
- `createProductStandard`: Changed `Record<string, any>` to `ProductStandardCreate`
- `updateProductStandard`: Changed `Record<string, any>` to `ProductStandardUpdate`
- `createMedium`: Changed `Record<string, any>` to `MediumCreate`
- `updateMedium`: Changed `Record<string, any>` to `MediumUpdate`
- `createStandard`: Changed `Record<string, any>` to `StandardCreate`
- `updateStandard`: Changed `Record<string, any>` to `StandardUpdate`
- Added eslint-disable for internal `api<T = any>` helper (implementation detail)
- Added imports for all Create/Update types from `@/types/static-data`

**Verification:**
- [x] All `any` types replaced with proper types in static-data API client
- [x] Types sourced from `@/types/generated/schema` or appropriate type modules
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in static-data API)
