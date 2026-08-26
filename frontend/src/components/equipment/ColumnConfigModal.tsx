'use client'

import { useState, useEffect } from 'react'
import { Modal, Checkbox, Button } from 'antd'
import { SettingOutlined } from '@ant-design/icons'

interface ColumnOption {
  key: string
  label: string
  defaultVisible: boolean
}

const ALL_COLUMNS: ColumnOption[] = [
  { key: 'asset_no', label: '资产编号', defaultVisible: true },
  { key: 'label_no', label: '标签号', defaultVisible: false },
  { key: 'equipment_tag', label: '设备位号', defaultVisible: false },
  { key: 'name', label: '设备名称', defaultVisible: true },
  { key: 'equipment_class', label: '设备分类', defaultVisible: false },
  { key: 'location_text', label: '设备位置', defaultVisible: true },
  { key: 'department', label: '归属部门', defaultVisible: true },
  { key: 'responsible', label: '负责人', defaultVisible: true },
  { key: 'status', label: '设备状态', defaultVisible: true },
  { key: 'category_description', label: '资产类别说明', defaultVisible: false },
  { key: 'model', label: '型号', defaultVisible: false },
  { key: 'manufacturer', label: '制造商', defaultVisible: false },
  { key: 'supplier', label: '供应商', defaultVisible: false },
  { key: 'commissioning_date', label: '投用日期', defaultVisible: true },
  { key: 'current_cost', label: '当前成本', defaultVisible: false },
  { key: 'book_value', label: '账面净值', defaultVisible: false },
  { key: 'scrap_status', label: '报废状态', defaultVisible: false },
  { key: 'scrap_time', label: '报废时间', defaultVisible: false },
  { key: 'quantity', label: '数量', defaultVisible: false },
]

const STORAGE_KEY = 'equipment_visible_columns'

interface ColumnConfigModalProps {
  open: boolean
  onClose: () => void
  onSave: (visibleColumns: string[]) => void
}

export function ColumnConfigModal({ open, onClose, onSave }: ColumnConfigModalProps) {
  const [selectedKeys, setSelectedKeys] = useState<string[]>([])

  // 从 localStorage 加载配置
  useEffect(() => {
    if (open) {
      try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored)
          if (Array.isArray(parsed)) {
            setSelectedKeys(parsed)
            return
          }
        }
      } catch (e) {
        console.warn('Failed to load column config from localStorage:', e)
      }
      // 如果没有存储的配置，使用默认值
      setSelectedKeys(ALL_COLUMNS.filter(col => col.defaultVisible).map(col => col.key))
    }
  }, [open])

  const handleSave = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(selectedKeys))
    } catch (e) {
      console.warn('Failed to save column config to localStorage:', e)
    }
    onSave(selectedKeys)
    onClose()
  }

  const handleSelectAll = () => {
    setSelectedKeys(ALL_COLUMNS.map(col => col.key))
  }

  const handleDeselectAll = () => {
    setSelectedKeys([])
  }

  const handleReset = () => {
    const defaults = ALL_COLUMNS.filter(col => col.defaultVisible).map(col => col.key)
    setSelectedKeys(defaults)
  }

  return (
    <Modal
      title={
        <span>
          <SettingOutlined style={{ marginRight: 8 }} />
          列配置
        </span>
      }
      open={open}
      onCancel={onClose}
      footer={[
        <Button key="reset" onClick={handleReset}>
          恢复默认
        </Button>,
        <Button key="cancel" onClick={onClose}>
          取消
        </Button>,
        <Button key="save" type="primary" onClick={handleSave}>
          保存
        </Button>,
      ]}
      width={600}
    >
      <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
        <Button size="small" onClick={handleSelectAll}>
          全选
        </Button>
        <Button size="small" onClick={handleDeselectAll}>
          取消全选
        </Button>
      </div>
      <div style={{ maxHeight: 400, overflowY: 'auto' }}>
        <Checkbox.Group
          style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
          value={selectedKeys}
          onChange={(values) => setSelectedKeys(values as string[])}
        >
          {ALL_COLUMNS.map((col) => (
            <Checkbox key={col.key} value={col.key}>
              {col.label}
            </Checkbox>
          ))}
        </Checkbox.Group>
      </div>
      <div style={{ marginTop: 16, fontSize: 12, color: '#94a3b8' }}>
        <p style={{ margin: 0 }}>
          💡 提示：至少需要保留"资产编号"和"设备名称"列以便识别设备。
        </p>
      </div>
    </Modal>
  )
}
