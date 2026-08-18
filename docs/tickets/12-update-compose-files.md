---
title: "Update docker-compose files for multi-stage architecture"
status: ready-for-agent
labels:
  - ready-for-agent
  - infrastructure
  - docker
  - frontend
created: 2026-08-18
blocked_by:
  - docs/tickets/11-refactor-dockerfile-multistage.md
spec: docs/specs/consolidate-frontend-dockerfiles.md
---

# 12 — Update docker-compose files for multi-stage architecture

## What to build

After this ticket, all three docker-compose files use `target:` directives to select the appropriate build stage from the multi-stage Dockerfile. The development environment supports hot reload with native inotify file watching. The production environment builds the optimized standalone image. The CI/E2E environment builds the production image for testing.

## Acceptance criteria

- [ ] `docker-compose.yml` specifies `target: runtime` for frontend service
- [ ] `docker-compose.dev.yml` specifies `target: dev` for frontend service
- [ ] `docker-compose.dev.yml` includes volume mounts for source code and `.next` cache
- [ ] `docker-compose.ci.yml` specifies `target: runtime` for frontend service
- [ ] Development environment starts successfully with `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build`
- [ ] Production environment starts successfully with `docker compose up -d --build`
- [ ] Hot reload works in development (edit file → browser updates)

## Notes

This ticket fixes the broken `docker-compose.dev.yml` that has been non-functional since commit 96e9881. The development environment now properly uses the `dev` stage instead of inheriting the production Dockerfile.
