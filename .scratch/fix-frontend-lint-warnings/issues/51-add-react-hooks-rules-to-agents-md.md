# 51 — Add React Hooks rules to AGENTS.md and update audit plan

**What to build:** Add comprehensive React Hooks and React Compiler guidelines to AGENTS.md, and update the audit plan to verify compliance. This ensures developers write React Compiler-compatible code from the start.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## AGENTS.md Updates

Add a new section "## React Hooks 与 React Compiler" under the "前端 — Next.js / TypeScript" section, positioned after "## 类型系统" and before "## 禁止修改的文件".

The section should cover:

### 1. React Compiler 启用说明
- State that React Compiler is enabled (`reactCompiler: true` in next.config.ts)
- Explain that this requires specific coding patterns for automatic optimization

### 2. 数据获取规则
- **禁止**: 在 `useEffect` 中调用 `setState` 来获取数据
- **必须**: 使用 React Query 的 `useQuery` 和 `useMutation`
- 原因: React Compiler 无法优化包含 `setState` 的 effect
- 提供正确示例:
  ```typescript
  const { data, isLoading, error } = useQuery({
    queryKey: ['users', userId],
    queryFn: () => fetchUser(userId),
  })
  ```
- 提供错误示例:
  ```typescript
  const [data, setData] = useState(null)
  useEffect(() => {
    fetchUser(userId).then(setData)
  }, [userId])
  ```

### 3. 派生状态规则
- **禁止**: 使用 `useEffect` + `setState` 计算派生状态
- **必须**: 使用 `useMemo`
- 提供正确示例:
  ```typescript
  const filteredItems = useMemo(
    () => items.filter(item => item.active),
    [items]
  )
  ```
- 提供错误示例:
  ```typescript
  const [filteredItems, setFilteredItems] = useState([])
  useEffect(() => {
    setFilteredItems(items.filter(item => item.active))
  }, [items])
  ```

### 4. useEffect 依赖规则
- 依赖数组**必须**包含所有在 effect 内部使用的变量
- **禁止**: 省略依赖
- **禁止**: 使用 `// eslint-disable-next-line react-hooks/exhaustive-deps` 抑制警告
- 如果依赖变化太频繁，使用 `useCallback` 或 `useRef` 稳定化

### 5. 不可变状态更新规则
- **禁止**: 直接修改状态（如 `items.push(newItem)`、`user.name = newName`）
- **必须**: 使用不可变更新模式
- 提供正确示例:
  ```typescript
  setItems([...items, newItem])
  setUser({ ...user, name: newName })
  ```
- 提供错误示例:
  ```typescript
  items.push(newItem)
  user.name = newName
  ```
- 原因: React Compiler 依赖不可变性来检测状态变化并优化重新渲染

## Audit Plan Updates

Add a new category "## 16. React Hooks 与 React Compiler" to `docs/ai-audit-plan.md`.

The audit category should include:

### Audit type
Full audit

### Rules (from AGENTS.md)
Reference the 5 rules added to AGENTS.md (数据获取, 派生状态, useEffect 依赖, 不可变状态更新)

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
- [ ] All 5 subsections included with correct/incorrect examples
- [ ] New audit category 16 added to docs/ai-audit-plan.md
- [ ] Audit category includes all 6 questions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes
