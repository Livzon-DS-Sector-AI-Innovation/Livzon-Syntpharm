'use client'

export default function ITTicketPage() {

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden">
      <div className="px-6 py-3 border-b border-gray-200 bg-blue-50 shrink-0">
        <div className="flex items-start gap-2 text-sm text-blue-800">
          <svg className="w-5 h-5 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="space-y-1">
            <p className="font-medium">报修温馨提示：</p>
            <p>1. 请尽量详细描述故障现象，便于技术人员快速定位问题。</p>
            <p>2. 如涉及硬件故障，请备注设备服务编号或电脑的计算机名。</p>
            <p>3. 紧急故障请直接在飞书联系 IT。</p>
          </div>
        </div>
      </div>

      <iframe
        src="https://j0eukrlohu.feishu.cn/share/base/form/shrcnK683zCX3MJNouST7a6PIUh"
        className="w-full flex-1 border-none"
        title="飞书 IT 服务工单表单"
      />
    </div>
  )
}
