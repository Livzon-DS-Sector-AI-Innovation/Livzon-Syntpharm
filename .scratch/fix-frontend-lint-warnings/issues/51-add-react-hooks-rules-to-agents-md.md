# 51 — Add React Hooks rules to AGENTS.md

**What to build:** Add a "React Hooks 与 React Compiler" section to AGENTS.md under the frontend section. This educates developers upfront about the patterns required by React Compiler, so they don't write code that violates behavioral lint rules.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Section added to AGENTS.md under "前端 — Next.js / TypeScript"
- [ ] Covers: data fetching with React Query (not useEffect + setState)
- [ ] Covers: derived state with useMemo (not useEffect + setState)
- [ ] Covers: complete useEffect dependency arrays
- [ ] Covers: immutable state updates
- [ ] Includes correct/incorrect code examples
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes
