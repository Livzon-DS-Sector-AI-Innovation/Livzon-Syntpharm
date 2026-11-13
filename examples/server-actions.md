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

## `'use server'` 文件中的类型定义

类型集中放在 `types/<模块>.ts`，不要从 `'use server'` 文件导出类型。

- **禁止** `export type { ... }` 再导出：历史上曾触发 Turbopack Server Actions loader 的运行时错误。
- **不建议**定义并导出 `export type` / `export interface`：容易与 `types/` 重复并造成类型漂移。例外：仅在本 action 文件内使用、且未在 `types/` 重复定义的 interface 可以保留（interface 编译后被擦除，不会造成运行时错误）。

### ✗ 错误

```ts
// src/actions/users.ts
'use server'
import type { UserManagementItem } from '@/types/users'
export type { UserManagementItem }    // 禁止：再导出类型
```

```ts
// src/actions/users.ts
'use server'
export type UserManagementItem = any // 不建议：应放到 types/
```

```ts
// src/actions/users.ts
'use server'
export interface AgentSkill { ... }  // 不建议：除非仅本文件使用且 types/ 未重复定义
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

## API 调用

客户端使用相对路径（由 `src/proxy.ts` 转发到后端），服务器端使用 `API_BASE_URL` 环境变量：

```typescript
// 客户端：相对路径（自动代理到后端）
const response = await fetch('/api/v1/quality/cpv/products')

// 服务器端：环境变量（Docker 内部网络）
const API_BASE = process.env.API_BASE_URL || 'http://backend:8000'
const response = await fetch(`${API_BASE}/api/v1/production/batches`)
```

**禁止**：
- 硬编码后端地址或暴露后端端口
- 使用 `NEXT_PUBLIC_API_BASE_URL`
- 硬编码 `localhost:3000` 或其他固定地址生成跳转/分享链接
