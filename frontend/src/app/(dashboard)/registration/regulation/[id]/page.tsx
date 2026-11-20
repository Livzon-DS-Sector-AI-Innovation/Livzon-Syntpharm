import RegulationDetailClient from '@/components/registration/RegulationDetailClient'

/**
 * 法规文件详情：id 由客户端 `useParams()` 读取，页面只做服务端外壳。
 */
export default function RegulatoryDocumentDetailPage() {
  return <RegulationDetailClient />
}