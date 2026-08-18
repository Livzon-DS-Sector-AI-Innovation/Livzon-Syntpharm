# 04 — Restructure AGENTS.md

**What to build:** AGENTS.md is reduced from 715 to ~450 lines. How-to content (code examples) moves to `development-guide.md`. Rules stay in AGENTS.md with "why" added to non-obvious ones. API diagram is deduplicated. References point to `examples/` at repo root.

**Blocked by:** 01 — Move examples to repo root, 02 — Consolidate backend docs

**Status:** ready-for-agent

- [ ] Code examples for authentication, config, feishu, storage, OCR, LLM, error handling move to `backend/docs/development-guide.md`
- [ ] Rules + pointers stay in AGENTS.md (e.g., "使用全局单例 llm_client，禁止创建自己的")
- [ ] Two duplicate API diagrams (lines 584 and 654) merge into one canonical version in "类型系统" section
- [ ] ~10 non-obvious "禁止" rules get "why" explanations
- [ ] All references to `backend/examples/` and `frontend/examples/` update to `examples/`
- [ ] AGENTS.md is ≤500 lines (target ~450)
