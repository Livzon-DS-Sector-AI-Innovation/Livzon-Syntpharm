# 04: Create HR public API for department lookup

**What to build:** HR module exposes get_department_by_name() and list_departments() functions for cross-module use

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] HR public API exposes get_department_by_name(name: str) -> Department | None
- [x] HR public API exposes list_departments() -> list[Department]
- [x] Functions use existing department repository
- [x] Public API is properly exported from HR module
- [ ] Tests verify lookup functionality
