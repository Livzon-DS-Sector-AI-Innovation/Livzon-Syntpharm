# 63 — Replace `any` in administration pages

**What to build:** All administration page components use proper types instead of `any`. This includes replacing `useState<any>(null)` with specific record types, form handlers with form field interfaces, error catches with `unknown` and type guards, and table column renderers with actual row types.

**Blocked by:** None — can start immediately

**Status:** done

- [x] All `useState<any>(null)` replaced with specific types (e.g., `useState<MeetingLedgerItem | null>(null)`)
- [x] All form handlers `(values: any)` replaced with form field interfaces
- [x] All `catch (err: any)` replaced with `catch (err: unknown)` and type guards
- [x] All table column renderers `(_: any, record: any)` replaced with actual row types
- [x] `tsc --noEmit` passes with no errors
- [x] `pnpm lint` shows 0 `@typescript-eslint/no-explicit-any` warnings in administration pages
- [x] Affected files: `meeting/ledger/page.tsx`, `meeting/requisitions/page.tsx`, `vehicles/page.tsx`

## Implementation Notes

### Key Changes

1. **GiftInventory Interface**: Defined interface with fields: id, name, specification, unit, opening_stock, incoming_qty, closing_stock, unit_price, total_amount, status

2. **GiftRequisition Interface**: Defined interface with fields: id, seq_no, department, item_name, unit_price, quantity, total_amount, recipient, requisition_date, remarks

3. **Vehicle Interface**: Defined interface with fields: id, plate_number, brand, model, color, mileage, status, owner_department, photo_data, photo_type

4. **Error Handling**: Changed all `catch (err: any)` to `catch (err: unknown)` with proper type guards using `err instanceof Error ? err.message : '...'`

5. **Type Casts**: Added `as unknown as Record<string, unknown>` casts when passing typed objects to API functions that expect `Record<string, unknown>`

### Files Modified
- `src/app/(dashboard)/administration/meeting/ledger/page.tsx`: 6 warnings fixed
- `src/app/(dashboard)/administration/meeting/requisitions/page.tsx`: 6 warnings fixed
- `src/app/(dashboard)/administration/vehicles/page.tsx`: 8 warnings fixed
