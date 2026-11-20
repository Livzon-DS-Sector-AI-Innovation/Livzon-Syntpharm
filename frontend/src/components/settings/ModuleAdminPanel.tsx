'use client'

import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Card, Empty, Skeleton, Space, Tag, Typography } from 'antd'
import { UserAddOutlined } from '@ant-design/icons'
import PersonSelect from '@/components/common/PersonSelect'
import { assignModuleAdmin, fetchModuleAdmins, removeModuleAdmin } from '@/actions/permission'
import type { ModuleAdminUser } from '@/types/permission'

const { Text } = Typography

/**
 * 系统管理员侧：为每个业务模块指派「模块负责人」。
 *
 * 只有系统管理员能进这个页签（后端 `require_assignment_admin` 兜底）。
 * 模块负责人自动拥有该模块全部业务权限，并可在模块配置页指派「模块代表」；
 * 模块代表不在本页维护（2026-11-19 需求）。
 */
export default function ModuleAdminPanel() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [picked, setPicked] = useState<Record<string, string | undefined>>({})
  const [pending, setPending] = useState<string | null>(null)

  const { data: groups = [], isLoading } = useQuery({
    queryKey: ['module-admins'],
    queryFn: fetchModuleAdmins,
  })

  const unassigned = useMemo(
    () => groups.filter((group) => (group.heads ?? []).length === 0).length,
    [groups],
  )

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['module-admins'] })

  const assign = async (moduleCode: string) => {
    const userId = picked[moduleCode]
    if (!userId) {
      message.warning('请先选择要指派的员工')
      return
    }
    setPending(moduleCode)
    try {
      const result = await assignModuleAdmin({ module_code: moduleCode, role_type: 'owner', user_id: userId })
      if (!result.ok) {
        message.error(result.message)
        return
      }
      message.success('已指派为模块负责人')
      setPicked((prev) => ({ ...prev, [moduleCode]: undefined }))
      await refresh()
    } finally {
      setPending(null)
    }
  }

  const remove = async (moduleCode: string, user: ModuleAdminUser) => {
    setPending(moduleCode)
    try {
      const result = await removeModuleAdmin({
        module_code: moduleCode,
        role_type: user.role_type,
        user_id: user.user_id,
      })
      if (!result.ok) {
        message.error(result.message)
        return
      }
      message.success('已移除')
      await refresh()
    } finally {
      setPending(null)
    }
  }

  return (
    <div className="space-y-4">
      <Card size="small">
        <Space direction="vertical" size={6} className="w-full">
          <Text strong>指派模块负责人</Text>
          <Text type="secondary">
            模块负责人自动拥有该模块全部业务权限并随新功能自动扩充，可在「模块配置」页维护岗位角色、授权并指派模块代表。
            模块代表由模块负责人指派，系统管理员不代劳。当前有 {unassigned} 个模块还没有负责人。
          </Text>
        </Space>
      </Card>

      {isLoading ? (
        <Card size="small">
          <Skeleton active paragraph={{ rows: 8 }} />
        </Card>
      ) : groups.length === 0 ? (
        <Card size="small">
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="还没有可指派的模块，请确认模块注册表已加载"
          />
        </Card>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {groups.map((group) => (
            <Card
              key={group.module_code}
              size="small"
              title={group.module_name}
              extra={<Text type="secondary" className="text-[12px]">{group.module_code}</Text>}
            >
              <Space direction="vertical" size={8} className="w-full">
                <div>
                  <Text type="secondary" className="text-[12px]">模块负责人</Text>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {(group.heads ?? []).length === 0 ? (
                      <Text type="secondary">尚未指派</Text>
                    ) : (
                      (group.heads ?? []).map((user) => (
                        <Tag
                          key={user.grant_id}
                          color="gold"
                          closable
                          onClose={(event) => {
                            event.preventDefault()
                            void remove(group.module_code, user)
                          }}
                        >
                          {user.name || user.username || user.user_id}
                        </Tag>
                      ))
                    )}
                  </div>
                </div>
                <Space.Compact className="w-full">
                  <PersonSelect
                    placeholder="搜索姓名，指派模块负责人"
                    value={picked[group.module_code]}
                    onChange={(person) =>
                      setPicked((prev) => ({ ...prev, [group.module_code]: person?.id }))
                    }
                  />
                  <Button
                    type="primary"
                    icon={<UserAddOutlined />}
                    loading={pending === group.module_code}
                    onClick={() => assign(group.module_code)}
                  >
                    指派
                  </Button>
                </Space.Compact>
              </Space>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
