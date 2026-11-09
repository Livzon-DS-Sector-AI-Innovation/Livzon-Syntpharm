'use client'

import { Button, Input, Tag, Typography } from 'antd'

interface Props {
  value: string
  onChange: (value: string) => void
  maxChars: number
  /** 无管理权限时只读，只展示不能改 */
  readOnly?: boolean
  /** 项目视图下继承到的全局指南，用于「留空即继承」提示 */
  inherited?: string
  /** 项目视图：文案改为「项目内可单独覆盖全局」 */
  scope?: 'global' | 'project'
}

/** 三条常见写法，点一下追加到输入框：比空提示更能让人知道该写什么 */
const EXAMPLES = [
  '面向客户汇报：少用缩写，术语首次出现给出中英文全称',
  '每页讲稿控制在 180 字以内，先结论后依据',
  '不用口语化表达，语气正式，不出现「我们觉得」这类措辞',
]

/**
 * 文稿提示词指南：一段自然语言规则，会拼进每次讲稿生成的提示词。
 *
 * 优先级：单次指令 > 项目 script_guide > 全局指南，所以项目视图要提示可覆盖。
 */
export default function AiGuidePanel({ value, onChange, maxChars, readOnly, inherited, scope = 'global' }: Props) {
  const isProject = scope === 'project'
  const append = (text: string) => {
    if (readOnly) return
    const next = value.trim() ? `${value.trim()}\n${text}` : text
    onChange(next.slice(0, maxChars))
  }

  return (
    <div className="flex flex-col gap-3">
      <Typography.Paragraph className="!mb-0 !text-[12px] !text-[#5D5B54]">
        {isProject
          ? '这些要求只对这个项目生效，生成讲稿时会一起交给 AI；留空则沿用全局要求。单次改写时输入的指令优先级最高。'
          : '这里写的要求会用在每次生成讲稿时；具体项目可以单独覆盖，单次改写指令优先级最高。'}
      </Typography.Paragraph>

      <div className="relative">
        <Input.TextArea
          value={value}
          onChange={(event) => onChange(event.target.value.slice(0, maxChars))}
          readOnly={readOnly}
          autoSize={{ minRows: 8, maxRows: 16 }}
          maxLength={maxChars}
          showCount
          placeholder={
            isProject
              ? '留空就沿用全局要求。例如：本项目面向审评专家，术语按药典写法，句子短。'
              : '例如：面向客户汇报，术语首次出现给出全称，每页讲稿 150 字以内。'
          }
          className={readOnly ? '!bg-[#FAFAF9]' : undefined}
        />
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        <Typography.Text type="secondary" className="text-[11px]">
          示例：
        </Typography.Text>
        {EXAMPLES.map((example) => (
          <Tag
            key={example}
            className={`!m-0 !text-[11px] ${readOnly ? '' : 'cursor-pointer hover:!border-[#5645D4]'}`}
            onClick={() => append(example)}
          >
            {example}
          </Tag>
        ))}
      </div>

      {isProject && (
        <div className="rounded-lg bg-[#FAFAF9] px-3 py-2 text-[11px] leading-relaxed text-[#5D5B54]">
          项目可以单独覆盖全局要求；留空就沿用全局。
          {inherited ? (
            <>
              <br />
              当前全局要求：{inherited.length > 80 ? `${inherited.slice(0, 80)}…` : inherited}
            </>
          ) : (
            <>
              <br />
              当前还没有全局要求。
            </>
          )}
        </div>
      )}

      {readOnly && (
        <Button size="small" disabled block>
          没有修改权限，请联系管理员
        </Button>
      )}
    </div>
  )
}