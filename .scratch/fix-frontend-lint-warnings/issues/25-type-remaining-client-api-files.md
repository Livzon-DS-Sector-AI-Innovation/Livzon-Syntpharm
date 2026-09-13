# 25 — Type remaining client API files

**What to build:** Replace all `any` types in remaining API client files (administration, warehouse, product, etc.) with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** done

**Result:** Fixed 3 `any` types across 2 files:
- `src/lib/api/client/equipment.ts`:
  - `batchDeleteEquipments`: Changed return type from `Promise<any>` to `Promise<void>`
  - Changed `fetchApi<any>` to `fetchApi<void>`
- `src/lib/api/client/inspection.ts`:
  - `fetchEquipmentsClient`: Changed return type from `Promise<{ items: any[]; total: number }>` to `Promise<{ items: Equipment[]; total: number }>`
  - Added `Equipment` to imports from `@/types/equipment/generated-bridge`

**Verification:**
- [x] All `any` types replaced with proper types in remaining API client files
- [x] Types sourced from appropriate `@/types/...` modules or `@/types/generated/schema`
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in remaining API clients)
