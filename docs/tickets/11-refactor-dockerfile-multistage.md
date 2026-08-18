---
title: "Refactor frontend Dockerfile to multi-stage build"
status: ready-for-agent
labels:
  - ready-for-agent
  - infrastructure
  - docker
  - frontend
created: 2026-08-18
blocked_by: []
spec: docs/specs/consolidate-frontend-dockerfiles.md
---

# 11 — Refactor frontend Dockerfile to multi-stage build

## What to build

After this ticket, the frontend has a single multi-stage Dockerfile with four named stages: `base`, `dev`, `builder`, and `runtime`. The `base` stage installs dependencies once, shared by all other stages. The `dev` stage runs the development server with hot reload. The `builder` stage runs the production build. The `runtime` stage contains only the standalone output for minimal image size.

## Acceptance criteria

- [ ] `frontend/Dockerfile` has four stages: `base`, `dev`, `builder`, `runtime`
- [ ] `base` stage installs pnpm 10.33.0 and dependencies
- [ ] `dev` stage copies source code and runs `pnpm dev`
- [ ] `builder` stage runs `pnpm build` with production environment variables
- [ ] `runtime` stage copies only standalone output (`.next/standalone`, `.next/static`, `public`)
- [ ] Production image size remains ~100-150MB
- [ ] All stages build successfully without errors

## Notes

This is the foundation for the multi-stage architecture. The existing `Dockerfile` behavior (production build) must be preserved in the `runtime` stage. The `dev` stage replaces the functionality of the current `Dockerfile.dev`.
