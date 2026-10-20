/**
 * 行政模块「开发中」提示条。
 *
 * 行政模块后端接口尚未实现（无 administration schema / 路由），
 * 相关页面数据不可用，统一展示此提示，避免用户误判为系统故障。
 */
export default function DevelopmentNotice({ feature }: { feature?: string }) {
  return (
    <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-[13px] leading-5 text-amber-800">
      <span className="font-medium">{feature ? `${feature}功能开发中` : '该功能开发中'}</span>
      ：行政管理模块后端接口尚未上线，页面数据暂不可用。
    </div>
  )
}
