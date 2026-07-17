import { EnergyType } from '@/types/energy'

export const energyTypeLabels: Record<EnergyType, { text: string; color: string }> = {
  electricity: { text: '电力', color: 'blue' },
  water: { text: '水', color: 'cyan' },
  steam: { text: '气体', color: 'orange' },
  natural_gas: { text: '天然气', color: 'purple' },
}
