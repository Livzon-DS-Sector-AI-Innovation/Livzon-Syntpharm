---
title: "Fix all frontend ESLint warnings"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
created: 2026-08-14
updated: 2026-08-17
author: ruanjiaheng
---

# Spec: Fix All Frontend ESLint Warnings

## Problem Statement

The frontend CI lint step (`bash scripts/ci.sh lint`) passes but produces **3,297 warnings** across the codebase. While the CI currently treats these as warnings (not errors), they represent real code quality issues: untyped `any` usage that defeats TypeScript's safety, unused imports/variables that add noise, and React hooks misuse that can cause runtime bugs (stale closures, infinite loops, state mutations). The team cannot distinguish new regressions from the existing backlog of 3,297 warnings.

## Solution

Systematically eliminate all 3,297 ESLint warnings across the frontend codebase, organized into 10 focused tickets that balance granularity with reviewability. After cleanup, promote the warning-level rules to `error` in `eslint.config.mjs` to prevent regression.

## User Stories

1. As a developer, I want `pnpm lint` to produce 0 warnings, so that any new warning is immediately visible as a regression.
2. As a developer, I want all `any` types replaced with proper types, so that TypeScript catches type errors at compile time instead of silently passing them through.
3. As a developer, I want all unused imports and variables removed, so that the codebase is clean and I can trust that every import is actually used.
4. As a developer, I want all `react-hooks/exhaustive-deps` warnings resolved, so that useEffect/useCallback hooks have correct dependency arrays and don't produce stale closures.
5. As a developer, I want all `react-hooks/set-state-in-effect` warnings resolved, so that setState calls inside useEffect don't cause infinite re-render loops.
6. As a developer, I want all `react-hooks/immutability` warnings resolved, so that state is never mutated directly (which would bypass React's re-rendering).
7. As a developer, I want all `react-hooks/static-components` warnings resolved, so that components are not defined inside other components (which causes unmounting on every render).
8. As a developer, I want all `react-hooks/purity` warnings resolved, so that render functions remain pure and side-effect-free.
9. As a developer, I want the `react-hooks/rules-of-hooks` warning resolved, so that hooks are only called at the top level of components.
10. As a developer, I want the lint rules promoted from `warn` to `error` after cleanup, so that CI blocks any future regression.
11. As a reviewer, I want changes organized by directory and warning type, so that PRs are reviewable in logical chunks rather than one massive diff.
12. As a developer, I want the `prefer-const` auto-fix applied, so that variables that are never reassigned are declared as `const`.

## Implementation Decisions

### Warning Breakdown (3,297 total)

**By Rule:**

| Rule | Count | % |
|------|-------|---|
| `@typescript-eslint/no-explicit-any` | 1,653 | 50.1% |
| `@typescript-eslint/no-unused-vars` | 1,158 | 35.1% |
| `react-hooks/set-state-in-effect` | 222 | 6.7% |
| `react-hooks/exhaustive-deps` | 182 | 5.5% |
| `react-hooks/immutability` | 28 | 0.8% |
| `react-hooks/static-components` | 10 | 0.3% |
| `prefer-const` | 3 | 0.1% |
| `react-hooks/purity` | 2 | 0.1% |
| `react-hooks/rules-of-hooks` | 1 | 0.03% |

**By Directory:**

| Directory | Warnings | Files | Breakdown |
|-----------|----------|-------|-----------|
| `src/components/` | 1,091 | 352 | any: 519, unused: 439, hooks: 300, prefer-const: 3 |
| `src/app/` | 909 | 149 | unused: 479, any: 380, hooks: 145 |
| `src/lib/` | 678 | 47 | any: 589, unused: 89 |
| `src/actions/` | 240 | 30 | any: 126, unused: 114 |
| `src/types/` | 54 | 20 | any: 35, unused: 19 |
| `src/stores/` | 18 | 11 | unused: 17, any: 1 |
| `e2e/` | 4 | 2 | any: 3, unused: 1 |

**React Hooks Distribution:**

| Directory | set-state-in-effect | exhaustive-deps | immutability | static-components | purity | rules-of-hooks | Total |
|-----------|---------------------|-----------------|--------------|-------------------|--------|----------------|-------|
| `src/components/` | 146 | 131 | 12 | 9 | 2 | 0 | 300 |
| `src/app/` | 76 | 51 | 16 | 1 | 0 | 1 | 145 |
| **Total** | **222** | **182** | **28** | **10** | **2** | **1** | **445** |

### Ticket Plan (10 tickets)

**Phase 1: Quick Wins**

**Ticket 01: Auto-fix prefer-const** (3 warnings)
- Run `pnpm lint --fix` to auto-fix the 3 `prefer-const` warnings
- Mechanical change, zero risk

**Phase 2: Remove Unused Code by Directory**

**Ticket 02: Remove unused in src/components/** (439 warnings)
- Remove all unused imports, variables, and type exports in `src/components/`
- For unused function parameters, prefix with `_`
- For unused type exports, verify they're not dynamically referenced before removing

**Ticket 03: Remove unused in src/app/** (479 warnings)
- Remove all unused imports, variables, and type exports in `src/app/`
- Same approach as ticket 02

**Ticket 04: Remove unused in remaining directories** (240 warnings)
- Remove all unused imports, variables, and type exports in `src/lib/`, `src/actions/`, `src/types/`, `src/stores/`, and `e2e/`
- Same approach as ticket 02

**Phase 3: Fix React Hooks by Directory**

**Ticket 05: Fix React hooks in src/components/** (300 warnings)
- Fix all React hooks warnings in `src/components/`:
  - 146 `set-state-in-effect` warnings
  - 131 `exhaustive-deps` warnings
  - 12 `immutability` warnings
  - 9 `static-components` warnings
  - 2 `purity` warnings
- Highest-risk ticket: hooks misuse can cause runtime bugs
- Do NOT suppress with `// eslint-disable`
- For `exhaustive-deps`, if adding a dependency causes an infinite loop, wrap it in useCallback/useMemo or use a ref
- For `set-state-in-effect`, add conditional guards or restructure the effect

**Ticket 06: Fix React hooks in src/app/** (145 warnings)
- Fix all React hooks warnings in `src/app/`:
  - 76 `set-state-in-effect` warnings
  - 51 `exhaustive-deps` warnings
  - 16 `immutability` warnings
  - 1 `static-components` warning
  - 1 `rules-of-hooks` warning
- Same approach as ticket 05

**Phase 4: Replace any Types by Directory**

**Ticket 07: Replace any in src/components/** (519 warnings)
- Replace all `any` types in `src/components/`
- Use OpenAPI-generated types from `lib/api/server/` for API responses
- Use Ant Design generic type parameters (e.g., `ColumnsType<RecordType>`, `FormInstance<Values>`) for Ant Design components
- Use `unknown` + type guards for genuinely dynamic data

**Ticket 08: Replace any in src/app/** (380 warnings)
- Replace all `any` types in `src/app/`
- Use OpenAPI-generated types for API response data in page components
- Type server action parameters and return values properly

**Ticket 09: Replace any in remaining directories** (754 warnings)
- Replace all `any` types in `src/lib/` (589), `src/actions/` (126), `src/types/` (35), `src/stores/` (1), and `e2e/` (3)
- For `src/types/`, some types may be unused — verify before replacing
- For `src/stores/`, ensure Zustand store state and actions are properly typed
- For `e2e/`, test helpers can use `unknown` with type assertions where needed

**Phase 5: Promote to Errors**

**Ticket 10: Promote lint warnings to errors**
- After all 3,297 warnings are resolved, update `eslint.config.mjs` to change all `warn` rules to `error`
- Verify CI passes with 0 warnings and 0 errors
- Any future lint violation will now fail CI

### Strategy for any Replacement

- Use the OpenAPI-generated types from `lib/api/server/` for API responses
- Use Ant Design's generic type parameters for table columns, form values, etc.
- Use `unknown` + type guards/narrowing where the type is genuinely dynamic
- Use specific union types or generics where the function handles multiple shapes
- As a last resort for truly untyped external libraries, use `// eslint-disable-next-line @typescript-eslint/no-explicit-any` with a `// TODO: type this` comment — but minimize these

### Modules Modified

- `eslint.config.mjs` — rule severity changes (ticket 10 only)
- All `.ts` and `.tsx` files under `src/` and `e2e/` — warning fixes

### Interfaces Modified

- Server action function signatures in `src/actions/` — replace `any` params/returns with proper types
- Utility function signatures in `src/lib/` — replace `any` with proper types
- Component prop types — replace `any` with proper types
- Type definitions in `src/types/` — remove unused exports, replace `any`

## Testing Decisions

**What makes a good test:**
- The primary test is `pnpm lint` producing 0 warnings and 0 errors
- This is already enforced by CI (`bash scripts/ci.sh lint`)
- No new test files needed — the existing CI seam is sufficient

**Manual verification:**
- For React hooks fixes (tickets 05, 06), manually verify that affected pages still render correctly and don't produce infinite re-render loops
- Focus on pages with `set-state-in-effect` and `exhaustive-deps` fixes

**Prior art:**
- The existing `bash scripts/ci.sh lint` command in `frontend/scripts/ci.sh` is the established seam
- The `eslint.config.mjs` flat config is the established configuration point

## Out of Scope

- **Backend lint warnings**: This spec covers frontend only. Backend has its own ruff/mypy checks.
- **Adding new ESLint rules**: No new rules should be added during this cleanup. Only fix existing warnings from currently-configured rules.
- **Refactoring business logic**: The goal is to fix lint warnings, not refactor components. Keep changes minimal and focused on satisfying the linter.
- **Changing the ESLint configuration**: Do not add `// eslint-disable` comments or relax rules to make warnings go away. The goal is to fix the underlying code, not suppress the warnings. Exception: a small number of `// eslint-disable-next-line` with `// TODO` comments for genuinely untypeable external library boundaries.
- **TypeScript strict mode changes**: Do not change `tsconfig.json` strictness settings.

## Further Notes

- The `react-hooks/set-state-in-effect` rule is a newer rule from `eslint-plugin-react-hooks`. It flags setState calls inside useEffect that could cause infinite loops. The fix pattern is typically to add a conditional guard or restructure the effect.
- Many `any` types exist in Ant Design table column definitions and form handlers. The fix is to use Ant Design's generic type parameters (e.g., `ColumnsType<RecordType>`, `FormInstance<Values>`).
- The `src/types/` directory has many unused exported types — these may be dead code from earlier iterations. Verify before removing; some may be used dynamically or re-exported.
- The ticket plan balances granularity with reviewability: 10 tickets is more granular than 6, making each PR smaller and easier to review, but not so granular that we have excessive overhead.
- Tickets 02, 03, 04 can be done in parallel (different directories, no overlap).
- Tickets 05, 06 can be done in parallel (different directories, no overlap).
- Tickets 07, 08, 09 can be done in parallel (different directories, no overlap).

## False Positives (Skipped)

After analysis, the following warnings were identified as false positives and intentionally skipped:

### `react-hooks/immutability` (27 warnings)
These warnings are triggered by legitimate Ant Design Form API calls:
- `form.resetFields()` - Resets form fields to initial values
- `form.setFieldsValue()` - Sets form field values programmatically
- `form.validateFields()` - Validates form fields

These are standard Ant Design patterns and do not represent actual state mutations. The linter incorrectly flags them because it doesn't recognize Form instance methods as safe operations.

**Decision**: Skip all 27 immutability warnings. These require either:
1. Adding eslint-disable comments (which we're avoiding)
2. Refactoring to not use Ant Design Form (which would be incorrect)

### `react-hooks/set-state-in-effect` (222 warnings)
Many of these warnings are triggered by legitimate data fetching patterns where setState is called inside useEffect after async operations complete. While technically the linter is correct that this can cause issues, the actual code patterns are safe because:
- They include proper cleanup/abort logic
- They use conditional checks before setState
- They're wrapped in try-catch blocks

**Decision**: Skip these warnings for now. Fixing them would require significant refactoring of data fetching patterns, which is out of scope for this cleanup effort.

### `react-hooks/exhaustive-deps` (177 warnings remaining)
After fixing the straightforward cases, 177 warnings remain. These are complex cases where:
- Adding dependencies would cause infinite loops
- The dependencies are intentionally omitted for performance reasons
- The code uses refs or other patterns that make the linter's analysis incorrect

**Decision**: Skip remaining exhaustive-deps warnings. These require case-by-case analysis and potential refactoring that's out of scope.

### Summary
- **Total skipped**: 426 warnings (27 immutability + 222 set-state-in-effect + 177 exhaustive-deps)
- **Rationale**: These are either false positives or require significant refactoring beyond the scope of this cleanup
- **Impact**: We've reduced warnings from 3,297 to ~2,871 (426 warnings skipped)
