'use client'

import { Avatar, Card, Descriptions, Tag, Typography } from 'antd'
import { UserOutlined } from '@ant-design/icons'

const { Text } = Typography

export interface ProfileInfo {
  name: string
  username: string | null
  employeeNo: string | null
  department: string | null
  position: string | null
  email: string | null
  mobile: string | null
  authSource: 'local' | 'feishu'
  avatarUrl: string | null
  status: 'active' | 'disabled'
  mustChangePassword: boolean
}

interface ProfileClientProps {
  user: ProfileInfo
  isSuperuser: boolean
  permissionCount: number
}

const EMPTY = '-'

/**
 * 个人信息（只读）。
 *
 * 数据全部由服务端 `getCurrentUser` 下发，页面不额外请求接口；
 * 人员资料以飞书同步为准，因此这里不提供编辑入口。
 */
export function ProfileClient({ user, isSuperuser, permissionCount }: ProfileClientProps) {
  const fields = [
    { key: 'name', label: '姓名', children: user.name || EMPTY },
    { key: 'username', label: '用户名', children: user.username || EMPTY },
    { key: 'employee_no', label: '工号', children: user.employeeNo || EMPTY },
    { key: 'department', label: '部门', children: user.department || EMPTY },
    { key: 'position', label: '职位', children: user.position || EMPTY },
    { key: 'email', label: '邮箱', children: user.email || EMPTY },
    { key: 'mobile', label: '手机号', children: user.mobile || EMPTY },
    {
      key: 'auth_source',
      label: '登录来源',
      children: user.authSource === 'feishu' ? '飞书登录' : '账号密码',
    },
  ]

  return (
    <div className="settings-scope settings-enter mx-auto max-w-[960px] md:px-6 md:py-6">
      <div className="mb-5">
        <h1 className="m-0 text-[24px] font-semibold text-[var(--color-charcoal)]">个人信息</h1>
        <p className="m-0 mt-1 text-[13px] text-[var(--color-steel)]">
          查看当前账号的基本资料与登录来源。人员资料以飞书同步为准，如需修改请联系管理员。
        </p>
      </div>

      <Card>
        <div className="flex flex-wrap items-center gap-4">
          <Avatar
            size={64}
            src={user.avatarUrl || undefined}
            icon={<UserOutlined />}
            className="shrink-0"
          />
          <div className="min-w-0">
            <div className="text-[20px] font-semibold text-[var(--color-ink)]">{user.name}</div>
            <div className="mt-0.5 text-[13px] text-[var(--color-steel)]">
              {user.username || user.email || EMPTY}
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <Tag color={user.status === 'active' ? 'success' : 'error'}>
                {user.status === 'active' ? '启用' : '禁用'}
              </Tag>
              <Tag color={isSuperuser ? 'purple' : 'default'}>
                {isSuperuser ? '超级管理员' : '普通账号'}
              </Tag>
              {user.mustChangePassword && <Tag color="warning">待改密</Tag>}
            </div>
          </div>
        </div>

        <Descriptions
          className="mt-6"
          column={{ xs: 1, sm: 1, md: 2 }}
          bordered
          size="middle"
          items={fields}
        />
      </Card>

      <Card className="mt-4" title="权限">
        <Descriptions
          column={{ xs: 1, sm: 1, md: 2 }}
          items={[
            {
              key: 'role',
              label: '角色',
              children: isSuperuser ? '超级管理员（拥有全部权限）' : '普通账号',
            },
            { key: 'count', label: '已授权权限', children: `${permissionCount} 项` },
          ]}
        />
        <Text type="secondary" className="text-[12px]">
          如需调整角色或权限，请联系系统管理员在「系统管理 → 权限管理」中修改。
        </Text>
      </Card>
    </div>
  )
}
