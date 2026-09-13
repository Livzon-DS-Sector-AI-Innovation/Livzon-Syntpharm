# 09 — Remove unused vars in src/actions/

**What to build:** Delete all unused imports and variables in action files. No behavioral change, zero risk.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All unused imports removed from actions
- [x] All unused variables removed from actions
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (warning count decreases)

## Summary

Fixed 104 unused vars across 18 action files:

- agent-skills.ts: removed 1 unused type (AgentSkill)
- doc-check.ts: removed 2 unused types, prefixed 4 unused params
- equipment.ts: removed 3 unused type definitions
- equipment/equipment.ts: removed 1 unused function (actionFetch)
- equipment/personnel.ts: removed 1 unused function (wrapApiCall)
- identity.ts: removed 1 unused type (LoginLog)
- inspection-table.ts: removed 1 unused type (ColumnConfig)
- instrument.ts: removed 18 unused types
- material-report.ts: removed 1 unused type (TemplateCreate)
- pressure.ts: removed 10 unused types
- product-output.ts: removed 3 unused types
- quality-cpv.ts: removed 1 unused type (CpvProductWithStats)
- quality.ts: removed 13 unused types
- registration-ledger.ts: removed 1 unused type (DateStringSchema)
- research/rd-project.ts: removed 7 unused types/functions
- safety/index.ts: removed 30 unused types
- static-data.ts: removed 1 unused type (DictOption)
- warehouse.ts: removed 5 unused types

All changes pass typecheck with no errors.
ESLint shows 0 unused vars warnings in src/actions/.
