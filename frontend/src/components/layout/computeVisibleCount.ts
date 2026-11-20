/**
 * 顶栏模块 Tab 的折叠计算。
 *
 * 给定容器可视宽度、每个 Tab 的右边缘偏移，算出能完整显示几个 Tab，
 * 以及是否还有 Tab 需要收进「更多」下拉。
 *
 * 抽成纯函数的原因：这是整块布局里唯一有边界条件的分支，独立出来才能直接对着用例核对，
 * 也不必为了验证去挂载组件。
 */

export interface OverflowFitInput {
  /** 容器可视宽度（nav.clientWidth，不含 margin） */
  containerWidth: number
  /** 各 Tab 右边缘相对容器左缘的偏移，必须单调递增 */
  itemOffsets: number[]
  /** 「更多」按钮宽度（含左右 padding） */
  moreWidth: number
}

export interface OverflowFit {
  /** 完整显示的 Tab 个数 */
  visibleCount: number
  /** 是否还有 Tab 需要收进「更多」 */
  showMore: boolean
}

/**
 * 计算规则：
 * 1. 没有 Tab → 全部为 0；
 * 2. 全部放得下 → 不出「更多」，也不为它预留宽度（否则会白白少显示一个 Tab）；
 * 3. 放不下 → 先给「更多」预留宽度，再取能放下的最大个数；
 * 4. 容器窄到连「首项 + 更多」都放不下时退化：仍显示首项并保留「更多」入口，
 *    保证被折叠的模块始终可达（md 断点下容器仍有 ~330px，现实中不会触发）。
 *
 * 用例（itemOffsets 省略外层的 moreWidth 参数说明）：
 * - `{ containerWidth: 800, itemOffsets: [], moreWidth: 60 }` → `{ 0, false }`
 * - `{ containerWidth: 1000, itemOffsets: [100, 200, 300], moreWidth: 60 }` → `{ 3, false }`
 * - `{ containerWidth: 300, itemOffsets: [100, 240], moreWidth: 60 }` → `{ 2, false }`
 *   （恰好放下，不该为了「更多」反而少显示一个）
 * - `{ containerWidth: 320, itemOffsets: [100, 200, 300], moreWidth: 60 }` → `{ 2, true }`
 * - `{ containerWidth: 300, itemOffsets: [260, 300], moreWidth: 60 }` → `{ 1, true }`
 * - `{ containerWidth: 80, itemOffsets: [100], moreWidth: 60 }` → `{ 1, true }`（退化分支）
 */
export function computeVisibleCount({
  containerWidth,
  itemOffsets,
  moreWidth,
}: OverflowFitInput): OverflowFit {
  const total = itemOffsets.length
  if (total === 0) return { visibleCount: 0, showMore: false }

  if (itemOffsets[total - 1] <= containerWidth) {
    return { visibleCount: total, showMore: false }
  }

  const capacity = containerWidth - moreWidth
  let visibleCount = 0
  for (const offset of itemOffsets) {
    if (offset > capacity) break
    visibleCount += 1
  }

  return { visibleCount: Math.max(1, Math.min(visibleCount, total)), showMore: true }
}