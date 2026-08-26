# 11: Update equipment module to use HR public API

**What to build:** Equipment module imports departments through HR public API instead of direct model imports

**Blocked by:** 04: Create HR public API for department lookup

**Status:** completed

- [x] Equipment module imports departments through HR public API
- [x] No direct imports of HrDepartment model in equipment module
- [x] Department lookup uses get_department_by_name() function
- [x] All existing functionality preserved
- [x] Tests verify department lookup works correctly
