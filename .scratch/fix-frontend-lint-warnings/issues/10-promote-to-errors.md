---
title: "Promote lint warnings to errors"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
  - ci
created: 2026-08-17
blocked_by: ["07-replace-any-components", "08-replace-any-app", "09-replace-any-remaining"]
spec: .scratch/fix-frontend-lint-warnings/spec.md
---

# 10 — Promote lint warnings to errors

## What to build

After this ticket, all ESLint rules that were previously set to `warn` are promoted to `error`. The CI now blocks on any lint violation, preventing future regressions. Running `pnpm lint` produces 0 warnings and 0 errors.

## Acceptance criteria

- [ ] Update `eslint.config.mjs` to change all `warn` rules to `error`:
  - `@typescript-eslint/no-explicit-any`: warn → error
  - `@typescript-eslint/no-unused-vars`: warn → error
  - `react/no-unescaped-entities`: warn → error
  - `react/jsx-key`: warn → error
  - `prefer-const`: warn → error
  - `react-hooks/rules-of-hooks`: warn → error
  - `react-hooks/exhaustive-deps`: warn → error
  - `react-hooks/set-state-in-effect`: warn → error
  - `react-hooks/static-components`: warn → error
  - `react-hooks/immutability`: warn → error
  - `react-hooks/purity`: warn → error
- [ ] `pnpm lint` produces 0 warnings and 0 errors
- [ ] CI passes with the updated rules
- [ ] Any future lint violation will now fail CI

## Notes

This is the final step. Only proceed after all warnings are resolved. The goal is to prevent regression — any new `any` type, unused import, or hooks misuse will now block the PR.
