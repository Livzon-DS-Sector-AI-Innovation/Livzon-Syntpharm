# 07: Fix hardcoded paths

**What to build:** All scripts use relative paths or Path(__file__).parent patterns

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] No hardcoded absolute paths in backend scripts
- [ ] All scripts use Path(__file__).parent or relative paths
- [ ] Scripts work across different environments and developers
- [ ] No /home/zhuangweizi/... paths remain
