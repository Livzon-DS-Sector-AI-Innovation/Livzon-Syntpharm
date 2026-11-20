/**
 * 注册管理模块共享内联 SVG 图标（stroke 风格，与注册概览设计原型一致）
 */
import type { ReactNode } from 'react'

export function RegSvg({ size = 16, children }: { size?: number; children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {children}
    </svg>
  )
}

export const IconTitleDoc = (
  <RegSvg size={18}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <path d="M14 2v6h6M9 13h6M9 17h4" />
  </RegSvg>
)
export const IconRefresh = (
  <RegSvg size={14}>
    <path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" />
  </RegSvg>
)
export const IconPlus = (
  <RegSvg size={14}>
    <path d="M12 5v14M5 12h14" />
  </RegSvg>
)
export const IconShieldCheck = (
  <RegSvg size={17}>
    <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1 1 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
    <path d="m9 12 2 2 4-4" />
  </RegSvg>
)
export const IconGlobe = (
  <RegSvg size={17}>
    <circle cx="12" cy="12" r="10" />
    <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20M2 12h20" />
  </RegSvg>
)
export const IconLink = (
  <RegSvg size={17}>
    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
  </RegSvg>
)
export const IconCert = (
  <RegSvg size={17}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <path d="M14 2v6h6M9 15l6-6M9 9h.01M15 15h.01" />
  </RegSvg>
)
export const IconList = (
  <RegSvg size={14}>
    <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
  </RegSvg>
)
export const IconWarn = (
  <RegSvg size={14}>
    <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <path d="M12 9v4M12 17h.01" />
  </RegSvg>
)
export const IconCheckCircle = (
  <RegSvg size={15}>
    <circle cx="12" cy="12" r="10" />
    <path d="m9 12 2 2 4-4" />
  </RegSvg>
)
export const IconGrid = (
  <RegSvg size={15}>
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <path d="M3 9h18M9 21V9" />
  </RegSvg>
)
export const IconFile = (
  <RegSvg size={15}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <path d="M14 2v6h6" />
  </RegSvg>
)
export const IconBulb = (
  <RegSvg size={15}>
    <path d="M12 2a7 7 0 0 1 7 7c0 2.4-1.2 4.5-3 5.7V17a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1v-2.3C6.2 13.5 5 11.4 5 9a7 7 0 0 1 7-7z" />
    <path d="M9 21h6" />
  </RegSvg>
)
export const IconBook = (
  <RegSvg size={15}>
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5z" />
    <path d="M8 7h8M8 11h5" />
  </RegSvg>
)
export const IconActivity = (
  <RegSvg size={15}>
    <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
  </RegSvg>
)
export const IconSliders = (
  <RegSvg size={15}>
    <path d="M20 7h-9M14 17H5" />
    <circle cx="17" cy="17" r="3" />
    <circle cx="7" cy="7" r="3" />
  </RegSvg>
)
export const IconEdit = (
  <RegSvg size={15}>
    <path d="M12 20h9M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z" />
  </RegSvg>
)
export const IconCheckSquare = (
  <RegSvg size={15}>
    <path d="m12 15 2 2 4-4" />
    <rect x="3" y="3" width="18" height="18" rx="2" />
  </RegSvg>
)
export const IconMessage = (
  <RegSvg size={15}>
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </RegSvg>
)
export const IconFlask = (
  <RegSvg size={15}>
    <path d="M10 2v7.31L4.16 19.16A2 2 0 0 0 5.93 22h12.14a2 2 0 0 0 1.77-2.84L14 9.31V2" />
    <path d="M8.5 2h7" />
    <path d="M7 16h10" />
  </RegSvg>
)
export const IconClock = (
  <RegSvg size={17}>
    <circle cx="12" cy="12" r="10" />
    <path d="M12 6v6l4 2" />
  </RegSvg>
)
export const IconTrash = (
  <RegSvg size={14}>
    <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
  </RegSvg>
)
export const IconCheck = (
  <RegSvg size={12}>
    <path d="m5 13 4 4L19 7" />
  </RegSvg>
)
export const IconUpload = (
  <RegSvg size={14}>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <path d="m17 8-5-5-5 5M12 3v12" />
  </RegSvg>
)
export const IconDownload = (
  <RegSvg size={14}>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <path d="m7 10 5 5 5-5M12 15V3" />
  </RegSvg>
)
