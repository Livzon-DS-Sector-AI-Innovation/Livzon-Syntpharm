import {
  DomesticApproval,
  OverseasApproval,
  InternationalReview,
  CoppCertificate,
  WcCertificate,
  LedgerSummary,
  ReviewingDrug,
} from '@/types/registration-ledger'

export type { DomesticApproval, OverseasApproval, InternationalReview, CoppCertificate, WcCertificate, LedgerSummary, ReviewingDrug } from '@/types/registration-ledger'

// Registration Ledger — GET-only API functions
// POST (import) functions are in src/actions/registration-ledger.ts

// ── API Functions (GET-only) ───────────────────────────────────────

async function fetchApi<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data
}

const API_BASE = '/api/v1/registration/ledger'

export const fetchDomesticApprovals = () => fetchApi<DomesticApproval[]>(`${API_BASE}/domestic-approvals`)
export const fetchOverseasApprovals = () => fetchApi<OverseasApproval[]>(`${API_BASE}/overseas-approvals`)
export const fetchInternationalReviews = () => fetchApi<InternationalReview[]>(`${API_BASE}/international-reviews`)
export const fetchCoppCertificates = () => fetchApi<CoppCertificate[]>(`${API_BASE}/copp-certificates`)
export const fetchWcCertificates = () => fetchApi<WcCertificate[]>(`${API_BASE}/wc-certificates`)
export const fetchLedgerSummary = () => fetchApi<LedgerSummary>(`${API_BASE}/summary`)
export const fetchReviewingDrugs = () => fetchApi<ReviewingDrug[]>(`${API_BASE}/reviewing`)

// Export functions (open in new tab)
export const exportDomesticApprovals = () => window.open(`${API_BASE}/domestic-approvals/export`, '_blank')
export const exportOverseasApprovals = () => window.open(`${API_BASE}/overseas-approvals/export`, '_blank')
export const exportInternationalReviews = () => window.open(`${API_BASE}/international-reviews/export`, '_blank')
export const exportCoppCertificates = () => window.open(`${API_BASE}/copp-certificates/export`, '_blank')
export const exportWcCertificates = () => window.open(`${API_BASE}/wc-certificates/export`, '_blank')