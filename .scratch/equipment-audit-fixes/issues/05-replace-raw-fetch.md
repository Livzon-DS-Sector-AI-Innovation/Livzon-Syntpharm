# 05: Replace Raw Fetch Calls with Authenticated Client

**What to build:** Replace all raw `fetch()` calls in the equipment API layer with `apiFetch()` or `apiFetchRaw()` from the authenticated client, so that all API calls consistently apply authentication headers.

**Blocked by:** 04: API Client Type Safety - Contract Phase

**Status:** completed

- [x] Replace all raw fetch() calls in src/lib/api/server/equipment.ts with apiFetch() or apiFetchRaw()
- [x] Ensure all API calls go through the authenticated client layer
- [x] Verify auth headers are properly applied in all cases
- [x] Ensure TypeScript compilation passes
- [x] All existing tests continue to pass
- [x] No raw fetch() calls remain in equipment API layer
