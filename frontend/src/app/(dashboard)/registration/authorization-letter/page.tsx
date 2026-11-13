import {
  fetchAuthorizationLetterFilterOptionsServer,
  fetchAuthorizationLettersServer,
  fetchProductsServer,
} from '@/actions/registration'
import { AuthorizationLetterClient } from '@/components/registration'

export const dynamic = 'force-dynamic'

export default async function AuthorizationLetterPage() {
  const [lettersRes, productsRes, filterOptionsRes] = await Promise.all([
    fetchAuthorizationLettersServer({ page: 1, page_size: 20 }),
    fetchProductsServer(),
    fetchAuthorizationLetterFilterOptionsServer(),
  ])

  return (
    <AuthorizationLetterClient
      initialLetters={lettersRes.items}
      initialTotal={lettersRes.total}
      products={productsRes}
      initialFilterOptions={filterOptionsRes}
    />
  )
}
