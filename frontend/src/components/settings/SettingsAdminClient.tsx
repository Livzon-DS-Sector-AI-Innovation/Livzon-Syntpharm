'use client'

import { Tabs, Tooltip } from 'antd'
import { usePermission } from '@/hooks/usePermission'
import { PERM } from '@/lib/permissions/codes'
import AgentSkillManagementClient from './AgentSkillManagementClient'
import FeishuSettingsClient from './FeishuSettingsClient'
import LLMConfigClient from './LLMConfigClient'
import { SettingsPageHeader } from './SettingsPageHeader'

/**
 * 系统设置：平台级配置（LLM / 飞书 / Livzon Skill）。
 *
 * 用户管理、登录记录、权限管理、系统运维都已拆成左侧独立菜单项，
 * 各自在页面（RSC）里做权限守卫，这里只留平台配置类。
 */
export default function SettingsAdminClient() {
  // 注意：hook 必须写在任何 early return 之前。
  const { can, loading } = usePermission()

  if (loading) {
    return (
      <div className="mx-auto max-w-[1320px] md:px-6 md:py-6 text-[13px] text-[var(--color-steel)]">
        正在加载…
      </div>
    )
  }

  const items = [
    ...(can(PERM.configRead)
      ? [
          {
            key: 'llm',
            label: 'LLM 模型配置',
            children: <LLMConfigClient embedded />,
          },
          {
            key: 'feishu',
            label: '飞书设置',
            children: <FeishuSettingsClient />,
          },
          {
            // 待后端接入：后端 agent 模块已在迁移 0035_drop_agent_tables 中下线，
            // /api/v1/agent/skills 已不存在（进入会 404），故 Tab 置灰且不挂载子组件。
            // 后端恢复后把 disabled 去掉即可，其余代码不用动。
            key: 'agent-skills',
            disabled: true,
            label: (
              <Tooltip title="功能待后端接入：原 agent 模块已下线，接口恢复后自动开放">
                Livzon Skill（待后端接入）
              </Tooltip>
            ),
            children: <AgentSkillManagementClient />,
          },
        ]
      : []),
  ]

  return (
    <div className="settings-scope settings-enter mx-auto max-w-[1320px] md:px-6 md:py-6">
      <SettingsPageHeader
        title="系统配置"
        description="统一 LLM 模型配置、飞书设置与 Livzon Skill。用户与权限相关功能见左侧对应菜单。"
      />
      <Tabs defaultActiveKey={items[0]?.key} items={items} />
    </div>
  )
}
