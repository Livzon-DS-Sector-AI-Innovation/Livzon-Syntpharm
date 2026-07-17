'use client'

import React, { useState, useEffect } from 'react'
import {
  Card,
  Form,
  Input,
  Button,
  Upload,
  message,
  Space,
  Divider,
  Alert,
  Spin,
  Result,
  Steps,
  Tag,
  List,
  Typography,
} from 'antd'
import {
  UploadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  FileTextOutlined,
  RobotOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import { singleCheck } from '@/actions/sop-ai'
import { CheckTaskResponse, CheckProblem, RiskLevel } from '@/types/sop-ai'

const { Title, Text, Paragraph } = Typography

type SopAiPreviewPageProps = Record<string, never>

/**
 * 单文件预审页面
 */
export default function SopAiPreviewPage(props: SopAiPreviewPageProps) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<CheckTaskResponse | null>(null)
  const [fileList, setFileList] = useState<any[]>([])

  // 处理文件选择
  const handleFileChange = (info: any) => {
    setFileList(info.fileList.slice(-1))
  }

  // 提交预审
  const handleSubmit = async (values: any) => {
    if (!fileList.length) {
      message.error('请选择文件')
      return
    }

    setLoading(true)
    setResult(null)

    try {
      const response = await singleCheck({
        file_path: fileList[0]?.originFileObj?.path || values.file_path,
        file_name: fileList[0]?.name || values.file_name,
        check_type: 'single',
        operator: values.operator,
      })

      setResult(response)
    } catch (error: any) {
      message.error(error.message || '预审失败')
    } finally {
      setLoading(false)
    }
  }

  // 获取风险标签颜色
  const getRiskTagColor = (level?: RiskLevel) => {
    switch (level) {
      case 'high':
        return 'red'
      case 'medium':
        return 'orange'
      case 'low':
        return 'green'
      default:
        return 'default'
    }
  }

  return (
    <div className="sop-ai-preview-page">
      <Card>
        <Title level={4}>单文件预审</Title>
        <Paragraph type="secondary">
          上传 SOP 文件进行 AI 辅助预审，检测重复、冲突和合规问题
        </Paragraph>

        <Divider />

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ check_type: 'single' }}
        >
          <Form.Item
            label="上传文件"
            name="file"
            valuePropName="fileList"
            getValueFromEvent={(e) => (Array.isArray(e) ? e : e?.fileList)}
          >
            <Upload
              accept=".doc,.docx,.pdf,.txt"
              maxCount={1}
              beforeUpload={() => false}
              onChange={handleFileChange}
              fileList={fileList}
            >
              <Button icon={<UploadOutlined />}>选择文件</Button>
            </Upload>
          </Form.Item>

          <Form.Item label="文件路径" name="file_path" rules={[{ required: true }]}>
            <Input placeholder="请输入文件路径" />
          </Form.Item>

          <Form.Item label="文件名" name="file_name" rules={[{ required: true }]}>
            <Input placeholder="请输入文件名" />
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
              >
                开始预审
              </Button>
            </Space>
          </Form.Item>
        </Form>

        {/* 加载状态 */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>
              <Text>正在预审中，请稍候...</Text>
            </div>
          </div>
        )}

        {/* 预审结果 */}
        {result && !loading && (
          <>
            <Divider />

            {result.status === 'completed' ? (
              <Result
                status="success"
                title="预审完成"
                subTitle={`发现问题 ${result.result?.total_problems || 0} 个`}
              />
            ) : result.status === 'failed' ? (
              <Result
                status="error"
                title="预审失败"
                subTitle={result.message}
              />
            ) : null}

            {/* 问题统计 */}
            {result.result && (
              <div style={{ marginTop: 16 }}>
                <Space size="large">
                  <Tag color="red">
                    高风险: {result.result.risk_high}
                  </Tag>
                  <Tag color="orange">
                    中风险: {result.result.risk_medium}
                  </Tag>
                  <Tag color="green">
                    低风险: {result.result.risk_low}
                  </Tag>
                </Space>
              </div>
            )}

            {/* 问题列表 */}
            {result.result?.problems && result.result.problems.length > 0 && (
              <div style={{ marginTop: 24 }}>
                <Title level={5}>问题明细</Title>
                <List
                  bordered
                  dataSource={result.result.problems}
                  renderItem={(item: CheckProblem) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={
                          item.risk_level === 'high' ? (
                            <CloseCircleOutlined style={{ fontSize: 24, color: '#ff4d4f' }} />
                          ) : item.risk_level === 'medium' ? (
                            <WarningOutlined style={{ fontSize: 24, color: '#fa8c16' }} />
                          ) : (
                            <CheckCircleOutlined style={{ fontSize: 24, color: '#52c41a' }} />
                          )
                        }
                        title={
                          <Space>
                            <Text strong>{item.problem_type}</Text>
                            <Tag color={getRiskTagColor(item.risk_level)}>
                              {item.risk_level}
                            </Tag>
                          </Space>
                        }
                        description={
                          <div>
                            <div>位置: {item.location}</div>
                            <div>描述: {item.description}</div>
                            {item.suggestion && (
                              <div>建议: {item.suggestion}</div>
                            )}
                          </div>
                        }
                      />
                    </List.Item>
                  )}
                />
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  )
}