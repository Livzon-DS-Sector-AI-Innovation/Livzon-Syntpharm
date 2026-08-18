---
title: "Consolidate frontend Dockerfiles into multi-stage build"
status: ready-for-agent
labels:
  - ready-for-agent
  - infrastructure
  - docker
  - frontend
  - ci
created: 2026-08-18
updated: 2026-08-18
author: ruanjiaheng
---

# Spec: Consolidate Frontend Dockerfiles into Multi-Stage Build

## Problem Statement

The frontend has two separate Dockerfiles (`Dockerfile` for production, `Dockerfile.dev` for development) that drift out of sync over time. The `Dockerfile.dev` is only used by `docker-compose.ci.yml` for E2E testing. The `docker-compose.dev.yml` file is broken — it inherits the production `Dockerfile` but tries to run `bash -c "pnpm dev"` in a runtime image that lacks bash, pnpm, and source code. This configuration has been broken since commit 96e9881 (Aug 10, 2026) but nobody noticed because the actual development workflow uses `scripts/dev.sh` which runs the production compose directly.

## Solution

Consolidate the two separate Dockerfiles into a single multi-stage Dockerfile with named stages (`base`, `dev`, `builder`, `runtime`). Use Docker Compose's `target:` directive to select which stage to build for different environments. Restructure CI pipeline so that `frontend-build` runs in Docker and `e2e` depends on it. Update documentation files to reflect the new architecture.

## User Stories

1. As a developer, I want a single source of truth for frontend Docker builds, so that production and development environments never drift out of sync.
2. As a developer, I want `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build` to work correctly, so that I can use the documented development workflow.
3. As a developer, I want hot module replacement (HMR) to work in development on Linux (native inotify), so that I can see code changes immediately without manual rebuilds.
4. As a CI engineer, I want the `frontend-build` job to run in a Docker container, so that CI validates the production Docker image.
5. As a CI engineer, I want the `e2e` job to depend on `frontend-build`, so that E2E tests only run if the production image builds successfully.
6. As a developer, I want to be able to run just the `frontend-build` job without running E2E tests, so that I can quickly validate the build.
7. As a developer, I want the production Docker image to remain small (~100-150MB), so that deployments are fast and resource-efficient.
8. As a team lead, I want all Dockerfile and docker-compose changes to require approval, so that infrastructure changes are reviewed before deployment.
9. As a developer, I want `AGENTS.md` to accurately describe the Docker setup, so that I can follow the documented workflow without encountering broken configurations.
10. As a developer, I want the multi-stage Dockerfile to share dependency installation across stages, so that build times are minimized through layer caching.

## Implementation Decisions

### 1. Multi-Stage Dockerfile Structure

The frontend Dockerfile will have four stages:

1. **base** — Shared foundation: Node 22 Alpine, pnpm 10.33.0, npm registry configuration, dependency installation
2. **dev** — Development stage: copies source code, exposes port 3000, runs `pnpm dev`
3. **builder** — Production build stage: copies source code, sets production env vars, runs `pnpm build`
4. **runtime** — Production runtime stage: minimal Alpine image, copies only standalone output from builder

### 2. Docker Compose Configuration

**Production (`docker-compose.yml`):**
- Uses `target: runtime` to build the final production stage
- No volume mounts (standalone output is self-contained)
- Runs `node server.js` (standalone mode)

**Development (`docker-compose.dev.yml`):**
- Uses `target: dev` to build the development stage
- Volume mounts: `./frontend:/app:ro` (source code), `/app/node_modules` (preserve deps), `frontend_dev_next:/app/.next` (webpack cache)
- Runs `pnpm dev` with hot reload
- File watching uses Linux kernel inotify (no polling needed)

**CI/E2E (`docker-compose.ci.yml`):**
- Uses `target: runtime` to build the production image
- E2E tests run against the production image
- Note: GitHub Actions CI jobs (lint, typecheck) run directly on runners, not in Docker

### 3. CI Pipeline Restructuring

**Current state:**
- `frontend-build` job runs on GitHub runner (no Docker)
- `e2e` job runs in parallel with `frontend-build`
- E2E builds a dev container and runs `pnpm build && next start` inside it

**Target state:**
- `frontend-build` job runs in Docker, builds production image, saves as artifact
- `e2e` job depends on `frontend-build` (`needs: frontend-build`)
- E2E loads pre-built production image from artifact

**Job dependency chain:**
```
frontend-lint (runner) ──┐
frontend-typecheck (runner) ──┼── frontend-build (Docker) ── e2e (Docker)
backend-lint (runner) ──┘
backend-typecheck (runner) ──┘
```

**Artifact sharing strategy:**
- `frontend-build` job builds Docker image and saves it using `docker save`
- Image is uploaded as GitHub Actions artifact
- `e2e` job downloads artifact and loads image using `docker load`
- This ensures E2E tests the exact image that was validated in `frontend-build`

**Files to modify:**
- `.github/workflows/ci.yml` — restructure jobs, add artifact handling
- `scripts/ci.sh` — update E2E section to use pre-built image

### 4. File Watching Strategy

Docker containers run on Linux kernel, which supports native inotify file watching. Volume mount events propagate immediately via inotify — no polling needed.

**Note:** This project only supports Linux kernel for development. Windows NT and XNU (macOS) kernels are not supported for local Docker development.

### 5. Approval Requirements

All Docker-related files require approval before editing:
- `frontend/Dockerfile`
- `backend/Dockerfile`
- `docker-compose.yml`
- `docker-compose.dev.yml`
- `docker-compose.ci.yml`

Rationale: Docker configuration affects all developers and deployment pipelines. Changes should be reviewed to prevent breaking the development workflow or production builds.

### 6. Documentation Updates Required

The following files need to be updated after implementation:

1. **`AGENTS.md`** (lines 606-617, "Docker 开发环境" section):
   - Document the multi-stage Dockerfile architecture (base → dev/builder → runtime)
   - Correct the production runtime description (`node server.js`, not `next start`)
   - Explain the `target:` directive usage for each compose file
   - Add new section documenting approval requirements for all Docker files

2. **`docs/ai-audit-plan.md`** (section 13, "Docker and deployment"):
   - Update rules to reflect multi-stage build architecture
   - Update audit questions to validate `target:` directives
   - Add questions about approval requirements
   - Update directory inspection list

### 7. Backward Compatibility

- `docker-compose.yml` behavior unchanged (still builds production image, now with explicit `target: runtime`)
- `docker-compose.dev.yml` now works correctly (was broken since Aug 10)
- `docker-compose.ci.yml` changes from `dockerfile: Dockerfile.dev` to `target: runtime`
- `frontend/Dockerfile.dev` deleted (replaced by `target: dev` in main Dockerfile)
- CI pipeline restructured: `e2e` now depends on `frontend-build`

## Testing Decisions

### What makes a good test

Tests should verify external behavior (container starts, serves content, responds to changes) rather than implementation details (specific Docker layers, build commands).

### Modules to test

1. **Production build:**
   - Container starts successfully
   - Serves the frontend on port 3000
   - Image size is ~100-150MB
   - No source code or node_modules in final image

2. **Development build:**
   - Container starts successfully
   - Hot reload works (edit file → browser updates)
   - File watching works on Linux (native inotify)
   - Volume mounts don't break node_modules

3. **CI/E2E build:**
   - Production container builds successfully using `target: runtime`
   - Docker image is saved and loaded as artifact
   - E2E tests run against production image
   - Image matches what gets deployed

### Prior art

- Existing `scripts/ci.sh` tests the CI build
- Existing `scripts/dev.sh` tests the development workflow
- Production deployment pipeline tests the production build

## Out of Scope

- Backend Dockerfile refactoring (backend has only one Dockerfile, no drift issue)
- Changing the production runtime from standalone mode to `next start`
- Adding image optimization CDN (current setup uses standalone mode without built-in image optimization)
- Optimizing build cache across different environments (each compose file builds independently)
- Adding health checks to frontend containers (not currently implemented)
- Supporting Windows NT or XNU kernels for local Docker development
- Changing GitHub Actions CI jobs (lint, typecheck) to use Docker (they run directly on runners)

## Further Notes

### Current broken state

The `docker-compose.dev.yml` file has been broken since commit 96e9881 (Aug 10, 2026) when the `dockerfile: Dockerfile.dev` line was removed. The file now inherits the production Dockerfile but tries to run development commands in a runtime image that lacks the necessary tools.

### Why nobody noticed

The actual development workflow uses `scripts/dev.sh`, which runs `docker compose up -d` (production compose only), not the dev overlay. Developers who followed the README instructions (`docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build`) would have encountered a broken frontend container.

### Migration path

1. Refactor `frontend/Dockerfile` to multi-stage structure
2. Update `docker-compose.yml` to add `target: runtime`
3. Update `docker-compose.dev.yml` to add `target: dev` and fix volume mounts
4. Update `docker-compose.ci.yml` to change from `dockerfile: Dockerfile.dev` to `target: runtime`
5. Update `.github/workflows/ci.yml`:
   - Restructure `frontend-build` job to build Docker image and save as artifact
   - Add `needs: frontend-build` to `e2e` job
   - Update `e2e` job to load Docker image from artifact
6. Update `scripts/ci.sh` E2E section to use pre-built Docker image
7. Delete `frontend/Dockerfile.dev` (no longer needed)
8. Update `AGENTS.md` to document the new architecture and approval requirements
9. Update `docs/ai-audit-plan.md` section 13 to reflect new Docker architecture
10. Test all three workflows: production, development, E2E

### Alternative considered

**Keep separate Dockerfiles:** Rejected because it requires maintaining two files that must stay in sync. The multi-stage approach provides a single source of truth while still allowing different build targets.

### Image size optimization

The multi-stage approach maintains the current production image size (~100-150MB) because the `runtime` stage only copies the standalone output, not the full build environment.

### Platform support

This project only supports Linux kernel for Docker development. Windows NT and XNU (macOS) kernels are not supported for local Docker development environments.
