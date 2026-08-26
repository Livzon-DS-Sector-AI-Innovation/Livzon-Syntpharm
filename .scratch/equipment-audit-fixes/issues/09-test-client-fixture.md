# 09: Test Infrastructure - TestClient Fixture

**What to build:** Move TestClient initialization into pytest fixtures and replace manual `dependency_overrides.clear()` with try/finally blocks or fixture-based cleanup, so that test state is properly isolated and cleaned up even when assertions fail.

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] Create pytest fixture for TestClient initialization
- [x] Replace module-level TestClient initialization with fixture
- [x] Replace manual dependency_overrides.clear() with try/finally or fixture cleanup
- [x] Ensure test isolation is maintained
- [x] All existing tests continue to pass
- [x] No unsafe cleanup patterns remain
