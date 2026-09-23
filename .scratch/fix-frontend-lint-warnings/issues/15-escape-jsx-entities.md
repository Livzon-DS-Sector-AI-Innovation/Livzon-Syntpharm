# 15 — Escape JSX entities (react/no-unescaped-entities)

**What to build:** Escape special characters in JSX text (quotes, apostrophes, etc.) to prevent rendering issues.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All special characters in JSX properly escaped
- [x] Text renders correctly
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no react/no-unescaped-entities warnings)

## Summary

Fixed 22 react/no-unescaped-entities warnings across 8 files by replacing unescaped quotes with &quot; entities:
- hplc-reference/page.tsx: escaped quotes around '需复标'
- AlertRecordTable.tsx: escaped quotes around '导入数据'
- ProjectListPage.tsx: escaped quotes around project name
- ProjectTable.tsx: escaped quotes around record name
- ModuleDOE.tsx: escaped quotes around 'AI生成CPP评估'
- HazardAIResultPanel.tsx: escaped quotes around '修改'
- HazardSelectModal.tsx: escaped quotes around risk level names
- WorkflowEditDrawer.tsx: escaped quotes in output format examples

All JSX entities are now properly escaped for safe rendering.
