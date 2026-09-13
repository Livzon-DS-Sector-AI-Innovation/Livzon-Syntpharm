# 33 — Type remaining components

**What to build:** Replace all `any` types in remaining components (registration, production, quality, energy, etc.) with proper types. Define interfaces where they don't exist. All props, parameters, and return values are properly typed.

**Blocked by:** None — can start immediately

**Status:** done

- [x] All `any` types replaced with proper types in remaining components
- [x] Interfaces defined where needed
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in remaining components)
