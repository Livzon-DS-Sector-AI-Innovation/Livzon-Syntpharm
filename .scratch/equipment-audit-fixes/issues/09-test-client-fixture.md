# 09: Test Infrastructure - TestClient Fixture

**What to build:** Move TestClient initialization into pytest fixtures and replace manual `dependency_overrides.clear()` with try/finally blocks or fixture-based cleanup, so that test state is properly isolated and cleaned up even when assertions fail.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Create pytest fixture for TestClient initialization
- [ ] Replace module-level TestClient initialization with fixture
- [ ] Replace manual dependency_overrides.clear() with try/finally or fixture cleanup
- [ ] Ensure test isolation is maintained
- [ ] All existing tests continue to pass
- [ ] No unsafe cleanup patterns remain
