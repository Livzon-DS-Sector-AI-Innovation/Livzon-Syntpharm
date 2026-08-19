# Polish AGENTS.md: reduce length, fix inconsistencies, improve rule quality

## Problem Statement

The AGENTS.md file has grown to 715 lines and contains duplicated content, overlaps with other documentation, and lacks explanations for many rules. AI agents and human developers both read this file, but the current structure makes it difficult to:

- Find the authoritative source for rules (some content appears twice)
- Understand why certain rules exist (most "禁止" rules lack justification)
- Locate code examples (scattered across backend/examples/, frontend/examples/, and development-guide.md)
- Distinguish between rules (must follow) and how-to guides (operational procedures)

## Solution

Restructure the documentation to achieve three goals:

1. **Reduce AGENTS.md length** from 715 to ~450 lines without omitting information
2. **Eliminate duplication** by consolidating examples and deleting redundant docs
3. **Improve rule quality** by adding "why" to non-obvious rules

The new structure separates concerns:
- AGENTS.md: terse rules + constraints (what to do, what not to do)
- development-guide.md: narrative how-to (how to use infrastructure)
- examples/: standalone code patterns and operational procedures

## User Stories

1. As an AI agent, I want AGENTS.md to be concise so that I can quickly understand the rules without parsing 715 lines on every task
2. As an AI agent, I want to know why certain rules exist (e.g., "禁止 response_model=dict") so that I can reason about edge cases
3. As a human developer, I want a single source of truth for code examples so that I don't have to search across multiple directories
4. As a new team member, I want clear separation between rules and how-to guides so that I know what's mandatory vs. what's a suggestion
5. As a developer, I want to find module structure examples at the repo root so that I don't have to navigate into backend/examples/
6. As a developer, I want to find operational procedures (like migration compression) in a predictable location so that I can perform one-time tasks
7. As a maintainer, I want to avoid duplicated content so that I don't have to update the same information in multiple places
8. As an AI agent, I want to know that central infrastructure exists (LLM client, OCR service, storage) so that I don't create duplicate implementations

## Implementation Decisions

### 1. AGENTS.md content split

**Keep in AGENTS.md** (rules + pointers):
- All "禁止" rules with "why" added for non-obvious ones
- Pointers to central infrastructure ("使用全局单例 llm_client，禁止创建自己的")
- Links to development-guide.md for code examples
- Docker development environment instructions (essential for frontend dev)

**Move to development-guide.md** (code examples):
- Authentication usage patterns (CurrentUser, JWT sources)
- Configuration management patterns (env var naming, get_settings() usage)
- Feishu integration patterns (FEISHU__{MODULE}__{FIELD} naming)
- File storage patterns (storage.py usage)
- OCR service patterns (get_ocr_service() initialization)
- LLM calling patterns (llm_client.chat() usage, streaming)
- Error handling patterns (retry strategies, degradation)

### 2. Examples consolidation

Move all standalone examples to repo root examples/:
- backend/examples/module-structure.md → examples/module-structure.md
- backend/examples/commands.md → examples/commands.md
- backend/docs/migration-baseline.md → examples/migration-compression.md
- frontend/examples/server-component-pattern.md → examples/server-component-pattern.md
- frontend/examples/server-actions.md → examples/server-actions.md

### 3. Documentation cleanup

- **Delete** backend/docs/architecture.md (redundant with AGENTS.md and module-structure.md)
- **Merge** backend/docs/development.md into backend/docs/development-guide.md (as "本地开发环境" section)
- **Keep** backend/docs/development-guide.md as the narrative how-to guide

### 4. API diagram deduplication

Merge the two duplicate API diagrams (lines 584 and 654) into one canonical version in the "类型系统" section. The first occurrence (line 584) in "新增 API 调用" will reference the canonical diagram.

### 5. Rule quality improvement

Add "why" to non-obvious "禁止" rules:
- "禁止 response_model=dict" → explain it breaks OpenAPI generation
- "禁止引入微服务" → explain this is a modular monolith by design
- "禁止在模块中直接 import paddleocr" → explain OCR service is centralized
- Other rules that aren't self-evident

### 6. CONTEXT.md creation

Create CONTEXT.md at repo root and add to .gitignore. This is a skill requirement for domain modeling, not a repo concern. Initially empty, populated as domain terms crystallize.


### 7. Audit plan updates

The `docs/ai-audit-plan.md` file references AGENTS.md extensively across 15 audit categories. After the AGENTS.md restructure, the audit plan must be updated:

**Path updates**:
- Update references from `backend/examples/` to `examples/`
- Update references from `frontend/examples/` to `examples/`

**Content updates**:
- Audit categories reference "Rules (from AGENTS.md)" — verify these rules still exist in AGENTS.md (some may have moved to development-guide.md as code examples, but the rules themselves stay)
- Category 1 (Repository layout) references directory structures — update if any paths changed
- Category 10 (Frontend API and generated types) references the API diagram — update to reference the canonical diagram location

**Validation**:
- Run a search for all file paths mentioned in ai-audit-plan.md and verify they still exist
- Run a search for all AGENTS.md section references and verify they still exist
- Ensure the audit plan's "Rules (from AGENTS.md)" sections match the actual rules in the updated AGENTS.md

This update is part of the same PR as the AGENTS.md polish to ensure the audit plan stays in sync.

## Testing Decisions

### What makes a good test

- Verify no information is lost (all original content exists somewhere)
- Verify no duplication remains (each piece of information appears exactly once)
- Verify links are valid (all cross-references point to existing files)
- Verify AGENTS.md is shorter (target: ~450 lines, down from 715)

### Test scenarios

1. **Information preservation**: Compare original AGENTS.md content against new structure. Every rule, constraint, and pointer must exist somewhere in the new structure.
2. **No duplication**: Search for key phrases (e.g., "lib/api 分层", "Docker 开发环境") and verify they appear only once.
3. **Link validation**: Run a link checker on AGENTS.md to verify all cross-references (e.g., "详见 backend/docs/development-guide.md") point to existing files.
4. **Length check**: Verify AGENTS.md is ≤500 lines (target ~450, with some tolerance).
5. **Rule quality**: Verify non-obvious "禁止" rules have "why" explanations.

### Prior art

- The existing docs/agents/domain.md already references CONTEXT.md and ADRs
- The existing development-guide.md already has code examples for infrastructure usage
- The existing examples/ directories already have standalone code patterns

## Out of Scope

- **CONTEXT.md content**: The file will be created and gitignored, but its content is out of scope. It will be populated lazily as domain terms crystallize during future work.
- **Module catalog**: AGENTS.md will not include a business description of each module. The module names are self-explanatory to the team, and README.md already covers the business context.
- **development-guide.md location**: The file stays at backend/docs/development-guide.md. Moving it to repo root would blur the backend/frontend boundary.
- **Docker.md**: The Docker instructions stay in AGENTS.md because they're essential for frontend development and not duplicated elsewhere.

## Further Notes

### Final documentation structure

```
AGENTS.md                          # Rules + constraints (~450 lines)
backend/docs/
├── development-guide.md           # Narrative how-to (absorbs development.md)
├── AI_FILL_GUIDE.md               # (unchanged)
├── PHASE1_REGULATORY_TRACKER.md   # (unchanged)
├── database-setup.md              # (unchanged)
└── training/                      # (unchanged)
examples/
├── module-structure.md            # Module directory structure
├── commands.md                    # Common commands
├── migration-compression.md       # One-time migration procedure
├── server-component-pattern.md    # Frontend pattern
└── server-actions.md              # Frontend pattern
CONTEXT.md                         # (new, gitignored, initially empty)
```

### Files deleted

- backend/docs/architecture.md (redundant)

### Files merged

- backend/docs/development.md → backend/docs/development-guide.md

### Files moved

- backend/examples/module-structure.md → examples/module-structure.md
- backend/examples/commands.md → examples/commands.md
- backend/docs/migration-baseline.md → examples/migration-compression.md
- frontend/examples/server-component-pattern.md → examples/server-component-pattern.md
- frontend/examples/server-actions.md → examples/server-actions.md

### AGENTS.md updates

- Add "why" to ~10 non-obvious "禁止" rules
- Merge two API diagrams into one canonical version
- Add links to development-guide.md for code examples
- Update references from backend/examples/ and frontend/examples/ to examples/

