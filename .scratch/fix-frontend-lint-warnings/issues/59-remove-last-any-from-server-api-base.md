# 59 — Remove last `any` types from server API base functions

**What to build:** Replace the final 2 `any` types in the server API layer with proper types. These are in foundational functions used throughout the codebase:
- `apiFetch<T = any>` generic default parameter
- `apiFetchFormData` return type `Promise<any>`

This requires updating all call sites (755 for apiFetch, 15 for apiFetchFormData) to either:
- Explicitly specify the generic type parameter, or
- Add type assertions at the call site

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Acceptance Criteria

- [ ] `apiFetch` generic default changed from `any` to `unknown` or removed
- [ ] `apiFetchFormData` return type changed from `Promise<any>` to `Promise<unknown>` or proper type
- [ ] All 755 `apiFetch` call sites updated with explicit types or type assertions
- [ ] All 15 `apiFetchFormData` call sites updated with explicit types or type assertions
- [ ] `tsc --noEmit` passes with no errors
- [ ] `pnpm lint` shows 0 `@typescript-eslint/no-explicit-any` warnings in `src/lib/api/server/`

## Notes

This is a wide refactor that affects many files. Consider using an expand-contract pattern:
1. First, add the new typed versions alongside the old ones
2. Migrate call sites in batches (e.g., by directory or module)
3. Finally, remove the old untyped versions

Alternatively, if the blast radius is too large, consider adding `eslint-disable` comments for these 2 specific cases with a comment explaining why they're left as `any`.
