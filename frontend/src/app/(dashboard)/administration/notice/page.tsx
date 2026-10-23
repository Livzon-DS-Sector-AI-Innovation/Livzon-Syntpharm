import { DevelopmentNotice, RegulationClient } from '@/components/administration'

export default async function NoticePage() {
  return (
    <>
      <DevelopmentNotice feature="公告通知" />
      <RegulationClient />
    </>
  )
}
