# 14 — Add keys to list elements (react/jsx-key)

**What to build:** Add proper React keys to all list elements for efficient rendering.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All list elements have unique keys
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no react/jsx-key warnings)

## Summary

Fixed 2 react/jsx-key warnings across 2 files:
- production/product-output/[workshop]/page.tsx: added key='delete' to delete button in Card actions array
- quality/AttachmentPreview.tsx: added key='delete' to delete review button in List.Item actions array

All list elements now have proper keys for efficient React rendering.
