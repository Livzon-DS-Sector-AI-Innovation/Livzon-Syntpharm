# 51 — Add React Hooks rules to AGENTS.md, create examples, and update audit plan

**What to build:** Add React Hooks and React Compiler guidelines to AGENTS.md with a reference to detailed examples in `examples/react-hooks-pattern.md`, and update the audit plan to verify compliance. This ensures developers write React Compiler-compatible code from the start.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## AGENTS.md Updates

Add a new section "## React Hooks 与 React Compiler" under the "前端 — Next.js / TypeScript" section, positioned after "## 类型系统" and before "## 禁止修改的文件".

The section should:
- State that React Compiler is enabled (`reactCompiler: true`)
- List the 5 key rules concisely:
  1. 数据获取: 使用 React Query，禁止 useEffect + setState
  2. 派生状态: 使用 useMemo，禁止 useEffect + setState
  3. useEffect 依赖: 必须完整，禁止省略或抑制
  4. 不可变状态: 禁止直接修改，使用展开运算符
  5. 依赖稳定化: 使用 useCallback/useRef
- Reference `examples/react-hooks-pattern.md` for detailed examples and explanations

## Examples File

Create `examples/react-hooks-pattern.md` with:

### 1. 数据获取模式
- 正确示例: useQuery with queryKey and queryFn
- 错误示例: useEffect + setState for data fetching
- 原因说明: React Compiler 无法优化包含 setState 的 effect

### 2. 派生状态模式
- 正确示例: useMemo for computed values
- 错误示例: useEffect + setState for derived state
- 原因说明: 派生状态应该在渲染期间计算

### 3. useEffect 依赖管理
- 正确示例: complete dependency array
- 错误示例: missing dependencies
- 稳定化模式: useCallback and useRef examples
- 原因说明: 完整的依赖数组确保 effect 在正确时机运行

### 4. 不可变状态更新
- 正确示例: spread operator for arrays and objects
- 错误示例: direct mutation (push, property assignment)
- 原因说明: React Compiler 依赖不可变性检测变化

## Audit Plan Updates

Add a new category "## 16. React Hooks 与 React Compiler" to `docs/ai-audit-plan.md`.

The audit category should include:

### Audit type
Full audit

### Rules (from AGENTS.md)
Reference the 5 rules added to AGENTS.md

### Directories to inspect
- `frontend/src/app/`
- `frontend/src/components/`
- `frontend/src/actions/`

### Questions
1. Are there `useEffect` hooks that call `setState` to fetch data? (Should use React Query)
2. Are there `useEffect` hooks that compute derived state? (Should use useMemo)
3. Do all `useEffect` hooks have complete dependency arrays?
4. Are there any `// eslint-disable-next-line react-hooks/exhaustive-deps` comments?
5. Are there direct state mutations (array.push, object.property = value)?
6. Are `useCallback` or `useRef` used appropriately to stabilize dependencies?

### Output format
Standard audit output format with findings table

## Acceptance Criteria

- [ ] Section added to AGENTS.md under "前端 — Next.js / TypeScript"
- [ ] Section positioned after "## 类型系统" and before "## 禁止修改的文件"
- [ ] AGENTS.md section references `examples/react-hooks-pattern.md`
- [ ] `examples/react-hooks-pattern.md` created with all 4 pattern categories
- [ ] Each pattern includes correct/incorrect examples and explanations
- [ ] New audit category 16 added to docs/ai-audit-plan.md
- [ ] Audit category includes all 6 questions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes
