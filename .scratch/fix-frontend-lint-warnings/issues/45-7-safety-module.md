# 45.7 — Fix exhaustive-deps in Safety module

**What to build:** Fix all React hooks dependency warnings in the Safety module so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] AIWorkflowConfigClient.tsx has no exhaustive-deps warnings
- [x] KnowledgeBasePicker.tsx has no exhaustive-deps warnings
- [x] KnowledgeGraphPanel.tsx has no exhaustive-deps warnings
- [x] SpecialOpsReportPanel.tsx has no exhaustive-deps warnings
- [x] regulation/RegulationGeneratorPageClient.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for these files
