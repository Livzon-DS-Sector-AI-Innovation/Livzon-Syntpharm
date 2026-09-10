# 05 — Test CI integration end-to-end

**What to build:** Verify that the naming validation check integrates correctly with the CI pipeline, catches violations with clear error messages, and doesn't introduce regressions in existing scope validation.

**Blocked by:** 04 (Implement naming validation in CI)

**Status:** ready-for-agent

- [ ] Run `backend/scripts/ci/ci.sh migration-scope` locally and verify it passes on current codebase
- [ ] Verify the check validates both scope and naming in a single run
- [ ] Create a test migration file with invalid naming (e.g., `abc123_test.py`)
- [ ] Run CI check and verify it fails with expected error message
- [ ] Delete the test file
- [ ] Test with valid filename but invalid revision ID — verify caught
- [ ] Test with invalid filename but valid revision ID — verify caught
- [ ] Verify exit codes are correct (0 for pass, 1 for fail)
- [ ] Verify no regressions in existing scope validation
- [ ] Document the new check in any relevant CI documentation
