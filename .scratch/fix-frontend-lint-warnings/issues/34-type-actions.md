# 34 — Type all action files

**What to build:** Replace all `any` types in action files (src/actions/) with proper types. This is the parent ticket for 39 child tickets that break down the work by domain.

**Blocked by:** None — can start immediately

**Status:** in-progress

See spec: `.scratch/fix-frontend-lint-warnings/specs/type-actions-breakdown.md`

## Child Tickets

### Safety Domain (12 tickets)
- [ ] 34.1: Type safety check actions
- [ ] 34.2: Type safety hazard actions
- [ ] 34.3: Type safety accident actions
- [ ] 34.4: Type safety contractor actions
- [ ] 34.5: Type safety training actions
- [ ] 34.6: Type safety regulation actions
- [ ] 34.7: Type safety knowledge base actions
- [ ] 34.8: Type safety special operations actions
- [ ] 34.9: Type safety EHS change actions
- [ ] 34.10: Type safety occupational health actions
- [ ] 34.11: Type safety daily risk report actions
- [ ] 34.12: Type safety helper functions

### HR Domain (3 tickets)
- [ ] 34.13: Type HR employee actions
- [ ] 34.14: Type HR training actions
- [ ] 34.15: Type HR annual training plan actions

### Equipment Domain (3 tickets)
- [ ] 34.16: Type equipment main actions
- [ ] 34.17: Type equipment inspection actions
- [ ] 34.18: Type equipment personnel actions

### Energy Domain (2 tickets)
- [ ] 34.19: Type energy device actions
- [ ] 34.20: Type energy alert actions

### Research Domain (3 tickets)
- [ ] 34.21: Type research project actions
- [ ] 34.22: Type research module actions
- [ ] 34.23: Type research deliverable actions

### Quality Domain (4 tickets)
- [ ] 34.24: Type quality main actions
- [ ] 34.25: Type quality CPV actions
- [ ] 34.26: Type quality inspection table actions
- [ ] 34.27: Type quality doc-check actions

### Registration Domain (3 tickets)
- [ ] 34.28: Type registration main actions
- [ ] 34.29: Type registration ledger actions
- [ ] 34.30: Type regulatory tracker actions

### Other Domains (9 tickets)
- [ ] 34.31: Type deviation actions
- [ ] 34.32: Type material-report actions
- [ ] 34.33: Type static-data actions
- [ ] 34.34: Type validation-audit actions
- [ ] 34.35: Type product actions
- [ ] 34.36: Type administration actions
- [ ] 34.37: Type dossier-writer actions
- [ ] 34.38: Type equipment-personnel actions
- [ ] 34.39: Type small utility actions

## Acceptance Criteria

- [ ] All 39 child tickets completed
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in `src/actions/`
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes
