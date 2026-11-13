'use client'

import { Select, Typography } from 'antd'
import type { Personnel } from '@/types/equipment-personnel'
import type { SelectProps } from 'antd'
import { UserAvatar } from '@/components/common/UserAvatar'

const { Text } = Typography

interface Props extends Omit<SelectProps, 'options' | 'optionRender' | 'children'> {
  personnel: Personnel[]
}

export function PersonnelSelect({ personnel, ...rest }: Props) {
  return (
    <Select
      {...rest}
      showSearch optionFilterProp='label'
      popupMatchSelectWidth={false}
      options={personnel.map(p => ({
        // 统一「姓名（账号）」；设备人员池没有账号时只显示姓名
        label: `${p.name}${p.username ? `（${p.username}）` : ''}${p.department ? ' · ' + p.department : ''}`,
        value: p.user_id || p.id,
      }))}
      optionRender={o => {
        const p = personnel.find(pe => (pe.user_id || pe.id) === o.value)
        if (!p) return <Text>{o.label}</Text>
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <UserAvatar size={28} name={p.name} src={p.avatar_url} />
            <div style={{ lineHeight: 1.3 }}>
              <Text style={{ fontSize: 13, fontWeight: 500 }}>{p.name}</Text>
              {p.department && (
                <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>
                  {p.department}{p.employee_no ? ` · ${p.employee_no}` : ''}
                </Text>
              )}
            </div>
          </div>
        )
      }}
    />
  )
}
