# 34.16 — Type equipment main actions

**What to build:** Type all equipment main action functions in src/actions/equipment.ts and src/actions/equipment/equipment.ts (getEquipmentCategories, createEquipment, updateEquipment, deleteEquipment, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/equipment.ts, src/actions/equipment/equipment.ts

## Acceptance Criteria

- [ ] All equipment main action functions have explicit return types
- [ ] All `as any` type assertions removed
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
