# 35 — Add global QueryClientProvider

**What to build:** Add a global QueryClientProvider at the app level (in src/app/layout.tsx or a new src/app/providers.tsx) so React Query is available app-wide. Currently only exists for equipment/personnel module.

**Blocked by:** Tickets 01-34 (reduce noise first)

**Status:** ready-for-agent

- [ ] Global QueryClientProvider added at app level
- [ ] QueryClient configured with appropriate defaults
- [ ] All pages can use useQuery/useMutation
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes
- [ ] Existing equipment/personnel QueryProvider removed or refactored to use global provider
