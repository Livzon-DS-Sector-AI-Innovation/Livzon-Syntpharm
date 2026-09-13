# 55 — Remove unused vars in registration components

**What to build:** Remove all unused imports and variables from `src/components/registration/` directory. This includes 35 unused variables across multiple registration-related component files.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All unused imports removed from registration components
- [x] All unused variables removed from registration components
- [x] `tsc --noEmit` passes with no errors
- [x] `pnpm lint` shows zero `@typescript-eslint/no-unused-vars` warnings in registration components
- [x] No functional changes to registration features

## Changes Made

### AiFillPanel.tsx
- Removed unused import: `EditOutlined`
- Removed unused import: `AssetCategory`
- Renamed unused parameter: `assets` → `assets: _assets`
- Renamed unused variable: `refetchSelectedAssets` → `_refetchSelectedAssets`

### DossierWriterDetailPageClient.tsx
- Removed unused import: `Descriptions`
- Removed unused import: `ReloadOutlined`
- Removed unused import: `getChapterPreview`
- Removed unused import: `ChapterPreview`
- Renamed unused variable: `currentDossierLoading` → `currentDossierLoading: _currentDossierLoading`

### ValidationAuditListClient.tsx
- Removed unused imports: `Modal`, `Input`
- Removed unused import: `ExportOutlined`

## Verification
- All unused vars warnings resolved in registration components
- TypeScript compilation passes with no errors
- No functional changes made
