# 08: Generated types migration - expand

**What to build:** Generated type aliases available alongside hand-written types (no breakage). This is the first step of an expand-contract pattern for a wide refactor. Generated types from OpenAPI spec should be made available as type aliases that can be used alongside existing hand-written types.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Generated types extracted from schema.ts operations
- [ ] Type aliases created for query parameters (e.g., GetEquipmentsQuery, GetStatisticsQuery)
- [ ] Type aliases exported from a central location
- [ ] Both hand-written and generated types coexist without conflicts
- [ ] No existing code broken
- [ ] TypeScript compilation succeeds
