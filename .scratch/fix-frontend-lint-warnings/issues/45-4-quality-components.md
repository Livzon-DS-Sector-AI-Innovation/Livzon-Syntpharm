# 45.4 — Fix exhaustive-deps in Quality module (Part 2)

**What to build:** Fix all React hooks dependency warnings in the Quality module components so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] AttachmentPreview.tsx has no exhaustive-deps warnings
- [x] CppBatchDataClient.tsx has no exhaustive-deps warnings
- [x] CqaBatchDataClient.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for these files
