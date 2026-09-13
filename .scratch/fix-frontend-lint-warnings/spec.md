# Fix Frontend Lint Warnings

## Problem Statement

The frontend has 3011 ESLint warnings across 463 files (out of 907 total). These warnings are currently set to "warn" level, so CI passes, but the code quality is degraded. The warnings span multiple categories:

- **Type safety**: 1655 `@typescript-eslint/no-explicit-any` warnings (55%)
- **Dead code**: 895 `@typescript-eslint/no-unused-vars` warnings (30%)
- **React hooks best practices**: 422 warnings across `set-state-in-effect` (222), `exhaustive-deps` (173), `immutability` (27)
- **Minor issues**: 39 warnings across `jsx-a11y/alt-text`, `no-img-element`, `no-location-assign`, `jsx-key`, `no-unescaped-entities`, `no-unused-expressions`

The team wants to eliminate all warnings, prevent regression, and enable React Compiler for automatic performance optimization.

## Solution

Systematically fix all 3011 warnings in a phased approach (51 commits), then flip ESLint rules from "warn" to "error" to prevent regression. Enable React Compiler for automatic performance optimization. No pre-commit hooks — rely on CI to enforce quality at the PR level.

## User Stories

1. As a developer, I want zero ESLint warnings, so that the codebase is clean and maintainable
2. As a developer, I want type-safe API clients, so that I catch type errors at compile time instead of runtime
3. As a developer, I want React Compiler enabled, so that components are automatically optimized without manual memoization
4. As a developer, I want ESLint rules set to "error", so that CI fails on lint violations and prevents bad code from merging
5. As a developer, I want unused imports removed, so that the code is cleaner and easier to understand
6. As a developer, I want proper types instead of `any`, so that I get autocomplete and type checking
7. As a developer, I want React Query for data fetching, so that I don't have to manually manage loading/error state
8. As a developer, I want derived state computed during render, so that it's always in sync with dependencies
9. As a developer, I want immutable state updates, so that React can detect changes correctly
10. As a developer, I want complete dependency arrays in useEffect, so that effects don't have stale closures
11. As a developer, I want granular commits, so that each change is reviewable and bisectable
12. As a developer, I want each commit to be independently green, so that CI passes at every step
13. As a developer, I want type checking after each commit, so that type errors are caught early
14. As a developer, I want lint checking after each commit, so that lint violations are caught early
15. As a developer, I want manual smoke testing after behavioral changes, so that I confirm no regression

## Implementation Decisions

### Phase 1: Remove unused vars (895 warnings, ~10 commits)

- Delete all unused imports and variables
- No behavioral change, zero risk
- One commit per directory/module
- Directories: `src/app/(dashboard)/administration/`, `src/app/(dashboard)/equipment/`, `src/app/(dashboard)/energy/`, `src/app/(dashboard)/hr/`, `src/app/(dashboard)/safety/`, `src/app/(dashboard)/remaining modules/`, `src/components/`, `src/lib/api/`, `src/actions/`, remaining directories

### Phase 2: Mechanical fixes (39 warnings, ~6 commits)

- Add alt text to images (`jsx-a11y/alt-text`)
- Replace `<img>` with `next/image` (`@next/next/no-img-element`)
- Use `router.push` instead of `window.location` (`@next/next/no-location-assign`)
- Add keys to list elements (`react/jsx-key`)
- Escape JSX entities (`react/no-unescaped-entities`)
- Remove unused expressions (`@typescript-eslint/no-unused-expressions`)

### Phase 3: Type API clients (584 warnings, ~10 commits)

- Replace `any` with proper types in `src/lib/api/client/` and `src/lib/api/server/`
- Use existing types from `@/types/...` (hand-written per-module types)
- Fall back to generated types from `@/types/generated/schema.ts` (OpenAPI-derived, 76K lines)
- Use `unknown` instead of `any` only when no type exists
- One commit per API client file
- Files: energy, equipment, hr, quality, registration, research, static-data, safety, remaining client files, server files

### Phase 4: Type components and actions (1071 warnings, ~8 commits)

- Replace `any` with proper types in `src/app/(dashboard)/`, `src/components/`, `src/actions/`
- Define interfaces where they don't exist
- Use generated types where available
- One commit per module
- Modules: dashboard pages (administration, equipment, energy), dashboard pages (hr, safety, remaining), safety components, equipment components, research components, hr components, remaining components, actions

### Phase 5: React Compiler migration (422 warnings, ~13 commits)

**Prep step**: Add global `QueryClientProvider` at app level (currently only exists for equipment/personnel module in `src/components/equipment/personnel/PersonnelQueryProvider.tsx`)

**Migrate data fetching to React Query**: Convert ~200 `useEffect` + `setState` patterns to `useQuery`/`useMutation`
- One commit per module
- Modules: administration, equipment, energy, hr, safety, research, remaining

**Refactor derived state**: Convert sync `useEffect` + `setState` to `useMemo`

**Fix immutability**: Fix 27 direct state mutations

**Fix exhaustive-deps**: Add missing deps, stabilize with `useCallback`

**Enable React Compiler**: Set `reactCompiler: true` in `next.config.ts`

### Phase 5.5: Documentation (1 commit)

- `chore: add React Hooks rules to AGENTS.md` — educate developers on React Compiler patterns (React Query for data fetching, useMemo for derived state, complete dependency arrays, immutable state updates) so they write correct code from the start


### Phase 6: Lock it down (2 commits)

- Flip all ESLint rules from "warn" to "error"
- Update CI to fail on lint errors

### Validation

- After each commit: `tsc --noEmit` + `pnpm lint` must pass
- After Phase 5: Manual smoke test of affected pages (safety, equipment, hr, research, production, energy, administration)

### Architecture Decisions

- **No pre-commit hooks**: Commit = save, PR = gate. Rely on CI to enforce quality.
- **React Compiler enabled**: Automatic performance optimization, requires strict React patterns (no direct mutations, no setState in effects, pure renders)
- **React Query for data fetching**: Replace manual `useEffect` + `setState` with `useQuery`/`useMutation`
- **Granular commits**: 51 commits, each independently green, for easy review and bisection
- **Type safety strategy**: Use existing hand-written types first, fall back to generated OpenAPI types, use `unknown` only when no type exists
- **React Compiler migration strategy**: Migrate data fetching to React Query (compiler-friendly pattern), refactor derived state to `useMemo`, fix all immutability violations

## Testing Decisions

### What makes a good test

- Tests should verify external behavior, not implementation details
- Type checking catches compile-time errors
- Lint checking catches code quality issues
- Manual smoke testing catches runtime behavioral issues

### Modules to test

- All modules affected by Phase 5: administration, equipment, energy, hr, safety, research, production

### Prior art

- Existing Playwright E2E tests (but can't run locally due to resource constraints)
- Existing type checking (`pnpm typecheck`)
- Existing lint checking (`pnpm lint`)

### Testing approach

- **Type checking**: Run `tsc --noEmit` after each commit to catch type errors
- **Lint checking**: Run `pnpm lint` after each commit to catch lint violations
- **Manual smoke test**: After Phase 5, manually test affected pages to confirm no behavioral regression
- **CI validation**: After Phase 6, CI will fail on any lint error, preventing merge

## Out of Scope

- **Backend changes**: This spec only covers frontend lint warnings
- **Performance optimization**: React Compiler is enabled for code quality, not performance metrics
- **New features**: No new functionality, only code quality improvements
- **Pre-commit hooks**: Explicitly excluded per user preference (commit = save, PR = gate)
- **E2E test automation**: Can't run locally, so manual testing is the validation method
- **React Query migration for all data fetching**: Only migrate the patterns that trigger `set-state-in-effect` warnings

## Further Notes

### React Query setup

Currently only configured for equipment/personnel module (`src/components/equipment/personnel/PersonnelQueryProvider.tsx`). Phase 5 prep adds a global `QueryClientProvider` at the app level (in `src/app/layout.tsx` or a new `src/app/providers.tsx`).

### Generated types

76K lines of OpenAPI-derived types exist in `src/types/generated/schema.ts` but are underutilized. Phase 3-4 wires these in. The types are generated from the backend OpenAPI spec via `pnpm generate:api`.

### Commit granularity

51 commits, each independently green. This allows easy review, bisection, and rollback if needed. Each commit is small enough to be reviewable but large enough to be meaningful.

### Risk mitigation

- Phases 1-4 are low-risk (deletion, mechanical fixes, typing)
- Phase 5 is higher-risk (behavioral changes from React Query migration)
- Phase 6 locks down the quality gate

### React Compiler implications

Enabling the compiler requires strict adherence to React rules:
- No direct state mutations (hence `immutability` rule)
- Pure render functions (hence `purity` rule)
- No `setState` in effects unless necessary (hence `set-state-in-effect` rule)

This is why Phase 5 migrates to React Query (compiler-friendly data fetching pattern) and refactors derived state to `useMemo`.

### Current state

- `reactCompiler: false` in `next.config.ts`
- `babel-plugin-react-compiler` installed but not configured
- 30 uses of `useQuery`/`useMutation` (only in equipment/personnel)
- 0 uses of `useEffect` + `setState` pattern that don't trigger warnings (all are flagged)

### Files affected

- 907 files scanned
- 463 files have warnings
- 0 errors (all warnings)
- Hotspots:
  - `src/lib/api/client/`: 661 warnings (584 `any` + 77 unused-vars)
  - `src/app/(dashboard)/`: ~540 warnings (418 unused-vars + 75 set-state-in-effect + 48 exhaustive-deps)
  - `src/components/safety/`: ~200 warnings
  - `src/components/equipment/`: ~150 warnings
  - `src/components/research/`: ~150 warnings

### ESLint configuration

Current rules in `eslint.config.mjs`:
- `@typescript-eslint/no-explicit-any`: "warn" → will become "error"
- `@typescript-eslint/no-unused-vars`: "warn" → will become "error"
- `react-hooks/set-state-in-effect`: "warn" → will become "error"
- `react-hooks/exhaustive-deps`: "warn" → will become "error"
- `react-hooks/immutability`: "warn" → will become "error"
- `react/no-unescaped-entities`: "warn" → will become "error"
- `react/jsx-key`: "warn" → will become "error"
- `jsx-a11y/alt-text`: "warn" → will become "error"
- `@next/next/no-location-assign-relative-destination`: "warn" → will become "error"
- `@next/next/no-img-element`: "warn" → will become "error"
- `@typescript-eslint/no-unused-expressions`: "warn" → will become "error"
- `react-hooks/react-compiler`: "off" (stays off)
- `react-hooks/static-components`: "warn" → will become "error"
- `react-hooks/purity`: "warn" → will become "error"

### Success criteria

- Zero ESLint warnings
- All ESLint rules set to "error"
- React Compiler enabled (`reactCompiler: true`)
- CI fails on any lint violation
- Type checking passes (`tsc --noEmit`)
- Manual smoke test confirms no behavioral regression
