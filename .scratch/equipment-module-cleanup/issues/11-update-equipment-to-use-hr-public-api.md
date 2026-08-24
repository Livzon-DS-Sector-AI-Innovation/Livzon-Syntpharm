# 11: Update equipment module to use HR public API

**What to build:** Equipment module imports departments through HR public API instead of direct model imports

**Blocked by:** 04: Create HR public API for department lookup

**Status:** ready-for-agent

- [ ] Equipment module imports departments through HR public API
- [ ] No direct imports of HrDepartment model in equipment module
- [ ] Department lookup uses get_department_by_name() function
- [ ] All existing functionality preserved
- [ ] Tests verify department lookup works correctly
