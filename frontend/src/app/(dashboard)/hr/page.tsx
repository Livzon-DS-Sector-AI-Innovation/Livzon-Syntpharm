import HrHomeClient from '@/components/hr/HrHomeClient'

export const dynamic = 'force-dynamic'

/** 人事管理首页：数据与交互都在客户端组件，页面只做服务端外壳。 */
export default function HrPage() {
  return <HrHomeClient />
}