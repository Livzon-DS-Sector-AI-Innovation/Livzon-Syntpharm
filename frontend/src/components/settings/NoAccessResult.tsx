'use client'

import { Result } from 'antd'

export function NoAccessResult() {
  return (
    <Result
      status="403"
      title="无权访问"
      subTitle="只有管理员可以管理用户、LLM 模型配置与 Livzon Skill。"
    />
  )
}
