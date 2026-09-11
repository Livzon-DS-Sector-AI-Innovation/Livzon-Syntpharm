import { render, screen } from '@testing-library/react'
import { StatsCards } from '../StatsCards'
import type { EquipmentStatistics } from '@/types/equipment/generated-bridge'

describe('StatsCards', () => {
  const mockStats: EquipmentStatistics = {
    total: 100,
    by_status: {
      '在用': 80,
      '备用': 5,
      '维修中': 5,
      '停用': 5,
      '报废': 5,
    },
    by_category: {},
    by_location: {},
  }

  it('should render the "Scrapped" (报废) card with correct count', () => {
    render(<StatsCards statistics={mockStats} />)
    
    // 查找包含“报废”文本的元素（getByText 找不到时会直接抛错）
    const scrappedCard = screen.getByText('报废')
    expect(scrappedCard).toBeTruthy()

    // 查找对应的数量 5
    const scrappedCount = screen.getByText('5')
    expect(scrappedCount).toBeTruthy()
  })
})
