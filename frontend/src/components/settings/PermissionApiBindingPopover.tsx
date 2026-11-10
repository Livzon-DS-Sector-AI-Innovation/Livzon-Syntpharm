'use client'

import { useState } from 'react'
import { Popover, Spin } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { fetchPermissionApiBindings } from '@/actions/permission'

/** 请求方法配色：查询蓝、新增绿、修改橙、删除红。 */
const METHOD_COLORS: Record<string, string> = {
  GET: '#0075de',
  POST: '#1aae39',
  PUT: '#dd5b00',
  PATCH: '#dd5b00',
  DELETE: '#e03131',
}

interface PermissionApiBindingPopoverProps {
  /** 权限码，如 safety:accident:read */
  code: string
  /** 该权限码绑定的接口数量，为 0 时不发起请求、只显示「未绑定接口」入口 */
  count: number
}

function methodStyle(method: string): { color: string; backgroundColor: string } {
  const color = METHOD_COLORS[method.toUpperCase()] ?? '#787671'
  return { color, backgroundColor: `${color}14` }
}

/**
 * 浮层顶部的权限码。
 * 权限树上不显示英文码，这里是开发/后端对照接口时唯一的锚点，所以每个浮层都带上。
 */
function CodeLine({ code }: { code: string }) {
  return (
    <div className="mb-2 border-b border-[var(--color-hairline)] pb-2">
      <code className="break-all font-mono text-[11px] text-[var(--color-steel)]">{code}</code>
    </div>
  )
}

function BindingList({ code, open }: { code: string; open: boolean }) {
  const { data: items = [], isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['permission-api-bindings', code],
    queryFn: () => fetchPermissionApiBindings(code),
    // 仅在浮层打开时请求：权限树本身不携带接口明细
    enabled: open,
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <div className="flex h-16 items-center justify-center">
        <Spin size="small" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center gap-2 py-5">
        <span className="text-[12px] text-[var(--color-error)]">接口清单加载失败</span>
        <button
          type="button"
          onClick={() => void refetch()}
          className="cursor-pointer text-[12px] text-[var(--color-primary)] hover:underline disabled:cursor-not-allowed"
          disabled={isFetching}
        >
          重试
        </button>
      </div>
    )
  }

  if (items.length === 0) {
    return <div className="py-6 text-center text-[12px] text-[var(--color-steel)]">该权限码当前未绑定任何接口</div>
  }

  return (
    <div>
      <div className="mb-2 text-[12px] text-[var(--color-steel)]">该权限码绑定的接口</div>
      <ul className="max-h-[240px] space-y-1 overflow-auto pr-1">
        {items.map((item) => (
          <li key={`${item.method}-${item.route_template}`} className="flex items-start gap-2">
            <span
              className="mt-[3px] inline-flex w-[52px] shrink-0 justify-center rounded px-1 py-[1px] text-[11px] font-medium"
              style={methodStyle(item.method)}
            >
              {item.method}
            </span>
            <code className="break-all font-mono text-[12px] leading-5 text-[var(--color-charcoal)]">
              {item.route_template}
            </code>
          </li>
        ))}
      </ul>
    </div>
  )
}

/**
 * 权限项的接口清单浮层：点击「N 个接口」才请求后端。
 * 未绑定接口的权限同样走浮层，保证权限码始终有一个可查看的入口。
 * 说明文案由后端模板生成（见 service/description.py），这里只负责接口层面的事实。
 */
export default function PermissionApiBindingPopover({ code, count }: PermissionApiBindingPopoverProps) {
  const [open, setOpen] = useState(false)

  if (count === 0) {
    return (
      <Popover
        open={open}
        onOpenChange={setOpen}
        trigger="click"
        placement="rightTop"
        content={
          <div className="w-[320px] max-w-[76vw]">
            <CodeLine code={code} />
            <div className="py-2 text-[12px] text-[var(--color-steel)]">
              该权限暂未绑定任何接口，勾选后不会立即产生实际权限。
            </div>
          </div>
        }
      >
        <button
          type="button"
          className="ml-2 shrink-0 cursor-pointer border-0 bg-transparent p-0 text-[12px] text-[var(--color-muted)] hover:text-[var(--color-steel)] hover:underline"
          // 阻止冒泡：点接口计数不应触发树节点选中 / 勾选
          onClick={(event) => event.stopPropagation()}
          title="查看权限码（当前未绑定接口）"
        >
          未绑定接口
        </button>
      </Popover>
    )
  }

  return (
    <Popover
      open={open}
      onOpenChange={setOpen}
      trigger="click"
      placement="rightTop"
      destroyOnHidden={false}
      content={
        <div className="w-[360px] max-w-[76vw]">
          <CodeLine code={code} />
          <BindingList code={code} open={open} />
        </div>
      }
    >
      <button
        type="button"
        className="ml-2 shrink-0 cursor-pointer border-0 bg-transparent p-0 text-[12px] text-[var(--color-primary)] hover:text-[var(--color-primary-pressed)] hover:underline"
        // 阻止冒泡：点接口计数不应触发树节点选中 / 勾选
        onClick={(event) => event.stopPropagation()}
        title={`查看 ${code} 绑定的接口`}
      >
        {count} 个接口
      </button>
    </Popover>
  )
}