import { fetchAuthorizationLettersServer, fetchProductsServer } from '@/actions/registration'
import { AuthorizationLetterClient } from '@/components/registration'

export const dynamic = 'force-dynamic'

export default async function AuthorizationLetterPage() {
  const [lettersRes, productsRes] = await Promise.all([
    fetchAuthorizationLettersServer({ page: 1, page_size: 20 }),
    fetchProductsServer(),
  ])

  return (
    <>
      <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)] mb-4">授权书</h1>
      <AuthorizationLetterClient
        initialLetters={lettersRes?.data || []}
        initialTotal={lettersRes?.meta?.total || 0}
        products={productsRes?.data || []}
      />
    </>
  )
}
