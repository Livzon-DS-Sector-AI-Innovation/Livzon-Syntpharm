# 31 — Type research components

**What to build:** Replace all `any` types in research components with proper types. Define interfaces where they don't exist. All props, parameters, and return values are properly typed.

**Blocked by:** None — can start immediately

**Status:** done

- [x] All `any` types replaced with proper types in research components
- [x] Interfaces defined where needed
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in research components)

**Result:** Fixed 112 `any` warnings across 26 files (25 originally listed + ModuleScaleUp.tsx). Applied proper type patterns including catch blocks, Ant Design table renders, JSON field casts with defined interfaces, function parameters, and state types.
