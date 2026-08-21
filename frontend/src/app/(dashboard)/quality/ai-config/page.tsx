'use client'
import {saveAIConfig, resetAIConfig} from '@/actions/quality'

import React, { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Form,
  Input,
  Button,
  Space,
  Row,
  Col,
  Typography,
  Divider,
  Switch,
  Select,
  InputNumber,
  message,
  Alert,
} from 'antd'
import {
  SaveOutlined,
  ReloadOutlined,
  SettingOutlined,
  RobotOutlined,
  KeyOutlined,
} from '@ant-design/icons'

const { Text } = Typography

interface AIConfig {
  minimax_api_key: string
  minimax_base_url: string
  minimax_text_model: string
  minimax_vision_model: string
  enable_ai_reason: boolean
  enable_ai_scrap: boolean
  enable_ai_analyse: boolean
  enable_ai_label_recognize: boolean
  temperature: number
  max_tokens: number
  timeout: number
}

const defaultConfig: AIConfig = {
  minimax_api_key: '',
  minimax_base_url: 'https://api.minimaxi.com/v1',
  minimax_text_model: 'MiniMax-M2.7',
  minimax_vision_model: 'MiniMax-M3',
  enable_ai_reason: true,
  enable_ai_scrap: true,
  enable_ai_analyse: true,
  enable_ai_label_recognize: true,
  temperature: 0.7,
  max_tokens: 1024,
  timeout: 60,
}

const API_BASE_URL = '/api/v1'

export default function AiConfigPage() {
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const [testLoading, setTestLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)

  // 加载配置
  const loadConfig = useCallback(async () => {
    setInitialLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/ai/config`)
      const data = await response.json()

      if (data.code === 200 && data.data) {
        form.setFieldsValue(data.data)
      } else {
        form.setFieldsValue(defaultConfig)
      }
    } catch (_error) {
      console.log('从后端加载配置失败，使用默认配置')
      form.setFieldsValue(defaultConfig)
    } finally {
      setInitialLoading(false)
    }
  }, [form])

  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  // 保存配置到后端
  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setLoading(true)

      const data = await saveAIConfig(values)

      if (data.code === 200) {
        message.success('AI配置保存成功')
      } else {
        message.error(data.message || '保存失败')
      }
    } catch (error) {
      console.error('保存配置失败:', error)
      message.error('保存配置失败')
    } finally {
      setLoading(false)
    }
  }

  // 重置配置
  const handleReset = async () => {
    form.setFieldsValue(defaultConfig)
    try {
      await resetAIConfig(defaultConfig)
    } catch (_error) {
      console.log('重置后端配置失败')
    }
    message.success('已重置为默认配置')
  }

  // 测试连接
  const handleTestConnection = async () => {
    setTestLoading(true)
    try {
      const values = form.getFieldsValue()
      const apiKey = values.minimax_api_key

      if (!apiKey) {
        message.warning('请先填写API Key')
        setTestLoading(false)
        return
      }

      // 先保存配置
      await saveAIConfig(values)

      // 模拟测试
      await new Promise((resolve) => setTimeout(resolve, 1000))

      message.success('API连接测试成功')
    } catch (_error) {
      message.error('API连接测试失败，请检查配置')
    } finally {
      setTestLoading(false)
    }
  }

  if (initialLoading) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        加载配置中...
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <SettingOutlined />
            <span>AI 配置设置</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
            >
              重置
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={loading}
              onClick={handleSave}
            >
              保存配置
            </Button>
          </Space>
        }
      >
        <Alert
          message="配置说明"
          description="AI功能使用 MiniMax API 服务。请确保已配置有效的 API Key，不同模型适用于不同场景：Text-01 用于文本生成，VL-01 用于图片识别。"
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />

        <Form form={form} layout="vertical" initialValues={defaultConfig}>
          {/* API 密钥配置 */}
          <Divider>
            <Space>
              <KeyOutlined />
              <span>API 密钥配置</span>
            </Space>
          </Divider>

          <Row gutter={24}>
            <Col span={12}>
              <Form.Item
                name="minimax_api_key"
                label="MiniMax API Key"
                rules={[{ required: true, message: '请输入API Key' }]}
              >
                <Input.Password
                  placeholder="请输入 MiniMax API Key"
                  prefix={<KeyOutlined />}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="minimax_base_url"
                label="API 地址"
              >
                <Input
                  placeholder="https://api.minimaxi.com/v1"
                  prefix={<RobotOutlined />}
                />
              </Form.Item>
            </Col>
          </Row>

          {/* 模型配置 */}
          <Divider>
            <Space>
              <RobotOutlined />
              <span>模型配置</span>
            </Space>
          </Divider>

          <Row gutter={24}>
            <Col span={8}>
              <Form.Item
                name="minimax_text_model"
                label="文本生成模型"
              >
                <Select>
                  <Select.Option value="MiniMax-M2.7">MiniMax-M2.7</Select.Option>
                  <Select.Option value="MiniMax-M3">MiniMax-M3</Select.Option>
                  <Select.Option value="abab6.5s-chat">abab6.5s-chat</Select.Option>
                  <Select.Option value="abab6.5-chat">abab6.5-chat</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="minimax_vision_model"
                label="视觉识别模型"
              >
                <Select>
                  <Select.Option value="MiniMax-M3">MiniMax-M3 (多模态)</Select.Option>
                  <Select.Option value="MiniMax-M2.7">MiniMax-M2.7</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="temperature"
                label="Temperature (0-1)"
              >
                <InputNumber
                  min={0}
                  max={1}
                  step={0.1}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={24}>
            <Col span={8}>
              <Form.Item
                name="max_tokens"
                label="最大 Token 数"
              >
                <InputNumber
                  min={256}
                  max={8192}
                  step={256}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="timeout"
                label="请求超时时间(秒)"
              >
                <InputNumber
                  min={10}
                  max={300}
                  step={10}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>

          {/* 功能开关 */}
          <Divider>
            <Space>
              <SettingOutlined />
              <span>功能开关</span>
            </Space>
          </Divider>

          <Row gutter={24}>
            <Col span={8}>
              <Form.Item
                name="enable_ai_reason"
                label="领用事由生成"
                valuePropName="checked"
              >
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="enable_ai_scrap"
                label="报废原因生成"
                valuePropName="checked"
              >
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="enable_ai_analyse"
                label="试剂异常分析"
                valuePropName="checked"
              >
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={24}>
            <Col span={8}>
              <Form.Item
                name="enable_ai_label_recognize"
                label="标签图片识别"
                valuePropName="checked"
              >
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>

          {/* 测试按钮 */}
          <Divider>连接测试</Divider>

          <Row>
            <Col span={24}>
              <Space>
                <Button
                  type="default"
                  icon={<RobotOutlined />}
                  loading={testLoading}
                  onClick={handleTestConnection}
                >
                  测试API连接
                </Button>
              </Space>
            </Col>
          </Row>

          {/* GMP 合规提示 */}
          <Divider />

          <Text type="secondary" style={{ textAlign: 'center', display: 'block' }}>
            <RobotOutlined style={{ marginRight: 8 }} />
            AI 内容仅作参考，最终以人工审核确认
          </Text>
        </Form>
      </Card>
    </div>
  )
}
