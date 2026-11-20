'use client'

import { Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { translationDownloadUrl } from '@/lib/api/client/docx-translator'
import type { DocxTranslationFileResult } from '@/types/docx-translator'
import { IconDownload, IconFile } from '../RegistrationIcons'
import styles from './docx-translator.module.css'

export interface ResultRow extends DocxTranslationFileResult {
  job_id: string
}

interface Props {
  rows: ResultRow[]
  onRetry: (fileName: string) => void
  retrying: boolean
  /** 点击下载后回调：任务状态页签据此把已取走的任务归档 */
  onDownloaded?: () => void
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

/**
 * 任务完成后的下载区：三列（文件 / 状态 / 下载），成功率与失败原因收进文件名副行，
 * 让下载按钮直接可见，不需要再点「查看结果」。
 */
export function DocxTranslatorResultTable({ rows, onRetry, retrying, onDownloaded }: Props) {
  const columns: ColumnsType<ResultRow> = [
    {
      title: '文件',
      dataIndex: 'filename',
      width: '44%',
      align: 'left',
      render: (value: string, record) => (
        <div className={styles.docCell}>
          <span
            className={`${styles.docIco} ${styles.docIcoSm} ${
              record.success ? styles.docIcoOk : styles.docIcoRisk
            }`}
          >
            {IconFile}
          </span>
          <span className={styles.docCellText}>
            <span className={styles.docName} title={value}>
              {value}
            </span>
            {record.success ? (
              <span className={styles.docMeta}>
                <span className={`${RATE_CLASS[rateTone(record.success_rate)]} ${styles.docMetaRate}`}>
                  成功率 {record.success_rate.toFixed(1)}%
                </span>
                {record.total_units > 0 && (
                  <span>
                    {' · '}
                    {record.translated_units}/{record.total_units} 段
                  </span>
                )}
                {record.success_rate < 90 && (
                  <span className={styles.docMetaWarn}> · 成功率偏低，请人工复核</span>
                )}
              </span>
            ) : (
              <span className={styles.docMetaRisk} title={record.error ?? ''}>
                失败原因：{record.error || '未知错误'}
              </span>
            )}
          </span>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'success',
      width: '16%',
      align: 'center',
      render: (success: boolean) =>
        success ? (
          <span className={`${styles.pill} ${styles.pillOk}`}>成功</span>
        ) : (
          <span className={`${styles.pill} ${styles.pillRisk}`}>失败</span>
        ),
    },
    {
      title: '下载',
      key: 'actions',
      width: '40%',
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
                className={`${styles.dlBtn} ${
                  output.kind === 'bilingual' ? styles.dlBtnBrand : styles.dlBtnInfo
                }`}
                href={translationDownloadUrl(record.job_id, output.file_index)}
                download={output.filename}
                onClick={onDownloaded}
              >
                {IconDownload}
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
    />
  )
}

export default DocxTranslatorResultTable
