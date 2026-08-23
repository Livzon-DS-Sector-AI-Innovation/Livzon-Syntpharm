# Type Actions Breakdown Spec

## Problem Statement

Ticket 34 has 843 `@typescript-eslint/no-explicit-any` warnings in `src/actions/` files. These warnings exist because action functions use `as any` type assertions to bypass type checking when calling server API functions that return `any`.

The warnings are distributed across 38 files, with the largest being:
- safety/index.ts: 305 warnings
- hr.ts: 83 warnings  
- equipment.ts: 57 warnings
- equipment/equipment.ts: 42 warnings
- energy.ts: 40 warnings

## Solution

Break down ticket 34 into 39 smaller tickets (plus ticket 34 as parent), each focusing on a specific domain or module. Each ticket will:

1. Define proper return types for action functions in that domain
2. Remove `as any` type assertions
3. Ensure components consuming those actions receive properly typed data
4. Pass `tsc --noEmit` and have zero `@typescript-eslint/no-explicit-any` warnings in the targeted files

## Implementation Decisions

### Ticket Breakdown Strategy

**Large files (>20 warnings)**: Split by function category within the domain
- Safety (306 warnings): Split into 12 tickets by entity type (checks, hazards, accidents, contractors, training, regulations, knowledge, special operations, EHS changes, occupational health, daily risk reports, helpers)
- HR (83 warnings): Split into 3 tickets by function area (employees, training, annual training plans)
- Equipment (121 warnings): Split into 3 tickets by sub-module (main, inspection, personnel)
- Energy (40 warnings): Split into 2 tickets (devices, alerts)
- Research (85 warnings): Split into 3 tickets (projects, modules, deliverables)
- Quality (51 warnings): Split into 4 tickets (main, CPV, inspection table, doc-check)
- Registration (31 warnings): Split into 3 tickets (main, ledger, regulatory tracker)

**Medium files (8-20 warnings)**: One ticket per file
- deviation.ts (20 warnings)
- material-report.ts (14 warnings)
- static-data.ts (22 warnings)
- validation-audit.ts (9 warnings)
- product actions (15 warnings across 3 files)
- administration.ts (8 warnings)
- dossier-writer.ts (7 warnings)
- equipment-personnel.ts (8 warnings)

**Small files (1-7 warnings)**: Group by domain
- Small utility actions (16 warnings across 8 files: admin, environment, identity, pressure, ai-parse, instrument, procurement, users)

### Implementation Pattern

For each action function:

```typescript
// Before
export async function getChecks(params: SafetyCheckQueryParams = {}) {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getChecks(params, authHeaders) as any as any
}

// After
export async function getChecks(
  params: SafetyCheckQueryParams = {}
): Promise<ApiResponse<SafetyCheck[]>> {
  const authHeaders = await getAuthHeaders()
  return safetyApi.getChecks(params, authHeaders) as ApiResponse<SafetyCheck[]>
}
```

Key points:
- Use existing types from `src/types/` directory
- Server API functions still return `any` (ticket 59 will fix this later)
- Action functions provide the type boundary with explicit return types
- Components automatically receive proper types

### Testing Decisions

- Run `tsc --noEmit` after each ticket to ensure no type errors
- Run `pnpm eslint` on modified files to verify zero `any` warnings
- Manual smoke test: verify affected pages still load and function correctly
- No unit tests needed (type-only changes, no logic changes)

## Ticket List

**Parent**: Ticket 34 — Type all action files (843 warnings)

**Safety Domain (12 tickets)**:
- Ticket 34.1: Type safety check actions
- Ticket 34.2: Type safety hazard actions
- Ticket 34.3: Type safety accident actions
- Ticket 34.4: Type safety contractor actions
- Ticket 34.5: Type safety training actions
- Ticket 34.6: Type safety regulation actions
- Ticket 34.7: Type safety knowledge base actions
- Ticket 34.8: Type safety special operations actions
- Ticket 34.9: Type safety EHS change actions
- Ticket 34.10: Type safety occupational health actions
- Ticket 34.11: Type safety daily risk report actions
- Ticket 34.12: Type safety helper functions

**HR Domain (3 tickets)**:
- Ticket 34.13: Type HR employee actions
- Ticket 34.14: Type HR training actions
- Ticket 34.15: Type HR annual training plan actions

**Equipment Domain (3 tickets)**:
- Ticket 34.16: Type equipment main actions
- Ticket 34.17: Type equipment inspection actions
- Ticket 34.18: Type equipment personnel actions

**Energy Domain (2 tickets)**:
- Ticket 34.19: Type energy device actions
- Ticket 34.20: Type energy alert actions

**Research Domain (3 tickets)**:
- Ticket 34.21: Type research project actions
- Ticket 34.22: Type research module actions
- Ticket 34.23: Type research deliverable actions

**Quality Domain (4 tickets)**:
- Ticket 34.24: Type quality main actions
- Ticket 34.25: Type quality CPV actions
- Ticket 34.26: Type quality inspection table actions
- Ticket 34.27: Type quality doc-check actions

**Registration Domain (3 tickets)**:
- Ticket 34.28: Type registration main actions
- Ticket 34.29: Type registration ledger actions
- Ticket 34.30: Type regulatory tracker actions

**Other Domains (9 tickets)**:
- Ticket 34.31: Type deviation actions
- Ticket 34.32: Type material-report actions
- Ticket 34.33: Type static-data actions
- Ticket 34.34: Type validation-audit actions
- Ticket 34.35: Type product actions (product.ts, product-output.ts, product-sync.ts)
- Ticket 34.36: Type administration actions
- Ticket 34.37: Type dossier-writer actions
- Ticket 34.38: Type equipment-personnel actions
- Ticket 34.39: Type small utility actions (admin, environment, identity, pressure, ai-parse, instrument, procurement, users)

## Out of Scope

- Typing server API base functions (ticket 59)
- Adding runtime validation or type guards
- Refactoring action function signatures (only adding return types)
- Creating new type definitions (reuse existing types from src/types/)

## Further Notes

- This breakdown allows incremental progress without breaking the build
- Each ticket is independently testable and mergeable
- Total of 40 tickets (1 parent + 39 children)
- Estimated effort: 15-30 minutes per ticket
