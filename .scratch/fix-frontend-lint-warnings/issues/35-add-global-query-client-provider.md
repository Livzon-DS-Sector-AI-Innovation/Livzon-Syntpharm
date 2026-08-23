# 35 — Add global QueryClientProvider

**What to build:** Add a global QueryClientProvider at the app level (in src/app/layout.tsx or a new src/app/providers.tsx) so React Query is available app-wide. Currently only exists for equipment/personnel module.

**Blocked by:** Tickets 01-34 (reduce noise first)

**Status:** done

- [x] Global QueryClientProvider added at app level
- [x] QueryClient configured with appropriate defaults
- [x] All pages can use useQuery/useMutation
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes
- [x] Existing equipment/personnel QueryProvider removed or refactored to use global provider
