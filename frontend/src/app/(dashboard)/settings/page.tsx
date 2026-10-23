import { getCurrentUser } from '@/actions/auth'
import {
  NoAccessResult,
  SettingsOverviewClient,
  SettingsPageHeader,
  type SettingsOverviewEntry,
  type SettingsOverviewGroup,
} from '@/components/settings'
import { PERM } from '@/lib/permissions/codes'
import { getPermissionsSnapshot } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

/**
 * 系统管理概览。
 *
 * 与其他业务模块的数据看板不同，这里展示的是**当前账号有权限使用的后台功能**：
 * - 服务端按权限码过滤，无权限的条目不下发，客户端不再判断；
 * - 每项标注「可管理 / 仅查看」，由对应的 `:manage` 权限码决定；
 * - 一项权限都没有（URL 直连）时显示无权限页。
 */
export default async function SettingsPage() {
  const user = await getCurrentUser()

  if (!user) {
    return <NoAccessResult title="请先登录" subTitle="登录后即可访问系统管理。" />
  }

  const snapshot = await getPermissionsSnapshot()
  if (!snapshot) {
    return (
      <NoAccessResult subTitle="暂时无法获取你的权限信息，请刷新页面或联系管理员。" />
    )
  }

  const granted = new Set(snapshot.permissions)
  const isSuperuser = snapshot.isSuperuser
  const can = (codes: readonly string[]) => isSuperuser || codes.some((code) => granted.has(code))

  const accountItems: SettingsOverviewEntry[] = []
  if (can([PERM.userRead])) {
    accountItems.push({
      key: 'users',
      title: '用户管理',
      description: '创建本地账号、重置密码、解绑飞书与查看登录来源。',
      path: '/settings/users',
      icon: 'team',
      manageable: can([PERM.userManage]),
    })
  }
  if (can([PERM.roleRead, PERM.grantRead, PERM.grantManage])) {
    accountItems.push({
      key: 'permission',
      title: '权限管理',
      description: '维护角色、给用户授权与数据范围，查看角色 / 授权 / 权限目录。',
      path: '/settings/permission',
      icon: 'security',
      manageable: can([PERM.roleManage, PERM.grantManage]),
    })
  }

  const auditItems: SettingsOverviewEntry[] = []
  if (can([PERM.auditRead])) {
    auditItems.push(
      {
        key: 'login-logs',
        title: '登录记录',
        description: '查询成功 / 失败的登录记录，定位异常登录来源。',
        path: '/settings/login-logs',
        icon: 'login',
        manageable: false,
      },
      {
        key: 'audit',
        title: '操作记录',
        description: '按操作者、对象与时间检索后台操作留痕。',
        path: '/settings/audit',
        icon: 'audit',
        manageable: false,
      },
    )
  }

  const platformItems: SettingsOverviewEntry[] = []
  if (can([PERM.configRead])) {
    platformItems.push({
      key: 'platform',
      title: '系统配置',
      description: 'LLM 模型配置、飞书设置与 Livzon Skill。',
      path: '/settings/platform',
      icon: 'config',
      manageable: can([PERM.configManage]),
    })
  }
  if (can([PERM.opsRead])) {
    platformItems.push(
      {
        key: 'menus',
        title: '菜单管理',
        description: '配置顶部导航与左侧菜单的显隐、排序权重与可见权限。',
        path: '/settings/menus',
        icon: 'menu',
        manageable: can([PERM.opsManage]),
      },
      {
        key: 'ops',
        title: '系统运维',
        description: '服务健康、资源监控、定时任务、接口启停与运行日志。',
        path: '/settings/ops',
        icon: 'ops',
        manageable: can([PERM.opsManage]),
      },
    )
  }

  const groups: SettingsOverviewGroup[] = []
  if (accountItems.length) groups.push({ key: 'account', title: '账号与权限', items: accountItems })
  if (auditItems.length) groups.push({ key: 'audit', title: '审计与安全', items: auditItems })
  if (platformItems.length) groups.push({ key: 'platform', title: '平台与运维', items: platformItems })

  if (!groups.length) {
    return (
      <NoAccessResult subTitle="当前账号没有可用的系统管理功能，请联系管理员为你的账号授权。" />
    )
  }

  const count = groups.reduce((total, group) => total + group.items.length, 0)

  return (
    <div className="settings-scope settings-enter mx-auto max-w-[1320px] md:px-6 md:py-6">
      <SettingsPageHeader
        title="系统管理"
        description={
          isSuperuser
            ? '当前账号为超级管理员，可访问全部后台功能。'
            : `当前账号可访问 ${count} 项后台功能，未授权的功能不会显示。`
        }
      />
      <SettingsOverviewClient groups={groups} />
    </div>
  )
}
