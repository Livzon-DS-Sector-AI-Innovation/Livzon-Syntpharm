import HazardDetailClient from '@/components/safety/HazardDetailClient'

/**
 * 隐患台账详情：id 由客户端 `useParams()` 读取，页面只做服务端外壳。
 */
export default function HazardLedgerDetailPage() {
  return <HazardDetailClient />
}