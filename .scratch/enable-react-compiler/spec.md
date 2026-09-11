# Eliminate setState-in-Effect Warnings

## Problem Statement

The frontend codebase has 41 ESLint warnings for `react-hooks/set-state-in-effect`. These warnings indicate that components are calling `setState` synchronously within `useEffect` bodies, which violates React's rules of hooks and prevents React Compiler from optimizing the code.

This is the last major category of lint warnings preventing us from:
1. Enabling React Compiler for automatic performance optimization
2. Setting the `set-state-in-effect` rule to "error" to prevent regression
3. Achieving zero lint warnings across the entire codebase

The warnings are concentrated in data fetching patterns, form initialization logic, and derived state calculations across the safety, quality, research, production, HR, and registration modules.

## Solution

Migrate all problematic patterns to canonical React patterns that are compatible with React Compiler:

1. **Data fetching**: Replace `useEffect` + `setState` with React Query (`useQuery`/`useMutation`)
2. **Derived state**: Replace `useEffect` that computes values with `useMemo`
3. **Form initialization**: Replace `useEffect` that syncs form state with controlled components or `useMemo`
4. **Content parsing**: Replace `useEffect` that parses and sets multiple state values with `useMemo` returning a single state object
5. **Event handlers**: Restructure handlers that trigger cascading state updates

This approach aligns with React's recommended patterns and enables React Compiler to automatically optimize component rendering.

## User Stories

1. As a developer, I want zero `set-state-in-effect` warnings so that the codebase follows React best practices
2. As a developer, I want to enable React Compiler so that components are automatically optimized without manual memoization
3. As a developer, I want data fetching to use React Query so that I get automatic caching, deduplication, and background refetching
4. As a developer, I want derived state to use `useMemo` so that expensive calculations are only recomputed when dependencies change
5. As a developer, I want form initialization to be declarative so that form state is always in sync with props
6. As a developer, I want to set the `set-state-in-effect` rule to "error" so that CI prevents future violations
7. As a user, I want faster page loads so that React Compiler can eliminate unnecessary re-renders
8. As a developer, I want consistent data fetching patterns across the codebase so that the code is easier to understand and maintain
9. As a developer, I want fewer manual memoization decisions so that I can focus on business logic
10. As a developer, I want the lint check to pass with zero warnings so that CI is green and I can merge with confidence

## Implementation Decisions

### Decision 1: Use React Query for all data fetching

**Rationale**: React Query is already set up globally in the application (ticket 35). It provides automatic caching, background refetching, and proper loading/error states. This eliminates the need for manual `useEffect` + `setState` patterns.

**Approach**: 
- Replace `useState` + `useEffect` + `loadData` with `useQuery`
- Use `useMutation` for create/update/delete operations with `queryClient.invalidateQueries` to refetch
- Keep toast notifications in a separate `useEffect` that watches the `error` state from React Query

### Decision 2: Use useMemo for derived state

**Rationale**: `useMemo` computes values during render, not in an effect. This is the canonical React pattern for derived state and is compatible with React Compiler.

**Approach**:
- Replace `useEffect` that computes filtered/sorted/transformed data with `useMemo`
- Dependencies are the same as the effect dependencies
- No need for separate state variables

### Decision 3: Use controlled components or useMemo for form initialization

**Rationale**: `useEffect` that syncs form state with props creates a cascading render pattern. Controlled components or `useMemo` are cleaner.

**Approach**:
- For simple cases: use controlled components with `value` and `onChange`
- For complex cases: use `useMemo` to compute initial form values from props
- Use `key` prop to force remount when props change (if needed)

### Decision 4: Use useMemo for content parsing

**Rationale**: Parsing content (e.g., markdown, SOP documents) and setting multiple state values in an effect creates cascading renders. `useMemo` can parse once and return a single state object.

**Approach**:
- Parse content in `useMemo` and return an object with all parsed values
- Destructure the object in the component
- If user edits are needed, initialize state from the parsed values

### Decision 5: Restructure event handlers to avoid cascading updates

**Rationale**: Some event handlers call `setState` multiple times or trigger effects that call `setState`. This creates cascading renders.

**Approach**:
- Batch state updates using a single state object
- Move state updates out of effects and into the handler itself
- Use `useCallback` to stabilize handler references if they're used as effect dependencies

## Testing Decisions

### What makes a good test

- **Type checking**: Run `tsc --noEmit` after each change to catch type errors
- **Lint checking**: Run `pnpm lint` after each change to verify warnings are eliminated
- **Manual smoke testing**: Test each affected page to confirm no behavioral regression
- **React Query verification**: Confirm that data loads, caches, and refetches correctly

### Which modules will be tested

- Safety module (15 warnings)
- Quality module (6 warnings)
- Research module (2 warnings)
- Production module (4 warnings)
- HR module (2 warnings)
- Registration module (1 warning)

### Prior art

- Tickets 36-42 already migrated many modules to React Query
- Ticket 35 set up global React Query provider
- Tickets 45-46 fixed `exhaustive-deps` warnings by adding proper dependencies
- The codebase already has 121 files using `useQuery`/`useMutation`

## Out of Scope

- **Backend changes**: This spec only covers frontend patterns
- **New features**: No new functionality, only pattern improvements
- **Performance metrics**: React Compiler is enabled for code quality, not performance targets
- **E2E test automation**: Can't run locally, so manual testing is the validation method
- **Other lint rules**: This spec focuses only on `set-state-in-effect`

## Further Notes

### React Compiler implications

Enabling React Compiler requires strict adherence to React's rules:
- No direct state mutations (hence `immutability` rule)
- Pure render functions (hence `purity` rule)
- No `setState` in effects unless necessary (hence `set-state-in-effect` rule)

This spec eliminates the `set-state-in-effect` violations, which is the last major blocker for enabling React Compiler.

### Current state

- 41 `set-state-in-effect` warnings remaining
- React Query already set up globally
- 121 files already using React Query (prior art from tickets 36-42)
- `react-hooks/set-state-in-effect` currently set to "warn"

### Success criteria

- Zero `set-state-in-effect` warnings
- `react-hooks/set-state-in-effect` rule set to "error"
- React Compiler enabled (`reactCompiler: true` in `next.config.ts`)
- Type checking passes (`tsc --noEmit`)
- Lint checking passes (`pnpm lint`)
- Manual smoke test confirms no behavioral regression

### Risk mitigation

- React Query migration is well-established (tickets 36-42)
- Each commit is independently green
- Manual smoke testing after each module
- Easy to rollback if issues arise

### Dependencies

- Tickets 60-67 must be complete (all other lint fixes)
- React Query must be set up globally (already done in ticket 35)
