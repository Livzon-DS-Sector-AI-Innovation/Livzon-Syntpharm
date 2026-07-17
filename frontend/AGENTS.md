# 前端 AI 编程规范

本文档定义 AI 编码助手必须遵守的规则。违反这些规则会导致代码被拒绝。

原料药厂管理系统前端，Next.js 16 App Router，TypeScript。后端为独立的 Python FastAPI 服务。

UI 和组件样式必须遵守 [DESIGN.md](DESIGN.md)。使用 antd 组件时，用 Context7 查询最新参数文档。

## 技术栈

- **Next.js 16** + React 19 + TypeScript + Tailwind CSS
- **组件库**：Ant Design V6（antd）
- **客户端状态**：Zustand（`stores/` 目录）
- **服务端数据**：Server Component 通过 `lib/api/server/` 获取数据
- **客户端数据**：React Query（`@tanstack/react-query`）
- **表单**：Ant Design Form（默认）
- **数据边界校验**：Zod（选择性使用）


## 表单与数据校验

### 表单系统

前端表单默认使用 **Ant Design Form**。使用 `Form.Item` 的 `rules` 属性进行简单的 UI 校验和用户反馈。

**禁止**：在没有明确理由的情况下，将现有的 Ant Design Form 迁移到 React Hook Form 或 Zod。

### Zod 的使用场景

Zod 仅用于**数据边界**的运行时校验，不用于普通表单。适用场景：

1. **Server Actions 的复杂输入**：当 Server Action 接收复杂、嵌套或不可信的输入时
2. **Excel/CSV 文件导入**：解析用户上传的文件时，校验数据结构
3. **LLM 结构化输出**：解析 LLM 返回的 JSON 数据时
4. **环境变量校验**：应用启动时校验关键环境变量
5. **复杂的数据转换**：跨系统数据转换前的校验

**不适用**：普通的表单字段校验（用 Ant Design Form rules）、简单的 API 响应处理（用 TypeScript 类型）。

### 示例：Server Action 中使用 Zod

```typescript
import { z } from 'zod'

const CreateBatchSchema = z.object({
  product_id: z.string().uuid(),
  batch_no: z.string().min(1, '批号不能为空'),
  quantity: z.number().int().positive('产量必须大于0'),
  produced_at: z.string().datetime(),
})

export async function createBatch(data: unknown) {
  'use server'
  const validated = CreateBatchSchema.parse(data)
  // validated 现在是类型安全的
  // ... 调用后端 API
}
```

### 示例：Excel 导入校验

```typescript
import { z } from 'zod'

const TrainingRecordSchema = z.object({
  employee_name: z.string(),
  training_date: z.string(),
  score: z.number().min(0).max(100),
})

export async function importTrainingRecords(file: File) {
  const rows = await parseExcel(file)
  const validated = z.array(TrainingRecordSchema).parse(rows)
  // validated 是类型安全的数组
  // ... 处理导入数据
}
```

后端 FastAPI/Pydantic 校验仍然是 API 输入的最终来源。

## 目录结构

```
src/
├── app/(dashboard)/<模块>/   # 路由页面（Server Component，只做数据获取和布局）
├── components/<模块>/        # 该模块所有 UI 组件
├── components/shared/        # 公共组件（禁止修改，需新增找架构负责人）
├── actions/<模块>.ts         # 该模块所有写操作（Server Actions）
├── stores/<模块>.ts          # 该模块客户端状态
├── types/<模块>.ts           # 该模块 TypeScript 类型
├── lib/                      # 基础设施（只允许修改自己负责模块的部分）
│   └── api/
│       ├── client/           # 浏览器只读 API（GET/list/search/detail）
│       └── server/           # 服务器端 API（Server Component / Server Action）
└── proxy.ts                  # API 代理（禁止修改）
```
## Server Component vs Client Component

`page.tsx` 默认是 Server Component，**不加** `'use client'`。

**必须加 `'use client'` 的情况**：
- 使用了 `useState`、`useEffect`、`useContext` 等 React Hooks
- 使用了浏览器 API（`window`、`document`、`localStorage`）
- 使用了事件处理器（`onClick`、`onChange`、`onSubmit`）
- 使用了 antd 的 `App.useApp()` hook
- 使用了 Zustand store
- **直接在页面中使用了 antd 组件**（Card、Row、Col、Button 等）

**不需要 `'use client'` 的情况**：
- 页面只是导入并渲染一个 Client Component
- 导出了 `generateMetadata` 函数（Server Component 专属功能）
- 页面是 `async function` 并且只是获取数据后传递给 Client 组件

**判断标准**：
- 如果页面文件中有 JSX 使用了 antd 组件 → 需要 `'use client'`
- 如果页面只是 `<ClientComponent />` → 不需要 `'use client'`

Client 组件放在 `components/<模块>/` 里，`page.tsx` 只负责获取数据然后传给 Client 组件。

详见 [examples/server-component-pattern.md](examples/server-component-pattern.md)。

**Barrel 文件（index.ts）规则**：当 Server Component 从 `components/<模块>/index.ts` 导入 Client 组件时，如果导出的组件使用了 **Zustand store**、**React Context** 或其他 Context-based 状态管理，barrel 文件**必须**加 `'use client'`。原因：Next.js 构建时会在服务端评估所有导入，如果 barrel 文件导出的组件使用了 `createContext()`（如 zustand 的 `create()`），服务端无法执行，导致构建失败：`TypeError: createContext is not a function`。示例：

```typescript
// src/components/energy/index.ts
'use client'  // ← 必须加，因为导出的组件使用 useEnergyStore

export { AlertsPageClient } from './AlertsPageClient'
export { DevicesPageClient } from './DevicesPageClient'
```

如果 barrel 文件导出的组件只使用基本 hooks（`useState`、`useEffect`），理论上不需要 `'use client'`，但**最佳实践**是所有 `components/<模块>/index.ts` 统一加 `'use client'`，避免未来添加 zustand 导入时构建失败。

### 动态渲染

Server Component 页面如果通过 `actions/` 获取运行时数据（调用后端 API），**必须**在页面顶部添加：

```typescript
export const dynamic = 'force-dynamic'
```

原因：Next.js 默认尝试静态预渲染 Server Component，但后端 API 在构建时不可用，会导致构建失败或返回过期数据。只有纯静态页面（不调用后端 API）才不需要此配置。

## 写操作必须用 Server Actions

所有 POST/PUT/DELETE 操作写在 `actions/` 目录。**禁止**在 Client 组件里直接 fetch 写接口。

**例外：** 需要流式响应（SSE/ReadableStream）或上传进度追踪时，允许在 `lib/api/client/` 中使用直接 fetch。

原因：Server Actions 自动处理 CSRF、revalidation 和错误边界，客户端 fetch 写操作会绕过这些安全机制。

详见 [examples/server-actions.md](examples/server-actions.md)。

## 模块边界

**禁止**跨模块直接 import 组件内部文件。如果需要用其他模块的东西，只能从该模块的 `index.ts` 导入：

```typescript
✗ import { BatchForm } from '@/components/production/BatchForm'
✓ import { BatchTable } from '@/components/production'
```

## 命名规范

- 组件文件：PascalCase（`BatchTable.tsx`）
- 非组件文件：camelCase（`useBatch.ts`、`batchApi.ts`）
- 类型名：PascalCase（`BatchStatus`、`CreateBatchInput`）
- Server Action 函数：动词开头（`createBatch`、`updateBatch`、`submitApproval`）
- API 请求函数：以 `fetch` 开头（`fetchBatches`、`fetchBatchById`）

## 新增页面的步骤

1. 在 `app/(dashboard)/<模块>/` 下新建目录和 `page.tsx`
2. `page.tsx` 里 fetch 数据，传给 `components/<模块>/` 里的组件
3. 组件写在 `components/<模块>/` 里，需要交互的加 `'use client'`
4. 如果有写操作，写在 `actions/<模块>.ts` 里
5. 类型定义更新到 `types/<模块>.ts`
6. 新增的对外组件记得在 `components/<模块>/index.ts` 里导出

## API 调用架构

### 路由转发

客户端代码使用相对路径 `/api/v1/...`，由 `src/proxy.ts` 转发到后端。服务器端代码使用 `API_BASE_URL` 环境变量。

```typescript
// 客户端：相对路径（自动代理到后端）
const response = await fetch('/api/v1/quality/cpv/products')

// 服务器端：环境变量（Docker 内部网络）
const API_BASE = process.env.API_BASE_URL || 'http://dazah-backend-app-1:8000'
const response = await fetch(`${API_BASE}/api/v1/production/batches`)
```

**禁止**：
- 硬编码后端地址或暴露后端端口
- 使用 `NEXT_PUBLIC_API_BASE_URL`
- 硬编码绝对文件路径（如 `D:/xxx`、`C:/xxx`）。必须使用相对路径或配置项
- 硬编码 `localhost:3000` 或其他固定地址生成跳转/分享链接。必须使用环境变量或运行时动态获取（如 `window.location.origin`

### proxy.ts 规则

`src/proxy.ts` 是 Next.js 请求中间层，仅负责 API 转发、流式响应处理和轻量登录状态判断。当前项目使用 Turbopack，因此不使用 `next.config.js` 的 `rewrites()`，而通过 `proxy.ts` 转发 `/api/v1/*`。

API 转发使用 `fetch` 和 `new NextResponse` 进行透明传递，不使用 `NextResponse.rewrite`。

**允许：**

* 将 `/api/v1/*` 转发到后端
* 透传 HTTP method、body、headers 和 cookies
* 保持流式响应和 SSE 行为
* 仅判断 session cookie 或 token 是否存在
* 将明显未登录的页面请求重定向到 `/login`
* 通过 `matcher` 排除公开路由和静态资源

**禁止：**

* 调用数据库或 API 验证 token
* 角色、权限或模块访问判断
* 业务规则和模块专属逻辑
* 请求或响应数据转换
* LLM 调用
* 审计日志写入
* 数据库访问
* 将 `proxy.ts` 的检查视为正式授权结果

真实身份验证、权限判断、业务规则、审计和数据访问必须由 FastAPI 后端执行。Server Actions 可以调用后端，但不能替代后端授权。

### 新增 API 调用

1. **客户端调用**：在 `lib/api/client/<模块>.ts` 中使用相对路径 `/api/v1/...`
2. **服务器端调用**：在 `lib/api/server/<模块>.ts` 中使用 `API_BASE_URL` 环境变量
3. **写操作**：在 `actions/<模块>.ts` 中调用 `lib/api/server/` 的函数，不要直接 fetch

## 类型系统

### lib/api 分层

```
src/lib/api/client/   # 浏览器 GET/list/search/detail，使用 /api/v1/...
src/lib/api/server/   # Server Component / Server Action 使用，使用 API_BASE_URL
src/actions/          # create/update/delete/upload/import/export
```

这防止了服务端代码被意外导入到客户端组件中。


### API 类型来源

所有 API 相关的类型（请求参数、响应数据）**必须**从 `@/types/generated/schema` 导入。**禁止**手写 API 类型。

原因：OpenAPI spec 是前后端契约的唯一来源，手写类型会与后端漂移，导致运行时错误。

```typescript
✗ export async function updateRoute(id: string, data: { name?: string; status?: string })
✓ import type { RouteUpdate } from '@/types/generated/schema'
  export async function updateRoute(id: string, data: RouteUpdate)
```

### API 调用层级

```
src/types/generated/     ← 自动生成，禁止编辑
src/lib/api/client/*.ts     ← 浏览器 GET/list/search/detail，使用 /api/v1/...
src/lib/api/server/*.ts     ← Server Component / Server Action，使用 API_BASE_URL
src/actions/*.ts         ← Server Actions，调用 lib/api
```

- **GET / list / search / detail**：浏览器调用放在 `src/lib/api/client/`，服务器调用放在 `src/lib/api/server/`
- **create / update / delete / upload**：必须通过 Server Actions

### 类型检查

如果后端 API 发生变化，前端必须重新生成类型：

```bash
# 1. 在 backend 仓库导出最新 spec
cd ../dazah-backend && uv run python scripts/export_openapi.py

# 2. 在 frontend 仓库重新生成类型
pnpm generate:api
```

CI 会检查生成的类型是否与后端同步，不同步的 PR 无法合并。

生成脚本：`scripts/generate-api.mjs`

生成文件：
- `src/types/generated/schema.ts` — 所有 API 类型定义（需提交到仓库）
- `src/types/generated/openapi.json` — OpenAPI spec 快照

## 禁止修改的文件

以下文件只有架构负责人可以修改，如有需求提 PR 说明原因：
- `src/proxy.ts`
- `src/components/shared/` 下所有文件
- `src/hooks/usePermission.ts`

## Docker 开发环境

两种 docker-compose 配置：
- `docker-compose.yml` — 生产构建（`next build` + `next start`，无热更新）
- `docker-compose.dev.yml` — 开发构建（`pnpm dev`，有热更新，推荐日常开发使用）

开发时**必须**使用：

```bash
docker compose -f docker-compose.dev.yml up -d --build
```
