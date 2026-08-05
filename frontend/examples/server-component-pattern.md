# Server Component 模式示例

## Server Component（获取数据）

```tsx
// app/(dashboard)/production/page.tsx（Server Component）
export default async function Page() {
  const data = await fetch(`${process.env.API_BASE_URL}/production/batches`, {
    headers: { Authorization: `Bearer ${await getServerToken()}` },
    next: { revalidate: 60 }
  }).then(r => r.json())

  return <BatchTable initialData={data} />  // BatchTable 是 Client 组件
}
```

## Client 组件条件

只有以下情况才加 `'use client'`：
- 用了 useState / useEffect / 事件处理器
- 用了浏览器 API
- 用了 Zustand store

Client 组件放在 `components/<模块>/` 里，`page.tsx` 只负责拿数据然后传给 Client 组件。

## Barrel 文件 (index.ts)

导出使用 Zustand store 或 React Context 的组件时，barrel 必须加 `'use client'`（否则构建报错 `TypeError: createContext is not a function`）。其他 barrel 建议统一加 `'use client'` 以防未来引入 store 导入时构建失败。

```typescript
// frontend/src/components/energy/index.ts
'use client'

export { AlertsPageClient } from './AlertsPageClient'
export { DevicesPageClient } from './DevicesPageClient'
```
