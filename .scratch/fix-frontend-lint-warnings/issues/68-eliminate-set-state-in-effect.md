# 68 — Eliminate `react-hooks/set-state-in-effect` warnings

**What to build:** Eliminate all 41 remaining `react-hooks/set-state-in-effect` warnings by applying canonical React patterns. This is the final step to enable React Compiler and flip the rule to "error".

**Blocked by:** Tickets 60-67 (all other lint fixes complete)

**Status:** ready-for-agent

## Problem Statement

After completing tickets 60-67, the codebase has 41 remaining `react-hooks/set-state-in-effect` warnings. These warnings indicate that `setState` is being called synchronously within `useEffect` bodies, which can cause cascading renders and prevent React Compiler from optimizing the code.

The warnings span 25 files across multiple modules:
- Safety module: 15 warnings (HazardDetailPageClient, SafetyRegulationPageClient, HazardLedgerPanel, etc.)
- Quality module: 6 warnings (CppBatchDataClient, CqaBatchDataClient, deviation pages, etc.)
- Research module: 2 warnings (StageModuleLayout, DeliverableTemplatePage)
- Production module: 4 warnings (AnnualReviewTab, WorkshopRankingTrend, PressureManualInputPageClient, product-output page)
- HR module: 2 warnings (TrainingSelectClient, TrainingSessionDetailModal)
- Registration module: 1 warning (AiFillPanel)
- Components: 11 warnings (various shared components)

## Solution

Apply canonical React patterns to eliminate all 41 warnings:

1. **Data fetching → React Query**: Migrate `useEffect` + `setState` data fetching patterns to `useQuery`/`useMutation`
2. **Derived state → useMemo**: Replace `useEffect` that computes derived state with `useMemo`
3. **Form initialization → useMemo or controlled components**: Replace `useEffect` that syncs form state with `useMemo` or lift state
4. **Content parsing → useMemo**: Replace `useEffect` that parses content and sets multiple state values with `useMemo` returning a single state object
5. **Event handlers → Restructure**: Some event handlers are flagged because they call setState in a way that looks like an effect; restructure to avoid the pattern

## User Stories

1. As a developer, I want zero `set-state-in-effect` warnings, so that React Compiler can optimize the code
2. As a developer, I want data fetching to use React Query, so that I get automatic caching, deduplication, and refetching
3. As a developer, I want derived state to use `useMemo`, so that it's computed during render instead of in effects
4. As a developer, I want form initialization to be declarative, so that form state is always in sync with props
5. As a developer, I want content parsing to be memoized, so that expensive parsing doesn't run on every render
6. As a developer, I want the `set-state-in-effect` rule set to "error", so that CI prevents future violations
7. As a developer, I want React Compiler enabled, so that components are automatically optimized
8. As a user, I want faster page loads, so that React Compiler can eliminate unnecessary re-renders
9. As a developer, I want consistent data fetching patterns, so that the codebase is easier to understand
10. As a developer, I want fewer manual memoization decisions, so that I can focus on business logic

## Implementation Decisions

### Pattern 1: Data fetching → React Query

**Current pattern (problematic):**
```typescript
const [data, setData] = useState([])
const [loading, setLoading] = useState(false)

const loadData = useCallback(async () => {
  setLoading(true)
  try {
    const response = await fetchData(params)
    setData(response.data)
  } catch (err) {
    message.error('Failed to load')
  } finally {
    setLoading(false)
  }
}, [params])

useEffect(() => { loadData() }, [loadData])
```

**Canonical pattern:**
```typescript
const { data = [], isLoading, error } = useQuery({
  queryKey: ['data', params],
  queryFn: () => fetchData(params),
})

// Show error message in JSX or use useEffect to show toast
useEffect(() => {
  if (error) message.error('Failed to load')
}, [error])
```

**Files to migrate:**
- `SafetyRegulationPageClient.tsx`: `loadRegulations`, `loadRevisions`, `loadRegulationsForSelect`
- `HazardLedgerPanel.tsx`: `fetchData`
- `SpecialOpsLedger.tsx`: `fetchStats`
- `SpecialOpsManagement.tsx`: `fetchStats`
- `CppBatchDataClient.tsx`: `loadData`
- `CqaBatchDataClient.tsx`: `loadData`
- `HazardDetailPageClient.tsx`: data fetching functions
- `HazardIdentificationDetailPageClient.tsx`: data fetching functions
- `WorkflowListPanel.tsx`: data fetching
- `StageModuleLayout.tsx`: `loadProjects`
- `TrainingSelectClient.tsx`: data fetching
- `product/[productName]/page.tsx`: data fetching

### Pattern 2: Derived state → useMemo

**Current pattern (problematic):**
```typescript
const [filteredData, setFilteredData] = useState([])

useEffect(() => {
  setFilteredData(data.filter(predicate))
}, [data, predicate])
```

**Canonical pattern:**
```typescript
const filteredData = useMemo(() => data.filter(predicate), [data, predicate])
```

**Files to migrate:**
- `StageModuleLayout.tsx`: `filteredProjects` (already using useMemo, but flagged for a different reason)
- `WorkshopRankingTrend.tsx`: `months` computation

### Pattern 3: Form initialization → useMemo or controlled components

**Current pattern (problematic):**
```typescript
useEffect(() => {
  if (editData) {
    form.setFieldsValue(editData)
    setSelectedSources(editData.data_sources || [])
    setCardTemplate(editData.card_template || '')
  } else {
    form.resetFields()
    setSelectedSources(defaults)
    setCardTemplate('')
  }
}, [editData])
```

**Canonical pattern:**
```typescript
const initialValues = useMemo(() => {
  if (editData) {
    return {
      ...editData,
      data_sources: editData.data_sources || [],
      card_template: editData.card_template || '',
    }
  }
  return {
    data_sources: defaults,
    card_template: '',
  }
}, [editData])

// Use initialValues in form with key={editData?.id} to force remount
```

**Files to migrate:**
- `ScheduledTaskForm.tsx`: form initialization from `editData`
- `HazardIdentificationBatchDrawer.tsx`: form initialization
- `HazardIdentificationDrawer.tsx`: form initialization

### Pattern 4: Content parsing → useMemo

**Current pattern (problematic):**
```typescript
useEffect(() => {
  const parsed = parseContent(initialContent)
  setHeaderMeta(parsed.meta)
  setSigTable(parsed.sig)
  setPreambleText(parsed.preamble)
  setChapters(parsed.chapters)
}, [initialContent])
```

**Canonical pattern:**
```typescript
const parsedContent = useMemo(() => {
  return parseContent(initialContent)
}, [initialContent])

// Use parsedContent.meta, parsedContent.sig, etc. in JSX
// Or if you need separate state for user edits, initialize state from parsedContent
const [headerMeta, setHeaderMeta] = useState(parsedContent.meta)
const [chapters, setChapters] = useState(parsedContent.chapters)
```

**Files to migrate:**
- `SopContentEditor.tsx`: content parsing and state initialization

### Pattern 5: Event handlers → Restructure

Some event handlers are flagged because they call setState in a way that looks like an effect. These need to be restructured to avoid the pattern.

**Files to migrate:**
- `CppBatchDataClient.tsx`: `handleSearch` calls `setPage(1)` then `loadData()`
- `CqaBatchDataClient.tsx`: same pattern
- `HazardSelectModal.tsx`: `handleSearch` pattern
- `KnowledgeBasePicker.tsx`: search handler
- `KnowledgeDetailDrawer.tsx`: version chain loading
- `StageSelector.tsx`: `handleCheckAll`
- `SopGeneratorModal.tsx`: generation handler
- `AiFillPanel.tsx`: fill results clearing
- `DeliverableTemplatePage.tsx`: template editing
- `HazardInspectionForm.tsx`: form submission
- `TrainingSessionDetailModal.tsx`: factory selection
- `AnnualReviewTab.tsx`: export handler
- `PressureManualInputPageClient.tsx`: add point handler
- `deviation-automation/preview/[id]/page.tsx`: data loading
- `deviation-automation/templates/page.tsx`: table change handler
- `deviation-flow/create/page.tsx`: form submission
- `deviation-flow/progress/page.tsx`: progress loading
- `instrument/list/edit/page.tsx`: form submission
- `static-data/[module]/[id]/page.tsx`: data loading

### React Query migration strategy

For each data fetching pattern:
1. Identify the query key (usually the params/dependencies)
2. Replace `useState` + `useEffect` + `loadData` with `useQuery`
3. Replace manual loading/error state with `isLoading`/`error` from `useQuery`
4. For mutations (create/update/delete), use `useMutation` with `queryClient.invalidateQueries`
5. Keep toast notifications in a separate `useEffect` that watches `error`

### Files to modify

**Safety module (15 warnings):**
- `src/components/safety/regulation/SafetyRegulationPageClient.tsx`
- `src/components/safety/HazardLedgerPanel.tsx`
- `src/components/safety/HazardLedgerPage.tsx`
- `src/components/safety/SpecialOpsLedger.tsx`
- `src/components/safety/SpecialOpsManagement.tsx`
- `src/components/safety/hazard/HazardDetailPageClient.tsx`
- `src/components/safety/hazard-identification/HazardIdentificationDetailPageClient.tsx`
- `src/components/safety/WorkflowListPanel.tsx`
- `src/components/safety/ScheduledTaskForm.tsx`
- `src/components/safety/HazardIdentificationBatchDrawer.tsx`
- `src/components/safety/HazardIdentificationDrawer.tsx`
- `src/components/safety/HazardSelectModal.tsx`
- `src/components/safety/KnowledgeBasePicker.tsx`
- `src/components/safety/KnowledgeDetailDrawer.tsx`
- `src/components/safety/StageSelector.tsx`
- `src/components/safety/SopContentEditor.tsx`
- `src/components/safety/SopGeneratorModal.tsx`

**Quality module (6 warnings):**
- `src/components/quality/CppBatchDataClient.tsx`
- `src/components/quality/CqaBatchDataClient.tsx`
- `src/app/(dashboard)/quality/deviation-automation/preview/[id]/page.tsx`
- `src/app/(dashboard)/quality/deviation-automation/templates/page.tsx`
- `src/app/(dashboard)/quality/deviation-flow/create/page.tsx`
- `src/app/(dashboard)/quality/deviation-flow/progress/page.tsx`
- `src/app/(dashboard)/quality/instrument/list/edit/page.tsx`
- `src/app/(dashboard)/quality/static-data/[module]/[id]/page.tsx`

**Research module (2 warnings):**
- `src/components/research/StageModuleLayout.tsx`
- `src/components/research/DeliverableTemplatePage.tsx`

**Production module (4 warnings):**
- `src/components/production/AnnualReviewTab.tsx`
- `src/components/production/WorkshopRankingTrend.tsx`
- `src/components/production/pressure/PressureManualInputPageClient.tsx`
- `src/app/(dashboard)/production/product-output/product/[productName]/page.tsx`

**HR module (2 warnings):**
- `src/components/hr/TrainingSelectClient.tsx`
- `src/components/hr/TrainingSessionDetailModal.tsx`

**Registration module (1 warning):**
- `src/components/registration/AiFillPanel.tsx`

### Testing approach

- Run `pnpm typecheck` after each file to catch type errors
- Run `pnpm lint` after each file to verify warning is gone
- Manual smoke test each affected page to confirm no behavioral regression
- Verify React Query caching works correctly (data persists across navigation)
- Verify error handling works (toast messages appear on failure)
- Verify loading states work (spinners appear during fetch)

### Commit strategy

- One commit per module (safety, quality, research, production, hr, registration)
- Each commit should be independently green (typecheck + lint pass)
- Final commit flips `set-state-in-effect` rule to "error"

## Testing Decisions

### What makes a good test

- Type checking catches compile-time errors
- Lint checking catches code quality issues
- Manual smoke testing catches runtime behavioral issues
- React Query tests should verify caching, refetching, and error handling

### Modules to test

- All modules with `set-state-in-effect` warnings: safety, quality, research, production, hr, registration

### Prior art

- Existing React Query migrations in tickets 36-42
- Existing Playwright E2E tests (but can't run locally)
- Existing type checking and lint checking

### Testing approach

- **Type checking**: Run `tsc --noEmit` after each commit
- **Lint checking**: Run `pnpm lint` after each commit
- **Manual smoke test**: Test each affected page to confirm no regression
- **React Query verification**: Check that data loads, caches, and refetches correctly

## Out of Scope

- **Backend changes**: This spec only covers frontend patterns
- **New features**: No new functionality, only pattern improvements
- **Performance metrics**: React Compiler is enabled for code quality, not performance targets
- **E2E test automation**: Can't run locally, so manual testing is the validation method
- **Other lint rules**: This spec focuses only on `set-state-in-effect`

## Further Notes

### React Compiler implications

Enabling React Compiler requires strict adherence to React rules:
- No direct state mutations (hence `immutability` rule)
- Pure render functions (hence `purity` rule)
- No `setState` in effects unless necessary (hence `set-state-in-effect` rule)

This spec eliminates the `set-state-in-effect` violations, which is the last major blocker for enabling React Compiler.

### Current state

- 41 `set-state-in-effect` warnings remaining
- React Query already set up globally in `src/components/Providers.tsx`
- 121 files already using `useQuery`/`useMutation` (prior art from tickets 36-42)
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

### Estimated effort

- 25 files to modify
- ~6 commits (one per module)
- ~2-3 days of work
- Manual smoke testing: ~1 day

### Dependencies

- Tickets 60-67 must be complete (all other lint fixes)
- React Query must be set up globally (already done in ticket 35)
