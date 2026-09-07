# 45.7 — Fix exhaustive-deps in Safety module

**What to build:** Fix all React hooks dependency warnings in the Safety module so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] AIWorkflowConfigClient.tsx has no exhaustive-deps warnings
- [ ] KnowledgeBasePicker.tsx has no exhaustive-deps warnings
- [ ] KnowledgeGraphPanel.tsx has no exhaustive-deps warnings
- [ ] SpecialOpsReportPanel.tsx has no exhaustive-deps warnings
- [ ] regulation/RegulationGeneratorPageClient.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for these files
