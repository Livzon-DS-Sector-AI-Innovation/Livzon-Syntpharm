'use client'

import { Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { translationDownloadUrl } from '@/lib/api/client/docx-translator'
import type { DocxTranslationFileResult } from '@/types/docx-translator'
import styles from './docx-translator.module.css'

export interface ResultRow extends DocxTranslationFileResult {
  job_id: string
}

interface Props {
  rows: ResultRow[]
  onRetry: (fileName: string) => void
  retrying: boolean
}

function rateTone(rate: number): 'ok' | 'warn' | 'risk' {
  if (rate >= 90) return 'ok'
  if (rate >= 70) return 'warn'
  return 'risk'
}

const RATE_CLASS = {
  ok: styles.rateOk,
  warn: styles.rateWarn,
  risk: styles.rateRisk,
}
const BAR_CLASS = {
  ok: styles.rateBarOk,
  warn: styles.rateBarWarn,
  risk: styles.rateBarRisk,
}

export function DocxTranslatorResultTable({ rows, onRetry, retrying }: Props) {
  const columns: ColumnsType<ResultRow> = [
    {
      title: '文件名',
      dataIndex: 'filename',
      width: '30%',
      align: 'center',
      render: (value: string) => (
        <span className={styles.cellEllipsis} title={value}>
          {value}
        </span>
      ),
    },
    {
      title: '段落成功率',
      dataIndex: 'success_rate',
      width: '26%',
      align: 'center',
      render: (value: number, record) => {
        if (!record.success) {
          return <span className={`${styles.rateValue} ${styles.numCell} ${styles.rateNone}`}>—</span>
        }
        const tone = rateTone(value)
        return (
          <div className={styles.rateCell}>
            <span className={`${styles.rateValue} ${styles.numCell} ${RATE_CLASS[tone]}`}>
              {value.toFixed(1)}%
            </span>
            <span className={styles.rateBar}>
              <span
                className={`${styles.rateBarFill} ${BAR_CLASS[tone]}`}
                style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
              />
            </span>
            {value < 90 && <span className={styles.warnLine}>成功率偏低，请人工复核</span>}
          </div>
        )
      },
    },
    {
      title: '状态',
      dataIndex: 'success',
      width: '18%',
      align: 'center',
      render: (success: boolean) =>
        success ? (
          <span className={`${styles.pill} ${styles.pillOk}`}>成功</span>
        ) : (
          <span className={`${styles.pill} ${styles.pillRisk}`}>失败</span>
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: '26%',
      align: 'center',
      render: (_, record) => {
        if (!record.success) {
          return (
            <button
              type="button"
              className={styles.retryLink}
              disabled={retrying}
              onClick={() => onRetry(record.filename)}
            >
              重试此文件
            </button>
          )
        }
        const outputs = record.outputs || []
        return (
          <div className={styles.dlButtons}>
            {outputs.map(output => (
              <a
                key={output.file_index}
                className={styles.dlBtn}
                href={translationDownloadUrl(record.job_id, output.file_index)}
                download={output.filename}
              >
                {output.kind === 'bilingual' ? '双语版' : '译文版'}
              </a>
            ))}
          </div>
        )
      },
    },
  ]

  return (
    <Table
      className={styles.resultTable}
      rowKey="filename"
      pagination={false}
      columns={columns}
      dataSource={rows}
      tableLayout="fixed"
      rowClassName={record => (!record.success ? styles.failRow : '')}
      expandable={{
        // 失败行常显原因：受控展开，不显示展开箭头
        expandedRowKeys: rows.filter(item => !item.success && item.error).map(item => item.filename),
        showExpandColumn: false,
        rowExpandable: record => !record.success && Boolean(record.error),
        expandedRowRender: record => (
          <div className={styles.failReason}>
            <span>失败原因：{record.error}</span>
            <button
              type="button"
              className={styles.retryLink}
              disabled={retrying}
              onClick={() => onRetry(record.filename)}
            >
              重试此文件
            </button>
          </div>
        ),
      }}
    />
  )
}

export default DocxTranslatorResultTable
