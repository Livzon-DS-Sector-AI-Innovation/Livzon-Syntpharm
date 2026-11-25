'use client'

import { useEffect, useState } from 'react'
import styles from './review-progress.module.css'

/** 通用审评流程 10 个节点（名称、顺序、大小写与设计稿逐字一致，不绑定具体品种） */
const NODES = [
  { x: 70, label: 'CDE通知核查' },
  { x: 200, label: '企业向CFDI确认核查' },
  { x: 330, label: 'CFDI告知企业核查' },
  { x: 460, label: '开展核查' },
  { x: 590, label: '企业递交核查报告' },
  { x: 720, label: 'CFDI递交报告给CDE' },
  { x: 850, label: '预计发补' },
  { x: 980, label: '发补递交' },
  { x: 1110, label: 'CDE发补审评' },
]

/** 节点间流动虚线（依次串联 10 个节点，避开圆体） */
const FLOW_LINES = [
  'M91 52 L179 52',
  'M221 52 L309 52',
  'M351 52 L439 52',
  'M481 52 L569 52',
  'M611 52 L699 52',
  'M741 52 L829 52',
  'M871 52 L959 52',
  'M1001 52 L1089 52',
  'M1131 52 L1234 52',
]

const TOTAL = NODES.length + 1 // 9 个编号节点 + 1 个终点「获批」

/**
 * 审评节点导轨：抽象通用示意（10 节点单行 + 流动虚线 + 轮回点亮动画）。
 * 节点 10「获批」为大圆 + 奖章图标（非数字 10）。
 * 轮回时序：0.6s 起依次点亮（每 0.8s 一个）→ 走过的保持 → 全亮停 1.6s → 同时清空 → 1s 后重来。
 */
export function ReviewFlowGuide() {
  const [lit, setLit] = useState(0)

  useEffect(() => {
    // 减弱动效：不启动 JS 轮回动画（CSS 侧同样全部关闭）
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const timers: number[] = []
    let i = 0
    const step = () => {
      if (i < TOTAL) {
        i += 1
        setLit(i)
        timers.push(window.setTimeout(step, 800))
      } else {
        timers.push(
          window.setTimeout(() => {
            // 全亮停一拍后，10 个节点【同时】清空，再从头循环
            setLit(0)
            i = 0
            timers.push(window.setTimeout(step, 1000))
          }, 1600),
        )
      }
    }
    timers.push(window.setTimeout(step, 600))
    return () => timers.forEach(t => clearTimeout(t))
  }, [])

  return (
    <section className={styles.flowCard} aria-label="审评节点说明">
      <div className={styles.fcHead}>
        <div>
          <div className={styles.fcEyebrow}>审评节点</div>
          <div className={styles.fcTitle}>受理后共 10 个节点</div>
          <div className={styles.fcDesc}>
            通用审评流程示意：下方表格中分段进度条的每一段，对应这里的一个节点
          </div>
        </div>
      </div>
      <div className={styles.fcScroll}>
        <svg
          className={styles.fcArt}
          viewBox="0 0 1330 116"
          fill="none"
          aria-hidden="true"
          preserveAspectRatio="xMidYMid meet"
        >
          {FLOW_LINES.map((d, idx) => (
            <path key={idx} className={styles.flowline} d={d} stroke="#A5A0EE" strokeWidth="1.8" />
          ))}

          {NODES.map((n, idx) => (
            <g key={idx} className={`${styles.seq} ${lit > idx ? styles.on : ''}`}>
              <circle className={styles.glow} cx={n.x} cy="52" r="26" />
              <circle className={styles.dot} cx={n.x} cy="52" r="21" />
              <text className={styles.num} x={n.x} y="57.5" textAnchor="middle">
                {idx + 1}
              </text>
              <text x={n.x} y="90" textAnchor="middle" fontSize="14" fill="#4D5266">
                {n.label}
              </text>
            </g>
          ))}

          {/* 节点 10「获批」：大圆（r=26）+ 奖章图标，终点仪式感 */}
          <g className={`${styles.seq} ${styles.final} ${lit > 9 ? styles.on : ''}`}>
            <circle className={styles.glow} cx="1260" cy="52" r="34" />
            <circle className={styles.dot} cx="1260" cy="52" r="26" />
            <g className={styles.medal} transform="translate(1260,50) scale(1.45)">
              <circle cx="0" cy="-1.5" r="5.5" />
              <path d="M-3.4 2.6 L-5.4 9 L-1.8 7.6 L0 10.4 L1.8 7.6 L5.4 9 L3.4 2.6" />
            </g>
            <text x="1260" y="90" textAnchor="middle" fontSize="15" fontWeight="700" fill="#4D5266">
              获批
            </text>
          </g>

          {/* 四角星点缀 */}
          <path
            d="M1300 12l1.5 3.5 3.5 1.5-3.5 1.5-1.5 3.5-1.5-3.5-3.5-1.5 3.5-1.5z"
            fill="#C9CDF2"
          />
        </svg>
      </div>
    </section>
  )
}
