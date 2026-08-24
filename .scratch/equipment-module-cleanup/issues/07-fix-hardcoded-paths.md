# 07: Fix hardcoded paths

**What to build:** All scripts use relative paths or Path(__file__).parent patterns

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] No hardcoded absolute paths in backend scripts
- [x] All scripts use Path(__file__).parent or relative paths
- [x] Scripts work across different environments and developers
- [x] No /home/zhuangweizi/... paths remain
