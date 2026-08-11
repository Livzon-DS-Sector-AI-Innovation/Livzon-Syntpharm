'use client'

import { useState } from 'react'
import { Upload, Button, Input, Space, Card, message, Spin } from 'antd'
import { UploadOutlined, RobotOutlined } from '@ant-design/icons'
import { parseExperimentRecord, parseProcessParameters } from '@/actions/ai-parse'

interface AIParserToolbarProps {
  parseType: 'lab_confirmation' | 'scale_up' | 'doe_data' | 'impurity_report'
  onDataParsed: (data: any) => void
}

export function AIParserToolbar({ parseType, onDataParsed }: AIParserToolbarProps) {
  const [loading, setLoading] = useState(false)
  const [textMode, setTextMode] = useState(false)
  const [textContent, setTextContent] = useState('')

  const handleFileUpload = async (file: File) => {
    setLoading(true)
    try {
      const result = await parseExperimentRecord(file, parseType)
      message.success('AI 解析成功！')
      onDataParsed(result)
    } catch (error) {
      message.error('解析失败，请检查文件格式')
    } finally {
      setLoading(false)
    }
    return false
  }

  const handleTextParse = async () => {
    if (!textContent.trim()) return
    setLoading(true)
    try {
      const result = await parseProcessParameters(textContent, parseType)
      message.success('AI 提取成功！')
      onDataParsed(result)
    } catch (error) {
      message.error('提取失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card 
      size="small" 
      title={<Space><RobotOutlined /> AI 智能辅助解析</Space>}
      style={{ marginBottom: 16, borderColor: '#1890ff', borderStyle: 'dashed' }}
    >
      <Spin spinning={loading}>
        <Space direction="vertical" style={{ width: '100%' }}>
          {!textMode ? (
            <Space>
              <Upload beforeUpload={handleFileUpload} maxCount={1}>
                <Button icon={<UploadOutlined />}>上传实验记录</Button>
              </Upload>
              <Button type="link" onClick={() => setTextMode(true)}>或粘贴文本</Button>
            </Space>
          ) : (
            <Space direction="vertical" style={{ width: '100%' }}>
              <Input.TextArea 
                rows={3} 
                placeholder="在此粘贴实验记录文本..." 
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
              />
              <Space>
                <Button type="primary" onClick={handleTextParse}>开始解析</Button>
                <Button onClick={() => setTextMode(false)}>取消</Button>
              </Space>
            </Space>
          )}
        </Space>
      </Spin>
    </Card>
  )
}
