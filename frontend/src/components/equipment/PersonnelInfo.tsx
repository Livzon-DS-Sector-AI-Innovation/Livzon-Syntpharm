'use client'

import {Popover, Typography} from 'antd'
import {
  IdcardOutlined, BankOutlined,
  PhoneOutlined,
} from '@ant-design/icons'
import type { Personnel } from '@/types/equipment-personnel'
import { UserAvatar } from '@/components/common/UserAvatar'

const { Text } = Typography

interface PersonnelInfoProps {
  personnel: Pick<Personnel, 'name' | 'employee_no' | 'department' | 'position' | 'mobile' | 'avatar_url' | 'roles'>
}

export function PersonnelInfo({ personnel }: PersonnelInfoProps) {
  const { name, employee_no, department, position, mobile, avatar_url, roles } = personnel

  const content = (
    <div style={{ width: 240 }}>
      {/* Header — large avatar + name + position */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 14,
        paddingBottom: 14, marginBottom: 14,
        borderBottom: '1px solid #ede9e4',
      }}>
        <UserAvatar
          size={48}
          name={name}
          src={avatar_url}
          style={{ boxShadow: '0 3px 12px rgba(0,0,0,0.1)' }}
        />
        <div style={{ minWidth: 0 }}>
          <Text strong style={{ fontSize: 15, color: '#1a1a1a', display: 'block', lineHeight: '20px' }}>
            {name || '—'}
          </Text>
          {position && (
            <Text style={{ fontSize: 12, color: '#787671', lineHeight: '16px' }}>
              {position}
            </Text>
          )}
          {!position && department && (
            <Text style={{ fontSize: 12, color: '#787671', lineHeight: '16px' }}>
              {department}
            </Text>
          )}
        </div>
      </div>

      {/* Fields grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {employee_no && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <IdcardOutlined style={{ fontSize: 14, color: '#a4a097', width: 16, flexShrink: 0 }} />
            <Text style={{ fontSize: 11, fontWeight: 600, color: '#a4a097', width: 28, flexShrink: 0, textTransform: 'uppercase', letterSpacing: 0.5 }}>工号</Text>
            <Text style={{ fontSize: 13, color: '#37352f', fontWeight: 500 }}>{employee_no}</Text>
          </div>
        )}
        {department && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <BankOutlined style={{ fontSize: 14, color: '#a4a097', width: 16, flexShrink: 0 }} />
            <Text style={{ fontSize: 11, fontWeight: 600, color: '#a4a097', width: 28, flexShrink: 0, textTransform: 'uppercase', letterSpacing: 0.5 }}>部门</Text>
            <Text style={{ fontSize: 13, color: '#37352f', fontWeight: 500 }}>{department}</Text>
          </div>
        )}
        {mobile && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <PhoneOutlined style={{ fontSize: 14, color: '#a4a097', width: 16, flexShrink: 0 }} />
            <Text style={{ fontSize: 11, fontWeight: 600, color: '#a4a097', width: 28, flexShrink: 0, textTransform: 'uppercase', letterSpacing: 0.5 }}>手机</Text>
            <Text style={{ fontSize: 13, color: '#37352f', fontWeight: 500 }}>{mobile}</Text>
          </div>
        )}
      </div>

      {/* Roles */}
      {roles && roles.length > 0 && (
        <div style={{
          marginTop: 14, paddingTop: 14,
          borderTop: '1px solid #ede9e4',
        }}>
          <Text style={{
            fontSize: 11, fontWeight: 600, color: '#a4a097',
            textTransform: 'uppercase', letterSpacing: 0.5,
            display: 'block', marginBottom: 8,
          }}>
            设备角色
          </Text>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {roles.map(r => (
              <span key={r.id} style={{
                display: 'inline-flex', alignItems: 'center',
                padding: '2px 10px', borderRadius: 4,
                fontSize: 12, fontWeight: 600, lineHeight: '20px',
                color: '#391c57', background: '#e6e0f5',
              }}>
                {r.name}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )

  return (
    <Popover
      content={content}
      trigger="hover"
      placement="right"
      mouseEnterDelay={0.3}
      overlayStyle={{ maxWidth: 320 }}
    >
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 10,
        cursor: 'pointer',
        padding: '4px 10px 4px 4px',
        margin: '-4px -10px -4px -4px',
        borderRadius: 9,
        transition: 'background 0.15s ease',
      }}>
        <UserAvatar
          size={34}
          name={name}
          src={avatar_url}
          style={{ border: '2px solid #ffffff', outline: '2px solid #ede9e4' }}
        />
        <div style={{
          display: 'flex', flexDirection: 'column',
          lineHeight: 1.35, minWidth: 0,
        }}>
          <Text style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a' }}>
            {name || '未命名'}
          </Text>
          {department && (
            <Text type="secondary" style={{ fontSize: 12, lineHeight: '16px' }}>
              {department}
            </Text>
          )}
        </div>
      </div>
    </Popover>
  )
}
