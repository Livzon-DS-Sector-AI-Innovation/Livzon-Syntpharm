# 13 — Safety other endpoints: response models + frontend types

**What to build:** Frontend can use generated types for EHS changes, regulations, daily risk reports, occupational health exams, knowledge base, scheduled tasks, feishu integration, and AI workflow APIs. All remaining safety endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Response wrapper schemas created for EHS changes, regulations, daily risk reports, occupational health exams, knowledge base, scheduled tasks, feishu integration, and AI workflow
- [ ] All remaining safety endpoints updated to use specific response models
- [ ] Backend OpenAPI spec exported and includes all remaining safety response schemas
- [ ] Frontend types regenerated from updated spec
- [ ] Frontend safety API calls updated to use generated types (replace remaining `safeApiFetch<unknown>` with concrete types)
- [ ] TypeScript compilation passes
- [ ] Runtime API responses match generated types (spot-check 2-3 endpoints from each sub-module)
- [ ] No `response_model=ApiResponse` remaining in safety module
