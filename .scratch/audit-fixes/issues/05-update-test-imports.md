# 05: Update test imports and remove redundant markers

**What to build:** Cleaner test files with consolidated imports and no redundant @pytest.mark.asyncio. Test files should import shared fixtures from conftest.py and remove redundant pytest markers that are already configured in pyproject.toml.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] test_batch_import_v2.py imports from conftest.py
- [ ] test_department_mapping.py imports from conftest.py
- [ ] test_import_api_integration.py imports from conftest.py
- [ ] Duplicate MockDB definitions removed from test files
- [ ] Duplicate _extract_param_values definitions removed from test files
- [ ] Redundant @pytest.mark.asyncio markers removed (asyncio_mode = "auto" in pyproject.toml)
- [ ] All tests still pass
