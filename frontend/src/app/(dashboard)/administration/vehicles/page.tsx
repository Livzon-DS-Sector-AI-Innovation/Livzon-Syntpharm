'use client'

import { useState, useEffect, useRef } from 'react'
import { Button, Input, Tag, Modal, Form, message, Popconfirm, Upload, Image, Card, Empty } from 'antd'
import { PlusOutlined, SearchOutlined, DeleteOutlined, EditOutlined, UploadOutlined, ImportOutlined, DownloadOutlined } from '@ant-design/icons'
import { fetchVehicles } from '@/lib/api/client/administration/vehicle'
import { batchImportVehicles } from '@/actions/administration'
import { createVehicle, updateVehicle, deleteVehicle } from '@/actions/administration'
import { UploadFile } from 'antd'

const STATUS_COLORS: Record<string, string> = {
  '可用': 'success',
  '维修中': 'warning',
  '已报废': 'error',
}

const fileToBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      resolve(result.split(',')[1])
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export default function VehiclePage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 })
  const importInputRef = useRef<HTMLInputElement>(null)

  const load = async (page = 1) => {
    setLoading(true)
    try {
      console.log('开始请求车辆列表...')
      const res = await fetchVehicles({ keyword, page, page_size: pagination.pageSize })
      console.log('请求结果:', res)
      setData(res.data || [])
      setPagination({ ...pagination, current: page, total: res.meta?.total || 0 })
    } catch (err: any) {
      console.error('请求失败:', err)
      message.error(err.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(1) }, [keyword])

  const handleSave = async (values: any) => {
    try {
      const payload = { ...values }
      if (fileList.length > 0 && fileList[0].originFileObj) {
        const base64 = await fileToBase64(fileList[0].originFileObj as File)
        payload.photo_data = base64
        payload.photo_type = fileList[0].type || 'image/jpeg'
      }
      if (editing) {
        await updateVehicle(editing.id, payload)
        message.success('更新成功')
      } else {
        await createVehicle(payload)
        message.success('创建成功')
      }
      setModalOpen(false)
      form.resetFields()
      setEditing(null)
      setFileList([])
      load(pagination.current)
    } catch (err: any) {
      message.error(err.message || '保存失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteVehicle(id)
      message.success('删除成功')
      load(pagination.current)
    } catch (err: any) {
      message.error(err.message || '删除失败')
    }
  }

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const res = await batchImportVehicles(file)
      const result = res.data || {}
      const parts = [
        `新增 ${result.created || 0} 条`,
        result.restored !== undefined ? `恢复 ${result.restored} 条` : null,
        `失败 ${result.failed || 0} 条`,
      ].filter(Boolean)
      message.success(`导入完成：${parts.join('，')}`)
      if (result.errors && result.errors.length > 0) {
        console.error('导入错误:', result.errors)
      }
      load(1)
    } catch (err: any) {
      message.error(err.message || '批量导入失败')
    } finally {
      if (importInputRef.current) importInputRef.current.value = ''
    }
  }

  const openModal = (record?: any) => {
    if (record) {
      setEditing(record)
      form.setFieldsValue(record)
      if (record.photo_data) {
        setFileList([{
          uid: '-1',
          name: 'photo.jpg',
          status: 'done',
          url: `data:${record.photo_type || 'image/jpeg'};base64,${record.photo_data}`,
        }])
      } else {
        setFileList([])
      }
    } else {
      setEditing(null)
      form.resetFields()
      setFileList([])
    }
    setModalOpen(true)
  }

  const VehicleCard = ({ record }: { record: any }) => (
    <Card
      hoverable
      className="relative overflow-hidden"
      cover={
        record.photo_data ? (
          <div className="aspect-square overflow-hidden bg-gray-50">
            <Image
              src={`data:${record.photo_type || 'image/jpeg'};base64,${record.photo_data}`}
              alt="车辆照片"
              className="w-full h-full object-cover"
              preview={{ mask: '点击查看大图' }}
            />
          </div>
        ) : (
          <div className="aspect-square bg-gray-100 flex items-center justify-center text-gray-400 text-sm">
            无照片
          </div>
        )
      }
      actions={[
        <Button key="edit" type="link" icon={<EditOutlined />} onClick={() => openModal(record)}>
          编辑
        </Button>,
        <Popconfirm key="delete" title="确认删除？" onConfirm={() => handleDelete(record.id)}>
          <Button type="link" danger icon={<DeleteOutlined />}>
            删除
          </Button>
        </Popconfirm>,
      ]}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-lg font-bold text-gray-900">{record.plate_number}</span>
        <Tag color={STATUS_COLORS[record.status] || 'default'}>{record.status}</Tag>
      </div>
      <div className="space-y-1 text-sm text-gray-600">
        <div className="flex justify-between">
          <span className="text-gray-400">品牌</span>
          <span>{record.brand || '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">型号</span>
          <span>{record.model || '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">颜色</span>
          <span>{record.color || '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">里程</span>
          <span>{record.mileage !== null && record.mileage !== undefined ? `${record.mileage} km` : '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">所属部门</span>
          <span>{record.owner_department || '-'}</span>
        </div>
      </div>
    </Card>
  )

  return (
    <div className="p-6">
      <div className="flex gap-2 mb-6">
        <Input
          placeholder="搜索车牌号或品牌"
          prefix={<SearchOutlined />}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={() => load(1)}
          style={{ width: 280 }}
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={() => openModal()}>
          新增车辆
        </Button>
        <Button icon={<ImportOutlined />} onClick={() => importInputRef.current?.click()}>
          批量导入
        </Button>
        <Button icon={<DownloadOutlined />}>
          <a href="/templates/车辆信息批量导入模板.xlsx" download style={{ color: 'inherit', textDecoration: 'none' }}>
            下载模板
          </a>
        </Button>
        <input
          ref={importInputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          style={{ display: 'none' }}
          onChange={handleImport}
        />
      </div>

      {data.length === 0 && !loading ? (
        <Empty description="暂无车辆数据" className="py-20" />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {data.map((record) => (
              <VehicleCard key={record.id} record={record} />
            ))}
          </div>
          {pagination.total > pagination.pageSize && (
            <div className="flex justify-center mt-6">
              <div className="flex items-center gap-2">
                <Button
                  disabled={pagination.current <= 1}
                  onClick={() => load(pagination.current - 1)}
                >
                  上一页
                </Button>
                <span className="text-sm text-gray-600">
                  第 {pagination.current} 页 / 共 {Math.ceil(pagination.total / pagination.pageSize)} 页
                </span>
                <Button
                  disabled={pagination.current >= Math.ceil(pagination.total / pagination.pageSize)}
                  onClick={() => load(pagination.current + 1)}
                >
                  下一页
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      <Modal
        open={modalOpen}
        title={editing ? '编辑车辆' : '新增车辆'}
        onCancel={() => { setModalOpen(false); setEditing(null); form.resetFields(); setFileList([]) }}
        onOk={() => form.submit()}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Form.Item name="plate_number" label="车牌号" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="brand" label="品牌">
            <Input />
          </Form.Item>
          <Form.Item name="model" label="型号">
            <Input />
          </Form.Item>
          <Form.Item name="color" label="颜色">
            <Input />
          </Form.Item>
          <Form.Item name="mileage" label="里程">
            <Input type="number" />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue="可用">
            <Input />
          </Form.Item>
          <Form.Item name="owner_department" label="所属部门">
            <Input />
          </Form.Item>
          <Form.Item label="车辆照片">
            <Upload
              listType="picture-card"
              fileList={fileList}
              beforeUpload={() => false}
              onChange={({ fileList: fl }) => setFileList(fl)}
              maxCount={1}
              accept="image/*"
            >
              {fileList.length < 1 && (
                <div>
                  <UploadOutlined />
                  <div style={{ marginTop: 8 }}>上传照片</div>
                </div>
              )}
            </Upload>
          </Form.Item>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
