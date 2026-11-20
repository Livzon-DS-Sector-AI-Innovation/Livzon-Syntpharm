'use client'

import { Drawer } from 'antd'
import { SettingOutlined } from '@ant-design/icons'

import { ModuleSettingsClient } from '@/components/settings'

interface Props {
  open: boolean
  onClose: () => void
}

/**
 * 智能体模块的运行时配置抽屉。
 *
 * 原先是独立页面 `/agent/settings`，为避免制作视频时来回跳页丢失列表筛选与分页状态，
 * 改成列表页「模型配置」左侧的按钮 + 抽屉，内容复用模块设置组件（embedded 去掉页头）。
 */
export default function AgentSettingsDrawer({ open, onClose }: Props) {
  return (
    <Drawer
      size={720}
      open={open}
      onClose={onClose}
      destroyOnHidden
      title={
        <span className="flex items-center gap-2">
          <SettingOutlined className="text-[#5645D4]" />
          智能体参数设置
        </span>
      }
      styles={{
        header: { borderBottom: '1px solid #e5e3df', padding: '16px 24px' },
        body: { padding: '16px 24px', background: '#FCFCFB' },
      }}
    >
      <ModuleSettingsClient
        moduleCode="agent"
        moduleName="智能体"
        moduleDescription="配置 PPT 配音视频的旁白、逐段合成节奏与页内视觉引导（讲到哪、画面就亮到哪）。"
        embedded
      />
    </Drawer>
  )
}