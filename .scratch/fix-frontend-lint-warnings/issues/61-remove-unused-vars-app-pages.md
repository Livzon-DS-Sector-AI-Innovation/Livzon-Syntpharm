# 61 — Remove unused vars in app pages

**What to build:** Remove or prefix with `_` all unused variables/imports in src/app/(dashboard)/*/page.tsx files

**Status:** done

## Files fixed

- src/app/(dashboard)/administration/login-logs/page.tsx: Removed queryClient usage and useQueryClient import
- src/app/(dashboard)/energy/collect-logs/page.tsx: Removed queryClient usage and useQueryClient import
- src/app/(dashboard)/energy/devices/page.tsx: Removed EnergyDeviceConfig and PaginatedResponse imports
- src/app/(dashboard)/equipment/assets/EquipmentPage.tsx: Renamed setLoading to _setLoading in destructuring
- src/app/(dashboard)/quality/material-report/page.tsx: Renamed refetch to _refetch in destructuring
- src/app/(dashboard)/quality/page.tsx: Removed UpcomingInstrument and ExpiringReagent interfaces

## Acceptance Criteria

- [x] All unused vars removed or prefixed with `_` in page.tsx files
- [x] `pnpm lint` shows 0 `@typescript-eslint/no-unused-vars` warnings in src/app/
- [x] `tsc --noEmit` passes
