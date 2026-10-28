'use client'

import { BoundaryResult } from '@/components/common/BoundaryResult'

/**
 * 模块级无权限页（模块 `layout.tsx` 守卫不通过时渲染）。
 *
 * 为什么单独做成客户端组件：模块 `layout.tsx` 是 RSC（要在服务端 await 权限判定），
 * 而 antd 组件必须在客户端渲染 —— 把 antd 收在这里，两边都能用。
 */
export default function ModuleNoAccess({ moduleName }: { moduleName: string }) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-6">
      <BoundaryResult
        kind="forbidden"
        title={`无访问${moduleName}的权限`}
        subTitle={`访问${moduleName}需要「访问${moduleName}」权限，请联系管理员为你的账号分配。`}
      />
    </div>
  )
}
