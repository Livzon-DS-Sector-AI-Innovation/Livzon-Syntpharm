'use client'

import type { ReactNode } from 'react'
import styles from './registration-ui.module.css'

/**
 * 注册管理模块统一页头：品牌紫方形图标 + 标题 + 副标题 + 右侧操作区
 */
export function RegistrationPageHeader({
  icon,
  title,
  sub,
  actions,
}: {
  icon: ReactNode
  title: string
  sub?: ReactNode
  actions?: ReactNode
}) {
  return (
    <div className={styles.pageHead}>
      <div>
        <div className={styles.pageTitle}>
          <div className={styles.titleIco}>{icon}</div>
          <h1>{title}</h1>
        </div>
        {sub ? <div className={styles.pageSub}>{sub}</div> : null}
      </div>
      {actions ? <div className={styles.headActions}>{actions}</div> : null}
    </div>
  )
}
