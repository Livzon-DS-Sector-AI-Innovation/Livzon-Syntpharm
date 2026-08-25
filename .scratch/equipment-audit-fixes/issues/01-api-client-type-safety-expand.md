# 01: API Client Type Safety - Expand Phase

**What to build:** Add typed versions of all equipment API functions alongside the existing `data: any` versions, so that callers can gradually migrate to type-safe versions without breaking existing code.

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] Create typed versions of all equipment API functions in src/lib/api/server/equipment.ts
- [x] Use generated types from components['schemas'] for all request bodies
- [x] Maintain backward compatibility by keeping old `data: any` versions
- [x] Ensure TypeScript compilation passes with strict mode
- [x] No existing code breaks
