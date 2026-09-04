# 40.11 — Update parent ticket 40 status

**What to build:** Mark parent ticket 40 as complete after all sub-tickets (40.1-40.10) are completed. Update spec status and verify all safety module pages pass linting.

**Blocked by:** 40.1, 40.2, 40.3, 40.4, 40.5, 40.6, 40.7, 40.8, 40.9, 40.10

**Status:** ready-for-agent

- [ ] Verify all sub-tickets (40.1-40.10) are marked as done
- [ ] Run full lint check on safety module: `pnpm lint src/app/\(dashboard\)/safety/`
- [ ] Verify zero `@typescript-eslint/no-set-state-in-effect` warnings in safety module
- [ ] Run full typecheck: `pnpm typecheck`
- [ ] Update parent ticket 40 status to done
- [ ] Update spec status if applicable
