'use client'

export default function VehicleRequestPage() {

  return (
    <div className="flex flex-col min-h-screen">
      {/* 飞书表单嵌入 */}
      <div className="flex-1 px-6 py-4">
        <iframe
          src="https://j0eukrlohu.feishu.cn/share/base/form/shrcnFLV3uTwGYB2t6kDEbxJfre"
          className="w-full border-none rounded-lg"
          style={{ height: '85vh' }}
          title="飞书用车申请表单"
        />
      </div>

      {/* 分隔符 */}
      <div className="flex items-center gap-3 px-6 py-6">
        <div className="flex-1 border-t border-gray-400" />
        <div className="w-1.5 h-1.5 rounded-full bg-gray-400" />
        <div className="flex-1 border-t border-gray-400" />
      </div>

      {/* 用车数据标题 */}
      <div className="flex items-center justify-between px-6 py-4 bg-white">
        <h2 className="text-lg font-semibold">用车数据</h2>
      </div>

      {/* 飞书数据视图嵌入 */}
      <div className="px-6 pb-6 bg-white">
        <iframe
          src="https://j0eukrlohu.feishu.cn/share/base/view/shrcnNq9B8CXiLibG96wRLqVdrg"
          className="w-full border-none rounded-lg"
          style={{ height: '600px' }}
          title="飞书用车申请数据视图"
        />
      </div>
    </div>
  )
}
