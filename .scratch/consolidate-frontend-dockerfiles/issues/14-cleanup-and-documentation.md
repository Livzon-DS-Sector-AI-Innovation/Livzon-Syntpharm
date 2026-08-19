---
title: "Clean up legacy files and update documentation"
status: ready-for-agent
labels:
  - ready-for-agent
  - documentation
  - infrastructure
created: 2026-08-18
blocked_by:
  - .scratch/consolidate-frontend-dockerfiles/issues/13-restructure-ci-pipeline.md
spec: .scratch/consolidate-frontend-dockerfiles/spec.md
---

# 14 — Clean up legacy files and update documentation

## What to build

After this ticket, all legacy Docker files are removed and documentation accurately reflects the new multi-stage architecture. No broken references or outdated instructions remain. Developers can follow the documented workflow without encountering configuration issues.

## Acceptance criteria

- [ ] `frontend/Dockerfile.dev` deleted
- [ ] `AGENTS.md` Docker section updated to document multi-stage architecture
- [ ] `AGENTS.md` includes approval requirements for Docker files
- [ ] `docs/ai-audit-plan.md` section 13 updated with new audit questions
- [ ] No references to `Dockerfile.dev` remain in codebase
- [ ] All three workflows (production, development, E2E) tested and documented

## Notes

This is the final cleanup ticket. After completion, the multi-stage Docker architecture is fully implemented and documented. The approval requirements ensure future Docker changes are reviewed.
