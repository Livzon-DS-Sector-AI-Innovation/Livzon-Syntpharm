# 45.20 — Fix exhaustive-deps in Safety workflow and regulation

**What to build:** Fix all React hooks dependency warnings in Safety workflow, hazard detail, regulation, and SOP editor components so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] safety/WorkflowListPanel.tsx has no exhaustive-deps warnings
- [ ] safety/hazard-identification/HazardIdentificationDetailPageClient.tsx has no exhaustive-deps warnings
- [ ] safety/hazard/HazardDetailPageClient.tsx has no exhaustive-deps warnings
- [ ] safety/regulation/SafetyRegulationPageClient.tsx has no exhaustive-deps warnings
- [ ] safety/SopContentEditor.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for these files
