# 51 — Add React Hooks rules to AGENTS.md and update audit plan

**What to build:** Add a "React Hooks 与 React Compiler" section to AGENTS.md under the frontend section, and update docs/ai-audit-plan.md to include audit checks for these new rules. This educates developers upfront about the patterns required by React Compiler, and ensures compliance can be verified.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Section added to AGENTS.md under "前端 — Next.js / TypeScript"
- [ ] Covers: data fetching with React Query (not useEffect + setState)
- [ ] Covers: derived state with useMemo (not useEffect + setState)
- [ ] Covers: complete useEffect dependency arrays
- [ ] Covers: immutable state updates
- [ ] Includes correct/incorrect code examples
- [ ] Add new audit category to docs/ai-audit-plan.md for React Hooks compliance
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes
