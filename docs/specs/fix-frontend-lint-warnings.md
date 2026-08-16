---
title: "Fix all frontend ESLint warnings"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
  - code-quality
created: 2026-08-14
author: ruanjiaheng
---

# Spec: Fix All Frontend ESLint Warnings

## Problem Statement

The frontend CI lint step (`bash scripts/ci.sh lint`) passes but produces **3,279 warnings** across the codebase. While the CI currently treats these as warnings (not errors), they represent real code quality issues: untyped `any` usage that defeats TypeScript's safety, unused imports/variables that add noise, and React hooks misuse that can cause runtime bugs (stale closures, infinite loops, state mutations). The team cannot distinguish new regressions from the existing backlog of 3,279 warnings.

## Solution

Systematically eliminate all 3,279 ESLint warnings across the frontend codebase, organized by warning type and directory, so that `pnpm lint` produces **0 warnings**. After cleanup, promote the warning-level rules to `error` in `eslint.config.mjs` to prevent regression.

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
11. As a reviewer, I want changes organized by directory/module, so that PRs are reviewable in logical chunks rather than one massive diff.
12. As a developer, I want the `prefer-const` auto-fix applied, so that variables that are never reassigned are declared as `const`.

## Implementation Decisions

### Warning Breakdown (3,279 total)

| Rule | Count | Category |
|------|-------|----------|
| `@typescript-eslint/no-explicit-any` | 1,641 | Type safety |
| `@typescript-eslint/no-unused-vars` | 1,155 | Dead code |
| `react-hooks/set-state-in-effect` | 220 | Hooks correctness |
| `react-hooks/exhaustive-deps` | 182 | Hooks correctness |
| `react-hooks/immutability` | 28 | Hooks correctness |
| `react-hooks/static-components` | 9 | Hooks correctness |
| `react-hooks/purity` | 2 | Hooks correctness |
| `react-hooks/rules-of-hooks` | 1 | Hooks correctness |
| `prefer-const` | 3 | Auto-fixable |

### File Distribution

| Directory | Warning Count |
|-----------|---------------|
| `src/components/` | 470 |
| `src/app/` | 199 |
| `src/lib/` | 47 |
| `src/actions/` | 30 |
| `src/types/` | 20 |
| `src/stores/` | 11 |
| `e2e/` | 1 |

### Phase 1: Quick Wins (auto-fixable + unused cleanup)

- Run `pnpm lint --fix` to auto-fix the 3 `prefer-const` warnings and any other auto-fixable issues.
- Remove all unused imports, variables, and type exports (`@typescript-eslint/no-unused-vars`). For type files (`src/types/`), many exported types are unused — prefix with `_` or remove if truly dead code. For function parameters, prefix unused args with `_`.
- This eliminates ~1,155 warnings.

### Phase 2: React Hooks Correctness (442 warnings)

These are the highest-risk warnings because they can cause runtime bugs. Fix them before `any` cleanup.

- **`exhaustive-deps` (182)**: Add missing dependencies to useEffect/useCallback. Where adding a dependency would cause an infinite loop, wrap the dependency in `useCallback` or `useMemo`, or use a ref. Do NOT suppress with `// eslint-disable`.
- **`set-state-in-effect` (220)**: Refactor useEffect callbacks that call setState to avoid triggering re-render loops. Common patterns: move setState outside useEffect, use functional updates, or guard with conditionals.
- **`immutability` (28)**: Replace direct state mutations (e.g., `state.x = y`) with immutable updates (e.g., `setState({...state, x: y})`).
- **`static-components` (9)**: Extract components defined inside other components to module scope.
- **`purity` (2)**: Remove side effects from render functions.
- **`rules-of-hooks` (1)**: Move the hook call to the top level of the component.

### Phase 3: Type Safety — Replace `any` (1,641 warnings)

This is the largest phase. Organize by directory to keep PRs reviewable:

- **`src/components/`** (~470 warnings): Replace `any` in component props, event handlers, and API response types. Use the existing generated API types from `lib/api/` where available. For Ant Design component callbacks, use the library's provided type generics.
- **`src/app/`** (~199 warnings): Replace `any` in page components, server action parameters, and route handlers.
- **`src/lib/`** (~47 warnings): Replace `any` in utility functions and API helpers.
- **`src/actions/`** (~30 warnings): Replace `any` in server action return types and parameters.
- **`src/types/`** (~20 warnings): Replace `any` in type definitions.
- **`e2e/`** (~1 warning): Replace `any` in test helpers.

Strategy for `any` replacement:
- Use the OpenAPI-generated types from `lib/api/server/` for API responses.
- Use Ant Design's generic type parameters for table columns, form values, etc.
- Use `unknown` + type guards/narrowing where the type is genuinely dynamic.
- Use specific union types or generics where the function handles multiple shapes.
- As a last resort for truly untyped external libraries, use `// eslint-disable-next-line @typescript-eslint/no-explicit-any` with a `// TODO: type this` comment — but minimize these.

### Phase 4: Promote Warnings to Errors

After all 3,279 warnings are resolved:
- Update `eslint.config.mjs` to change all current `warn` rules to `error`.
- Verify CI passes with 0 warnings and 0 errors.

### Modules Modified

- `eslint.config.mjs` — rule severity changes (Phase 4 only)
- All `.ts` and `.tsx` files under `src/` and `e2e/` — warning fixes

### Interfaces Modified

- Server action function signatures in `src/actions/` — replace `any` params/returns with proper types
- Utility function signatures in `src/lib/` — replace `any` with proper types
- Component prop types — replace `any` with proper types
- Type definitions in `src/types/` — remove unused exports, replace `any`

## Testing Decisions

- **What makes a good test**: The primary test is `pnpm lint` producing 0 warnings and 0 errors. This is already enforced by CI (`bash scripts/ci.sh lint`).
- **No new test files needed**: The existing CI seam is sufficient. The lint command itself is the test.
- **Manual verification**: For React hooks fixes, manually verify that affected pages still render correctly and don't produce infinite re-render loops. Focus on pages with `set-state-in-effect` and `exhaustive-deps` fixes.
- **Prior art**: The existing `bash scripts/ci.sh lint` command in `frontend/scripts/ci.sh` is the established seam. The `eslint.config.mjs` flat config is the established configuration point.

## Out of Scope

- **Backend lint warnings**: This spec covers frontend only. Backend has its own ruff/mypy checks.
- **Adding new ESLint rules**: No new rules should be added during this cleanup. Only fix existing warnings from currently-configured rules.
- **Refactoring business logic**: The goal is to fix lint warnings, not refactor components. Keep changes minimal and focused on satisfying the linter.
- **Changing the ESLint configuration**: Do not add `// eslint-disable` comments or relax rules to make warnings go away. The goal is to fix the underlying code, not suppress the warnings. Exception: a small number of `// eslint-disable-next-line` with `// TODO` comments for genuinely untypeable external library boundaries.
- **TypeScript strict mode changes**: Do not change `tsconfig.json` strictness settings.

## Further Notes

- The full lint output (8,635 lines) is saved at `/tmp/frontend-lint-warnings.txt` for reference.
- The `react-hooks/set-state-in-effect` rule is a newer rule from `eslint-plugin-react-hooks`. It flags setState calls inside useEffect that could cause infinite loops. The fix pattern is typically to add a conditional guard or restructure the effect.
- Many `any` types exist in Ant Design table column definitions and form handlers. The fix is to use Ant Design's generic type parameters (e.g., `ColumnsType<RecordType>`, `FormInstance<Values>`).
- The `src/types/` directory has many unused exported types — these may be dead code from earlier iterations. Verify before removing; some may be used dynamically or re-exported.
- Consider running the cleanup in this order: Phase 1 → Phase 2 → Phase 3 (by directory) → Phase 4. Each phase should be a separate PR for reviewability.
