'use client'

export default function ShippingApplicationPage() {

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden">
      <div className="px-6 py-3 border-b border-gray-200 bg-blue-50 shrink-0">
        <div className="flex items-start gap-2 text-sm text-blue-800">
          <svg className="w-5 h-5 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="space-y-1">
            <p className="font-medium">寄件温馨提示：</p>
            <p>1. 请准确填写收件地址、金额和部门领导，行政审批人为骆经理，申请通过后才能寄件。</p>
            <p>2. 寄件物品需符合公司邮寄规定，违禁品不予寄送。</p>
            <p>3. 贵重或紧急物品请提前联系行政部确认物流方式。</p>
          </div>
        </div>
      </div>

      <iframe
        src="https://j0eukrlohu.feishu.cn/share/base/form/shrcnpClyTLZinw7KSKA7aeTziM"
        className="w-full flex-1 border-none"
        title="飞书寄件申请表单"
      />
    </div>
  )
}
