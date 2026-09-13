# 34.7 — Type safety knowledge base actions

**What to build:** Type all safety knowledge base action functions (getKnowledgeArticles, createKnowledgeArticle, updateKnowledgeArticle, deleteKnowledgeArticle, generatePpt, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/safety/index.ts (SafetyKnowledgeArticle section)

## Acceptance Criteria

- [ ] All safety knowledge base action functions have explicit return types
- [ ] All `as any` type assertions removed from knowledge base functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in knowledge base functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
