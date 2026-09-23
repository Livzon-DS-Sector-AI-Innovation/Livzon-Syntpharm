# 11 — Add alt text to images (jsx-a11y/alt-text)

**What to build:** Add meaningful alt text to all images for accessibility compliance.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All images have descriptive alt text
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no jsx-a11y/alt-text warnings)

## Summary

Fixed 5 jsx-a11y/alt-text warnings across 2 files:
- material-report/[id]/page.tsx: added alt="报告图片" and alt="预览图片"
- reagent/page.tsx: added alt="试剂图片", alt="试剂标签", alt="试剂标签预览"

All images now have proper alt text for accessibility.
