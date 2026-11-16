'use client'

import { useCallback, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { App, Button, Empty, Input, List, Modal, Popconfirm, Space, Tag, Typography } from 'antd'
import { CheckOutlined, CloseOutlined, DeleteOutlined, EditOutlined, LockOutlined, PlusOutlined } from '@ant-design/icons'
import { createHazardCategory, deleteHazardCategory, updateHazardCategory } from '@/actions/safety'
import { fetchHazardCategories, invalidateHazardCategoryCache } from '@/lib/api/client/safety'

const { Text } = Typography

interface Props {
  open: boolean
  onClose: () => void
  /** 类别字典变化后通知父组件刷新下拉数据 */
  onChanged?: () => void | Promise<void>
}

/**
 * 隐患类别管理弹窗（仅「隐患类别管理员」可打开）。
 *
 * - 新增 / 改名 / 删除都由后端 safety:hazard-category:manage 校验，前端隐藏只是体验优化
 * - 内置 7 类不在字典表内（id 为 null），只读展示、不可改不可删
 * - 删除是软删除，历史台账保留原类别名
 *
 * 内容体单独抽成 CategoryManager，配合 destroyOnHidden 实现「每次打开都是干净状态」，
 * 避免在 effect 里同步 setState 重置编辑态。
 */
export default function HazardCategoryModal({ open, onClose, onChanged }: Props) {
  return (
    <Modal title="隐患类别管理" open={open} onCancel={onClose} footer={null} width={560} destroyOnHidden>
      <CategoryManager onChanged={onChanged} />
    </Modal>
  )
}

function CategoryManager({ onChanged }: Pick<Props, 'onChanged'>) {
  const { message } = App.useApp()
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingName, setEditingName] = useState('')
  const [savingId, setSavingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // 加载态与刷新交给 React Query：避免在 effect 里同步 setState（React 19 lint 规则）
  const {
    data: items = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['hazard-categories', 'admin'],
    // 强制穿透模块级缓存：管理弹窗必须看到最新列表
    queryFn: () => fetchHazardCategories(true),
    staleTime: 0,
    refetchOnMount: 'always',
  })

  const notifyChanged = useCallback(async () => {
    invalidateHazardCategoryCache()
    await refetch()
    await onChanged?.()
  }, [onChanged, refetch])

  const handleCreate = useCallback(async () => {
    const name = newName.trim()
    if (!name) {
      message.warning('请输入类别名称')
      return
    }
    setCreating(true)
    try {
      const response = await createHazardCategory(name)
      if (response.code !== 200) {
        message.error(response.message || '新增类别失败')
        return
      }
      setNewName('')
      message.success(`已新增隐患类别「${name}」`)
      await notifyChanged()
    } catch {
      message.error('新增类别失败，请确认当前账号有类别管理权限')
    } finally {
      setCreating(false)
    }
  }, [message, newName, notifyChanged])

  const handleRename = useCallback(
    async (id: string) => {
      const name = editingName.trim()
      if (!name) {
        message.warning('请输入类别名称')
        return
      }
      setSavingId(id)
      try {
        const response = await updateHazardCategory(id, name)
        if (response.code !== 200) {
          message.error(response.message || '修改类别失败')
          return
        }
        setEditingId(null)
        setEditingName('')
        message.success(`已重命名为「${name}」，历史台账中的旧名称同步更新`)
        await notifyChanged()
      } catch {
        message.error('修改类别失败，请确认当前账号有类别管理权限')
      } finally {
        setSavingId(null)
      }
    },
    [editingName, message, notifyChanged]
  )

  const handleDelete = useCallback(
    async (id: string) => {
      setDeletingId(id)
      try {
        const response = await deleteHazardCategory(id)
        if (response.code !== 200) {
          message.error(response.message || '删除类别失败')
          return
        }
        message.success('已删除该隐患类别')
        await notifyChanged()
      } catch {
        message.error('删除类别失败，请确认当前账号有类别管理权限')
      } finally {
        setDeletingId(null)
      }
    },
    [message, notifyChanged]
  )

  return (
    <>
      <Text type="secondary" style={{ fontSize: 12 }}>
        类别全公司共享。内置 7 类不可修改或删除；自定义类别改名后，历史隐患记录中的旧名称会同步更新。
      </Text>

      <Space.Compact style={{ width: '100%', marginTop: 12 }}>
        <Input
          maxLength={64}
          placeholder="输入新类别名称"
          value={newName}
          onChange={(event) => setNewName(event.target.value)}
          onPressEnter={handleCreate}
        />
        <Button type="primary" icon={<PlusOutlined />} loading={creating} onClick={handleCreate}>
          新增
        </Button>
      </Space.Compact>

      <List
        style={{ marginTop: 12 }}
        loading={isLoading}
        dataSource={items}
        locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无类别" /> }}
        renderItem={(item) => {
          const builtin = item.is_builtin || !item.id
          const editing = !builtin && editingId === item.id
          return (
            <List.Item
              actions={
                builtin
                  ? [
                      <Tag key="builtin" icon={<LockOutlined />} color="default">
                        内置
                      </Tag>,
                    ]
                  : editing
                    ? [
                        <Button
                          key="save"
                          type="link"
                          size="small"
                          icon={<CheckOutlined />}
                          loading={savingId === item.id}
                          onClick={() => item.id && handleRename(item.id)}
                        >
                          保存
                        </Button>,
                        <Button
                          key="cancel"
                          type="link"
                          size="small"
                          icon={<CloseOutlined />}
                          onClick={() => {
                            setEditingId(null)
                            setEditingName('')
                          }}
                        >
                          取消
                        </Button>,
                      ]
                    : [
                        <Button
                          key="edit"
                          type="link"
                          size="small"
                          icon={<EditOutlined />}
                          onClick={() => {
                            setEditingId(item.id as string)
                            setEditingName(item.name)
                          }}
                        >
                          改名
                        </Button>,
                        <Popconfirm
                          key="delete"
                          title={`删除类别「${item.name}」？`}
                          description="删除后不再出现在下拉中，历史隐患记录保留原类别名。"
                          okText="删除"
                          okButtonProps={{ danger: true }}
                          cancelText="取消"
                          onConfirm={() => item.id && handleDelete(item.id)}
                        >
                          <Button
                            type="link"
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                            loading={deletingId === item.id}
                          >
                            删除
                          </Button>
                        </Popconfirm>,
                      ]
              }
            >
              {editing ? (
                <Input
                  autoFocus
                  size="small"
                  maxLength={64}
                  value={editingName}
                  style={{ maxWidth: 280 }}
                  onChange={(event) => setEditingName(event.target.value)}
                  onPressEnter={() => item.id && handleRename(item.id)}
                />
              ) : (
                <Text>{item.name}</Text>
              )}
            </List.Item>
          )
        }}
      />
    </>
  )
}