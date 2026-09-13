# 12 — Replace img with next/image (@next/next/no-img-element)

**What to build:** Replace all `<img>` elements with Next.js `<Image>` component for optimized image loading.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All `<img>` elements replaced with `<Image>`
- [x] Image dimensions (width/height) properly specified
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @next/next/no-img-element warnings)

## Summary

Fixed 5 @next/next/no-img-element warnings across 5 files:
- KnowledgeDetailDrawer.tsx: replaced img with Image, added width={500} height={500}
- HazardRectificationReplyModal.tsx: replaced img with NextImage (aliased), added width={80} height={80}
- InspectionExecuteView.tsx: replaced img with Image, added width={80} height={80}
- instrument/list/create/page.tsx: replaced img with Image, added width={400} height={200}
- instrument/list/page.tsx: replaced img with Image, added width={300} height={150}

All images now use Next.js Image component for optimized loading.
