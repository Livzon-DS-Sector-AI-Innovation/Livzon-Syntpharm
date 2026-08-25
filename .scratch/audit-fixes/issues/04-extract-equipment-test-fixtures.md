# 04: Extract equipment test fixtures to conftest.py

**What to build:** Shared MockDB and helper functions eliminate duplication across test files. Test fixtures that are currently duplicated in multiple test files should be moved to a shared conftest.py file.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] backend/tests/modules/equipment/conftest.py created
- [ ] MockDB class moved to conftest.py
- [ ] _extract_param_values helper moved to conftest.py
- [ ] create_mock_department helper moved to conftest.py
- [ ] Fixtures are properly scoped for pytest
- [ ] Existing tests can import from conftest
