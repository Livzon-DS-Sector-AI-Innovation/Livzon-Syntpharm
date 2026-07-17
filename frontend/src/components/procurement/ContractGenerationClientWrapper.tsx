'use client'

import dynamic from 'next/dynamic'
import type { ContractCategory } from '@/types/procurement'

const ContractGenerationClient = dynamic(
  () => import('./ContractGenerationClient').then(mod => ({ default: mod.ContractGenerationClient })),
  { ssr: false }
)

type ContractGenerationClientWrapperProps = {
  category: ContractCategory
  categoryLabel: string
}

export default function ContractGenerationClientWrapper(props: ContractGenerationClientWrapperProps) {
  return <ContractGenerationClient {...props} />
}
