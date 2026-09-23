# 57 — Remove unused vars in hr components

**What to build:** Remove all unused imports and variables from `src/components/hr/` directory. This includes 14 unused variables across multiple HR-related component files.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All unused imports removed from hr components
- [x] All unused variables removed from hr components
- [x] `tsc --noEmit` passes with no errors
- [x] `pnpm lint` shows zero `@typescript-eslint/no-unused-vars` warnings in hr components
- [x] No functional changes to hr features

## Changes Made

### CandidateDetailClient.tsx
- Line 38: Renamed unused setter `setNavContext` to `_setNavContext`

### EmployeeProfileClient.tsx
- Line 68: Renamed unused variable `loading` to `_loading`

### OnboardingPrejobClient.tsx
- Lines 19, 21: Removed unused imports `fetchPrejobTrainingPlan` and `fetchOnboardingRecords`
- Line 25: Renamed unused constant `DEPT_CONTENT_MAP` to `_DEPT_CONTENT_MAP`
- Line 290: Renamed unused variable `visibleIds` to `_visibleIds`

### TrainingNotificationClient.tsx
- Line 379: Renamed unused variable `traineeDepts` to `_traineeDepts`
- Line 426: Renamed unused parameter `value` to `_value`
- Line 568: Renamed unused function `EvaluationPreview` to `_EvaluationPreview` and parameter `props` to `_props`

### TrainingSessionDetailModal.tsx
- Line 18: Removed unused imports `EditOutlined` and `CloseOutlined`

### TrainingSpecialistsClient.tsx
- Line 3: Removed unused import `useCallback`
- Line 4: Removed unused import `Tag`

## Verification
- All unused vars warnings resolved in hr components
- TypeScript compilation passes with no errors
- No functional changes made
