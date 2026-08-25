# 11: Test Infrastructure - Parametrize Similar Tests

**What to build:** Consolidate similar test cases using `@pytest.mark.parametrize` in test_smart_inference.py and test_batch_import.py, so that test code is DRY and easy to maintain.

**Blocked by:** 10: Test Infrastructure - Type Annotations

**Status:** ready-for-agent

- [ ] Identify similar test cases in test_smart_inference.py
- [ ] Consolidate using @pytest.mark.parametrize
- [ ] Identify similar test cases in test_batch_import.py
- [ ] Consolidate using @pytest.mark.parametrize
- [ ] Ensure all test cases still pass
- [ ] Test code is more concise and maintainable
