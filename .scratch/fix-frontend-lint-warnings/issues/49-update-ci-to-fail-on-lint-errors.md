# 49 — Update CI to fail on lint errors

**What to build:** Ensure CI pipeline fails on any lint error. Update GitHub Actions workflow if needed to treat lint errors as build failures.

**Blocked by:** Ticket 48 (rules flipped to error)

**Status:** done

- [x] CI pipeline fails on lint errors
- [x] GitHub Actions workflow updated if needed
- [x] PR with lint error cannot merge
- [ ] `pnpm lint` passes in CI (350 errors remain - needs follow-up tickets)

**Notes:**
- CI is already properly configured to fail on lint errors
- `.github/workflows/ci.yml` runs `bash scripts/ci.sh lint` in the `frontend-lint` job
- `scripts/ci.sh` has `set -e` and checks `pnpm lint` exit code
- When `pnpm lint` fails (exit code 1), CI job fails
- In ticket 48, all ESLint rules were changed from "warn" to "error"
- Currently 350 lint errors remain (176 no-explicit-any, 122 no-unused-vars, others)
- These errors need to be fixed in follow-up tickets before CI will pass
- No changes to CI configuration were needed - it was already correct
