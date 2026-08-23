# 21 — Type registration API client

**What to build:** Replace all `any` types in registration API client with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All `any` types replaced with proper types in registration API client
- [x] Types sourced from `@/types/registration` or `@/types/generated/schema`
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in registration API)

## Summary

Fixed 6 @typescript-eslint/no-explicit-any warnings:
- fetchAuthorizationLetters: data `any[]` → `AuthorizationLetterListItem[]`
- fetchReferenceStandards: data `any[]` → `ReferenceStandardListItem[]`
- fetchSupplementaryReplies: data `any[]` → `SupplementaryReplyListItem[]`
- Added imports for AuthorizationLetterListItem, ReferenceStandardListItem, SupplementaryReplyListItem

Registration API client is now fully typed.
