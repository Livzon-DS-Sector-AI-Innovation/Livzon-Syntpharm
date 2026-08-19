# Rewrite README.md: focus on "what" and "how to deploy"

## Problem Statement

The current README.md (233 lines) contains too much information that overlaps with AGENTS.md and other documentation. It includes module tables, repo structure diagrams, service lists, troubleshooting commands, and detailed development sections. This makes it hard for readers to quickly understand what the repo is about and how to deploy it. New developers don't know where to start, and the README doesn't explain the business purpose of the system.

## Solution

Rewrite README.md to focus on two things:
1. **What this repo is about** — business context, tech stack overview
2. **How to deploy it** — prerequisites, quick start, access URLs

Everything else (repo structure, detailed development setup, troubleshooting) moves to or stays in specialized docs (AGENTS.md, development-guide.md, docker-compose.yml).

## User Stories

1. As a new developer joining the team, I want to understand what this system does and why it exists, so that I can contextualize my work
2. As a new developer, I want to know what OS and tools I need before cloning the repo, so that I don't waste time on incompatible environments
3. As a new developer, I want a minimal set of commands to deploy the system, so that I can see it running within 10 minutes
4. As a new developer, I want to know the URLs to access the frontend, API, and documentation, so that I can start using the system
5. As a new developer, I want to know how to start the dev servers for backend and frontend, so that I can begin coding
6. As a new developer, I want a link to the development guide, so that I can learn about testing, migrations, and other development workflows
7. As an external stakeholder (manager, client, auditor), I want to understand the business purpose of the system, so that I can evaluate its value
8. As an external stakeholder, I want to see the tech stack at a glance, so that I can assess technical fit
9. As a reader, I want the README to be concise (under 100 lines), so that I can scan it quickly without getting lost

## Implementation Decisions

### 1. Add a one-liner "why"

The current README says "原料药厂 ERP 管理系统" but doesn't explain why it was built. Add a sentence explaining the business purpose: replaces legacy systems and provides integrated data management for GMP compliance.

### 2. Delete the module table

The current README lists 12 modules with descriptions. This is not actionable and will become outdated as the system grows. Delete it.

### 3. Delete the repo structure diagram

The current README shows the directory structure. This overlaps with AGENTS.md and is not essential for deployment. Delete it.

### 4. Keep tech stack overview

The backend and frontend tech stack lists are essential context for both developers and stakeholders. Keep them.

### 5. Add Prerequisites section

List only what we're sure of:
- Ubuntu 22.04+ (or any Linux distribution that supports Docker)
- Docker + Docker Compose
- Git

Do not specify system resources (CPU/RAM/disk) since we don't have concrete requirements.

### 6. Simplify Deployment section

Keep:
- Quick start (3 commands: cp .env, docker compose up)
- Access URLs (frontend, API, docs, MinIO)

Delete:
- Service table (8 services with ports) — this is in docker-compose.yml
- Troubleshooting commands — this is operational detail

### 7. Minimal Development section

Keep only the commands to start dev servers:
- Backend: `cd backend && uv run uvicorn app.main:app --reload`
- Frontend: `cd frontend && pnpm dev`

Link to `backend/docs/development-guide.md` for testing, migrations, API type generation, and other development workflows.

Delete:
- Backend environment setup details
- Backend testing commands
- Backend migration commands
- Frontend environment setup details
- Frontend testing commands
- Frontend API type generation commands

### 8. Delete Data persistence section

The list of runtime directories (postgres-data/, redis-data/, etc.) is redundant with docker-compose.yml and .gitignore. Delete it.

### 9. Delete 注意事项 section

The current "注意事项" section contains obvious advice (don't commit .env, containers run in detached mode). This is not needed. Delete it.

### 10. Final structure

```
# Livzon Syntpharm ERP System

[One-liner: what it is + why it exists]

## 技术栈
[Backend tech stack]
[Frontend tech stack]

## Prerequisites
- Ubuntu 22.04+
- Docker + Docker Compose
- Git

## 部署

### 快速开始
[3 commands]

### 访问地址
[4 URLs]

## 开发

[2 commands to start dev servers]

[Link to backend/docs/development-guide.md]
```

Target: under 100 lines (down from 233).

## Testing Decisions

### What makes a good test

- Verify no essential information is lost (tech stack, deployment commands, access URLs)
- Verify no overlap with AGENTS.md (repo structure, detailed development setup)
- Verify the README is under 100 lines
- Verify a new developer can deploy the system by following the README alone

### Test scenarios

1. **Information preservation**: Verify tech stack, deployment commands, and access URLs are present
2. **No overlap**: Verify repo structure, module table, service table, troubleshooting, and detailed development sections are removed
3. **Length check**: Verify README is under 100 lines
4. **Deployment test**: Follow the README from scratch on a fresh Ubuntu VM and verify the system is accessible

### Prior art

- The existing `backend/docs/development-guide.md` already covers detailed development workflows
- The existing `AGENTS.md` already covers repo structure and coding standards
- The existing `docker-compose.yml` already lists all services and ports

## Out of Scope

- **Module catalog**: The README will not include a business description of each module. The module names are self-explanatory to the team, and the system will grow beyond the current 12 modules.
- **System resource requirements**: The README will not specify CPU/RAM/disk requirements since we don't have concrete data. This can be added later when we have benchmarks.
- **Network requirements**: The README will not list firewall rules or port requirements. This is operational detail that belongs in a deployment guide.
- **Post-deployment setup**: The README will not cover creating admin users, configuring Feishu integration, or importing initial data. This can be added in a "Getting Started Guide" later.

## Further Notes

### Files modified

- `README.md` — rewritten from 233 lines to ~80 lines

### Files not modified

- `AGENTS.md` — unchanged (already covers repo structure and coding standards)
- `backend/docs/development-guide.md` — unchanged (already covers detailed development workflows)
- `docker-compose.yml` — unchanged (already lists all services and ports)

### Migration notes

This is a documentation-only change. No code is modified. No migration is needed.

### Future work

- Add a "Getting Started Guide" that covers post-deployment setup (creating admin users, configuring integrations)
- Add system resource requirements when we have benchmarks
- Add network requirements when we have a deployment checklist
