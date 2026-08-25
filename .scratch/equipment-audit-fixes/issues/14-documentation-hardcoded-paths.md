# 14: Documentation - Remove Hardcoded Paths

**What to build:** Replace all hardcoded absolute paths in backend/docs/flexible-import-guide.md and backend/docs/department-seeding-summary.md with relative paths or placeholder variables, so that documentation examples work across different environments without modification.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Replace /home/zhuangweizi/Livzon-Syntpharm/... with relative paths in flexible-import-guide.md
- [ ] Replace /home/zhuangweizi/Livzon-Syntpharm/... with relative paths in department-seeding-summary.md
- [ ] Use $(pwd) or relative path notation in shell command examples
- [ ] Verify documentation examples are still valid
- [ ] No hardcoded absolute paths remain in documentation
