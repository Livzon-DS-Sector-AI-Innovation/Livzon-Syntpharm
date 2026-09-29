'use client'

/**
 * 「项目知识库」弹窗版：从「新建报告」里点「上传/管理资料」打开，
 * 用户在本弹窗内建库 / 上传 / 看解析进度，关闭后回到新建报告弹窗（表单内容不丢）。
 *
 * 与独立页面共用 KnowledgeBaseManager，行为一致。
 */
import { Modal } from 'antd'
import { KnowledgeBaseManager } from './KnowledgeBaseManager'

interface Props {
  open: boolean
  projectId: string
  /** 关闭弹窗 */
  onClose: () => void
  /** 弹窗内发生建库/上传/删除等写操作：父组件据此刷新知识库摘要 */
  onChanged: () => void
}

export function KnowledgeBaseModal({ open, projectId, onClose, onChanged }: Props) {
  return (
    <Modal
      open={open}
      title="项目知识库"
      width={960}
      footer={null}
      destroyOnClose
      mask={{ closable: false }}
      onCancel={onClose}
      styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
    >
      <KnowledgeBaseManager projectId={projectId} variant="modal" onChanged={onChanged} />
    </Modal>
  )
}
