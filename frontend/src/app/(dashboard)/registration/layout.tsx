import { RegistrationBreadcrumb } from './RegistrationBreadcrumb'

export default function RegistrationLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <>
      <RegistrationBreadcrumb />
      {children}
    </>
  )
}
