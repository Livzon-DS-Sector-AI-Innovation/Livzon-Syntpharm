# Server Actions 示例

所有 POST/PUT/DELETE 操作写在 `actions/` 目录，不要在 Client 组件里直接 fetch 写接口。

## 基本示例

```ts
// actions/production.ts
'use server'
export async function createBatch(data: CreateBatchInput) {
  const token = await getServerToken()
  const res = await fetch(`${process.env.API_BASE_URL}/production/batches`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  if (!res.ok) throw new Error('创建批次失败')
  revalidatePath('/production')
}
```

## `'use server'` 文件禁止 `export type` 和 `export interface`

Turbopack 的 Server Actions loader 无法正确剥离 `export type`、`export type { ... }` 和 `export interface` 语句，会导致运行时 `ReferenceError: X is not defined`。类型定义必须放在 `types/<模块>.ts` 中。

### ✗ 错误

```ts
// src/actions/users.ts
'use server'
import type { UserManagementItem } from '@/types/users'
export type { UserManagementItem }    // 运行时崩溃
```

```ts
// src/actions/users.ts
'use server'
export type UserManagementItem = any // 运行时崩溃
```

```ts
// src/actions/users.ts
'use server'
export interface AgentSkill { ... }  // 运行时崩溃
```

### ✓ 正确

类型定义放在 `types/<模块>.ts` 中：

```ts
// src/types/users.ts
export interface UserManagementItem {
  id: string
  username: string
  role: string
  status: string
}
```

`actions/<模块>.ts` 只导入类型用作参数/返回值注解，只导出 Server Action 函数：

```ts
// src/actions/users.ts
'use server'
import type { UserManagementItem } from '@/types/users'
import { createUser as createUserServer } from '@/lib/api/server/users'

export async function createUser(data: UserManagementItem) {
  const token = await getAuthToken()
  return createUserServer(data, token) as Promise<UserManagementItem>
}
```

客户端分别从 `actions/` 导入函数，从 `types/` 导入类型：

```ts
// src/components/settings/UserManagementClient.tsx
'use client'
import { createUser } from '@/actions/users'
import type { UserManagementItem } from '@/types/users'
```
