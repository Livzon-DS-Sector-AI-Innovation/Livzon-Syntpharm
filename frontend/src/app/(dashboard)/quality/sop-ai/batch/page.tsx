'use client'
import type { UploadFile } from 'antd'

import React, { useState } from 'react'
import {
  Card,
  Form,
  Input,
  Button,
  Upload,
  message,
  Space,
  Divider,
  Table,
  Tag,
  Typography,
  Progress,
  Spin,
  Result,
} from 'antd'
import {
  FileTextOutlined,
  RobotOutlined,
  InboxOutlined,
} from '@ant-design/icons'
import { batchCheck } from '@/actions/sop-ai'
import {BatchCheckResult as BatchResultType} from '@/types/sop-ai'

const { Title, Text, Paragraph } = Typography
const { Dragger } = Upload

type SopAiBatchPageProps = Record<string, never>

/**
 * 批量巡检页面
 */
export default function SopAiBatchPage(_props: SopAiBatchPageProps) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<BatchResultType | null>(null)
  const [fileList, setFileList] = useState<UploadFile[]>([])

  // 处理文件选择
  const handleFileChange = (info: { fileList: UploadFile[] }) => {
    setFileList(info.fileList)
  }

  // 提交批量巡检
  const handleSubmit = async (values: Record<string, unknown>) => {
    if (!fileList.length) {
      message.error('请选择文件')
      return
    }

    setLoading(true)
    setResult(null)

    try {
      const filePaths = fileList.map(
        (f) => f.name
      )

      const response = await batchCheck({
        file_paths: filePaths,
        check_type: 'batch',
        operator: values.operator as string,
      })

      setResult(response)
    } catch (error: unknown) {
      message.error((error instanceof Error ? error.message : "操作失败") || '批量巡检失败')
    } finally {
      setLoading(false)
    }
  }

  // 表格列定义
  const columns = [
    {
      title: '文件',
      dataIndex: 'file_path',
      key: 'file_path',
      render: (text: string) => (
        <Space>
          <FileTextOutlined />
          <Text>{text.split('/').pop()?.split('\\').pop()}</Text>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'completed' ? 'green' : 'red'}>
          {status === 'completed' ? '完成' : '失败'}
        </Tag>
      ),
    },
    {
      title: '问题数',
      key: 'problems',
      render: (_: unknown, record: Record<string, unknown>) => (
        <Space>
          <Tag color="red">{record.risk_high as string}</Tag>
          <Tag color="orange">{record.risk_medium as string}</Tag>
          <Tag color="green">{record.risk_low as string}</Tag>
        </Space>
      ),
    },
  ]

  return (
    <div className="sop-ai-batch-page">
      <Card>
        <Title level={4}>批量巡检</Title>
        <Paragraph type="secondary">
          批量上传多个 SOP 文件进行 AI 辅助巡检，检测重复、冲突和合规问题
        </Paragraph>

        <Divider />

        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            label="上传文件"
            name="files"
            valuePropName="fileList"
            getValueFromEvent={(e) => (Array.isArray(e) ? e : e?.fileList)}
          >
            <Dragger
              accept=".doc,.docx,.pdf,.txt"
              multiple
              beforeUpload={() => false}
              onChange={handleFileChange}
              fileList={fileList}
              maxCount={50}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
              <p className="ant-upload-hint">
                支持 .doc/.docx/.pdf/.txt 格式，最多 50 个文件
              </p>
            </Dragger>
          </Form.Item>

          <Form.Item label="操作人" name="operator">
            <Input placeholder="请输入操作人账号" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                icon={<RobotOutlined />}
                disabled={!fileList.length}
              >
                开始批量巡检
              </Button>
              <Button onClick={() => setFileList([])}>清空文件</Button>
            </Space>
          </Form.Item>
        </Form>

        {/* 加载状态 */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>
              <Text>正在批量巡检中，请稍候...</Text>
            </div>
            <Progress percent={-1} status="active" />
          </div>
        )}

        {/* 巡检结果 */}
        {result && !loading && (
          <>
            <Divider />

            <Result
              status="success"
              title="批量巡检完成"
              subTitle={`共检查 ${result.result.total_files} 个文件，发现 ${result.result.total_problems} 个问题`}
            />

            {/* 文件结果表格 */}
            <Table
              columns={columns}
              dataSource={result.result.file_results}
              rowKey="file_path"
              pagination={false}
              style={{ marginTop: 16 }}
            />
          </>
        )}
      </Card>
    </div>
  )
}