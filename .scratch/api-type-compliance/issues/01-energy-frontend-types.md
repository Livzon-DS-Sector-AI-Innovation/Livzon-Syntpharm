# 01 — Regenerate energy frontend types

**What to build:** Frontend can use generated types for energy APIs (`EnergyDeviceConfig`, `AlertRule`, `AlertRecord`, `EnergyWorkshop`, `EnergyMonthlyRecord`). Backend is already correct; this is just regenerating types and updating frontend API calls.

**Blocked by:** None — can start immediately

**Status:** complete

- [x] Backend OpenAPI spec exported successfully
- [x] Frontend types regenerated from updated spec
- [x] Frontend energy API files (`client/energy.ts`, `server/energy.ts`) updated to use generated types
- [x] Type aliases created for backward compatibility where needed
- [x] TypeScript compilation passes
- [x] Runtime API responses match generated types (spot-check 2-3 endpoints)
- [x] Backend spec gaps documented (types not yet in OpenAPI: `EnergyOverviewData`, `EnergyData`, `EnergyStatistics`, `CollectLog`, etc.)

## Summary

Completed ticket 01 of API type compliance fix:

1. **Backend OpenAPI spec**: Already correct (energy module uses specific response models)
2. **Frontend type regeneration**: Ran `openapi-typescript` to regenerate `schema.ts` from backend spec
3. **Type aliases**: Added type aliases in `energy.ts` for backward compatibility:
   - `EnergyDeviceConfig` → `components['schemas']['EnergyDeviceConfigResponse']`
   - `AlertRule` → `components['schemas']['EnergyAlertRuleResponse']`
   - `AlertRecord` → `components['schemas']['EnergyAlertRecordResponse']`
   - `EnergyWorkshop` → `components['schemas']['EnergyWorkshopResponse']`
   - `EnergyMonthlyRecord` → `components['schemas']['EnergyMonthlyRecordResponse']`
4. **Removed hand-written interfaces**: Deleted 159 lines of hand-written interfaces that now exist in generated schema
5. **Documented backend spec gaps**: Added comment block explaining which types are NOT in backend spec yet:
   - `EnergyOverviewData`, `EnergyData`, `EnergyStatistics`
   - `CollectLog`, `CollectLogDetail`, `CollectLogDeviceDetail`
   - `TrendDataPoint`, `DistributionDataPoint`, `DeviceRankItem`
   - `FeishuImportResult`
6. **Verification**: TypeScript compilation passes with no errors

**Commit**: e224a5bb
