# 64 — Replace `any` in administration pages

**What to build:** All administration page components use proper types instead of `any`. This includes replacing `useState<any>(null)` with specific record types, form handlers with form field interfaces, error catches with `unknown` and type guards, and table column renderers with actual row types.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All `useState<any>(null)` replaced with specific types (e.g., `useState<MeetingLedgerItem | null>(null)`)
- [ ] All form handlers `(values: any)` replaced with form field interfaces
- [ ] All `catch (err: any)` replaced with `catch (err: unknown)` and type guards
- [ ] All table column renderers `(_: any, record: any)` replaced with actual row types
- [ ] `tsc --noEmit` passes with no errors
- [ ] `pnpm lint` shows 0 `@typescript-eslint/no-explicit-any` warnings in administration pages
- [ ] Affected files: `meeting/ledger/page.tsx`, `meeting/requisitions/page.tsx`, `vehicles/page.tsx`
