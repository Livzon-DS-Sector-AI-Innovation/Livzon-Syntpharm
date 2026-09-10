# 66 — Replace `any` in equipment, production, safety pages

**What to build:** All equipment, production, and safety page components use proper types instead of `any`. This includes API response callbacks, error handlers, and data transformations. The `production/product-output/` pages have 17 warnings with complex data transformations that need careful typing.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All `any` types replaced with proper types in equipment pages
- [ ] All `any` types replaced with proper types in production pages
- [ ] All `any` types replaced with proper types in safety pages
- [ ] API response callbacks properly typed (e.g., `(cats: any[])` → `(cats: EquipmentCategory[])`)
- [ ] `tsc --noEmit` passes with no errors
- [ ] `pnpm lint` shows 0 `@typescript-eslint/no-explicit-any` warnings in equipment, production, safety pages
- [ ] Affected files: `EquipmentPage.tsx` (6 warnings), `equipment/inspection/page.tsx` (2 warnings), `production/product-output/` pages (17 warnings), `safety/hazard/[id]/page.tsx` (5 warnings)
