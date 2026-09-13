# React Hooks 与 React Compiler 模式

本文档提供 React Compiler 兼容代码的详细示例和说明。React Compiler 已启用（`reactCompiler: true`），需要遵循特定的编码模式以确保编译器能够正确优化。

## 1. 数据获取模式

### 正确示例：使用 React Query

```typescript
// ✅ 正确：使用 useQuery 获取数据
import { useQuery } from '@tanstack/react-query'

function UserProfile({ userId }: { userId: string }) {
  const { data: user, isLoading, error } = useQuery({
    queryKey: ['user', userId],
    queryFn: () => fetchUser(userId),
  })

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error loading user</div>
  
  return <div>{user.name}</div>
}
```

### 错误示例：useEffect + setState

```typescript
// ❌ 错误：使用 useEffect 获取数据
function UserProfile({ userId }: { userId: string }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setIsLoading(true)
    fetchUser(userId)
      .then(setUser)
      .catch(setError)
      .finally(() => setIsLoading(false))
  }, [userId]) // React Compiler 无法优化这个 effect

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error loading user</div>
  
  return <div>{user.name}</div>
}
```

### 原因说明

React Compiler 无法优化包含 `setState` 的 effect。当 effect 中调用 `setState` 时，编译器无法确定何时应该重新执行该 effect，也无法安全地进行优化。React Query 提供了内置的缓存、重试、和依赖追踪机制，是数据获取的标准方式。

## 2. 派生状态模式

### 正确示例：使用 useMemo

```typescript
// ✅ 正确：使用 useMemo 计算派生状态
function ProductList({ products, filter }: { products: Product[], filter: string }) {
  const filteredProducts = useMemo(() => {
    return products.filter(p => p.name.includes(filter))
  }, [products, filter])

  const totalValue = useMemo(() => {
    return filteredProducts.reduce((sum, p) => sum + p.price, 0)
  }, [filteredProducts])

  return (
    <div>
      <div>Total: ${totalValue}</div>
      {filteredProducts.map(p => <ProductCard key={p.id} product={p} />)}
    </div>
  )
}
```

### 错误示例：useEffect + setState

```typescript
// ❌ 错误：使用 useEffect 计算派生状态
function ProductList({ products, filter }: { products: Product[], filter: string }) {
  const [filteredProducts, setFilteredProducts] = useState([])
  const [totalValue, setTotalValue] = useState(0)

  useEffect(() => {
    const filtered = products.filter(p => p.name.includes(filter))
    setFilteredProducts(filtered)
    
    const total = filtered.reduce((sum, p) => sum + p.price, 0)
    setTotalValue(total)
  }, [products, filter]) // 额外的渲染周期

  return (
    <div>
      <div>Total: ${totalValue}</div>
      {filteredProducts.map(p => <ProductCard key={p.id} product={p} />)}
    </div>
  )
}
```

### 原因说明

派生状态应该在渲染期间计算，而不是通过 effect 异步更新。使用 `useEffect` + `setState` 会导致额外的渲染周期：第一次渲染使用旧值，effect 运行后触发第二次渲染使用新值。`useMemo` 在渲染期间同步计算值，避免了这个问题，也允许 React Compiler 进行优化。

## 3. useEffect 依赖管理

### 正确示例：完整的依赖数组

```typescript
// ✅ 正确：完整的依赖数组
function OrderDetails({ orderId }: { orderId: string }) {
  const [order, setOrder] = useState(null)
  
  const fetchOrder = useCallback(async () => {
    const data = await api.getOrder(orderId)
    setOrder(data)
  }, [orderId])

  useEffect(() => {
    fetchOrder()
  }, [fetchOrder]) // 依赖 fetchOrder，而 fetchOrder 依赖 orderId

  return <div>{order?.id}</div>
}
```

### 错误示例：缺失依赖

```typescript
// ❌ 错误：缺失依赖
function OrderDetails({ orderId }: { orderId: string }) {
  const [order, setOrder] = useState(null)
  
  const fetchOrder = async () => {
    const data = await api.getOrder(orderId)
    setOrder(data)
  }

  useEffect(() => {
    fetchOrder() // ESLint 警告：缺少 fetchOrder 依赖
  }, []) // 缺失依赖会导致闭包捕获旧值

  return <div>{order?.id}</div>
}
```

### 稳定化模式：useCallback 和 useRef

```typescript
// ✅ 使用 useCallback 稳定函数引用
const handleSubmit = useCallback(async (data: FormData) => {
  await api.submit(data)
}, []) // 无外部依赖，函数引用稳定

// ✅ 使用 useRef 存储不需要触发重新渲染的值
function SearchInput({ onSearch }: { onSearch: (query: string) => void }) {
  const [query, setQuery] = useState('')
  const timeoutRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    // 清除之前的 timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    
    // 设置新的 timeout
    timeoutRef.current = setTimeout(() => {
      onSearch(query)
    }, 300)
    
    // 清理函数
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [query, onSearch])

  return <input value={query} onChange={e => setQuery(e.target.value)} />
}
```

### 原因说明

完整的依赖数组确保 effect 在正确时机运行。缺失依赖会导致闭包捕获旧值，产生难以追踪的 bug。使用 `useCallback` 稳定函数引用，使用 `useRef` 存储不需要触发重新渲染的值，这些都是 React Compiler 能够安全优化的模式。

## 4. 不可变状态更新

### 正确示例：使用展开运算符

```typescript
// ✅ 正确：不可变更新数组
function TodoList() {
  const [todos, setTodos] = useState<Todo[]>([])

  const addTodo = (todo: Todo) => {
    setTodos(prev => [...prev, todo]) // 创建新数组
  }

  const updateTodo = (id: string, updates: Partial<Todo>) => {
    setTodos(prev => prev.map(todo => 
      todo.id === id ? { ...todo, ...updates } : todo // 创建新对象
    ))
  }

  const removeTodo = (id: string) => {
    setTodos(prev => prev.filter(todo => todo.id !== id)) // 创建新数组
  }

  return <div>...</div>
}

// ✅ 正确：不可变更新对象
function UserProfile() {
  const [user, setUser] = useState<User>({ name: '', email: '' })

  const updateName = (name: string) => {
    setUser(prev => ({ ...prev, name })) // 创建新对象
  }

  const updateEmail = (email: string) => {
    setUser(prev => ({ ...prev, email })) // 创建新对象
  }

  return <div>...</div>
}
```

### 错误示例：直接修改状态

```typescript
// ❌ 错误：直接修改数组
function TodoList() {
  const [todos, setTodos] = useState<Todo[]>([])

  const addTodo = (todo: Todo) => {
    todos.push(todo) // 直接修改数组
    setTodos(todos) // React 不会检测到变化
  }

  const updateTodo = (id: string, updates: Partial<Todo>) => {
    const todo = todos.find(t => t.id === id)
    if (todo) {
      Object.assign(todo, updates) // 直接修改对象
      setTodos(todos) // React 不会检测到变化
    }
  }

  return <div>...</div>
}

// ❌ 错误：直接修改对象
function UserProfile() {
  const [user, setUser] = useState<User>({ name: '', email: '' })

  const updateName = (name: string) => {
    user.name = name // 直接修改对象
    setUser(user) // React 不会检测到变化
  }

  return <div>...</div>
}
```

### 原因说明

React Compiler 依赖不可变性检测变化。当直接修改状态时，React 无法检测到变化，因为对象引用没有改变。这会导致组件不重新渲染，或者 React Compiler 无法正确优化代码。使用展开运算符、`map`、`filter` 等方法创建新对象/数组，确保每次更新都产生新的引用。

## 总结

遵循这些模式确保代码与 React Compiler 兼容：

1. **数据获取**：使用 React Query，避免 useEffect + setState
2. **派生状态**：使用 useMemo，避免 useEffect + setState
3. **依赖管理**：保持完整的依赖数组，使用 useCallback/useRef 稳定依赖
4. **不可变更新**：使用展开运算符和数组方法，避免直接修改状态

这些模式不仅使代码与 React Compiler 兼容，还能提高代码质量、可维护性和性能。
