---
title: "Restructure CI pipeline to use Docker for frontend build"
status: ready-for-agent
labels:
  - ready-for-agent
  - infrastructure
  - ci
  - frontend
created: 2026-08-18
blocked_by:
  - docs/tickets/12-update-compose-files.md
spec: docs/specs/consolidate-frontend-dockerfiles.md
---

# 13 — Restructure CI pipeline to use Docker for frontend build

## What to build

After this ticket, the `frontend-build` CI job runs in Docker and produces the production image. The `e2e` job depends on `frontend-build` and tests the exact image that gets deployed. Artifact sharing ensures E2E tests the validated image. Users can run just `frontend-build` for quick validation without running E2E tests.

## Acceptance criteria

- [ ] `frontend-build` job builds Docker image using `target: runtime`
- [ ] `frontend-build` job saves Docker image as GitHub Actions artifact
- [ ] `e2e` job has `needs: frontend-build` dependency
- [ ] `e2e` job loads Docker image from artifact
- [ ] `e2e` job runs tests against the production image (no build inside container)
- [ ] `scripts/ci.sh` E2E section updated to use pre-built image
- [ ] CI pipeline succeeds end-to-end
- [ ] Running only `frontend-build` job works independently

## Notes

This is the first CI build job to run in Docker. Other jobs (lint, typecheck) remain on GitHub runners for speed. The artifact sharing pattern ensures consistency between build and test stages.
