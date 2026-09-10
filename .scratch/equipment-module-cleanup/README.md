# Equipment Module Cleanup

This directory contains the spec and tickets for cleaning up the equipment module.

## Spec

See [spec.md](spec.md) for the full specification.

## Tickets

17 tickets organized by deployment batch:

### Security Batch (deploy together)
- [01](issues/01-add-authentication-to-equipment-api.md): Add authentication to all equipment API endpoints
- [02](issues/02-add-auth-headers-to-frontend-api-client.md): Add authentication headers to frontend API client
- [03](issues/03-fix-cors-configuration.md): Fix CORS configuration

### Architecture Batch (deploy together)
- [04](issues/04-create-hr-public-api.md): Create HR public API for department lookup
- [11](issues/11-update-equipment-to-use-hr-public-api.md): Update equipment module to use HR public API (blocked by #04)
- [12](issues/12-move-write-operations-to-server-actions.md): Move write operations to Server Actions (blocked by #01)
- [14](issues/14-update-client-components-to-use-server-actions.md): Update client components to use Server Actions (blocked by #12)

### Type Safety (expand-contract pattern)
- [05](issues/05-expand-generated-types.md): Expand generated types
- [13](issues/13-migrate-equipment-components-to-generated-types-batch-1.md): Migrate batch 1 (blocked by #05)
- [15](issues/15-migrate-equipment-components-to-generated-types-batch-2.md): Migrate batch 2 (blocked by #13)
- [16](issues/16-migrate-equipment-components-to-generated-types-batch-3.md): Migrate batch 3 (blocked by #15)
- [17](issues/17-remove-old-hand-written-types.md): Remove old types (blocked by #16)

### Code Hygiene (independent deployments)
- [06](issues/06-remove-backup-files.md): Remove backup files
- [07](issues/07-fix-hardcoded-paths.md): Fix hardcoded paths
- [08](issues/08-consolidate-duplicate-components.md): Consolidate duplicate components

### Docker Improvements (independent deployments)
- [09](issues/09-add-docker-health-checks.md): Add Docker health checks
- [10](issues/10-implement-multi-stage-docker-builds.md): Implement multi-stage Docker builds

## Current Frontier (can start immediately)

Tickets with no blockers:
- 01: Add authentication to all equipment API endpoints
- 02: Add authentication headers to frontend API client
- 03: Fix CORS configuration
- 04: Create HR public API for department lookup
- 05: Expand generated types
- 06: Remove backup files
- 07: Fix hardcoded paths
- 08: Consolidate duplicate components
- 09: Add Docker health checks
- 10: Implement multi-stage Docker builds
