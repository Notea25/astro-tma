/**
 * Payment hook — wraps invoice creation + Stars payment in one call.
 * Invalidates React Query cache on successful payment so UI auto-updates.
 */

import { useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { paymentsApi } from '@/services/api'
import { useStarsPayment } from './useTelegram'

interface UsePaymentResult {
  purchase: (productId: string) => Promise<boolean>
  loading: boolean
  error: string | null
}

export function usePayment(): UsePaymentResult {
  const { pay } = useStarsPayment()
  const queryClient = useQueryClient()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const purchase = useCallback(async (productId: string): Promise<boolean> => {
    setLoading(true)
    setError(null)
    try {
      // 1. Get invoice URL from our backend
      const { invoice_url } = await paymentsApi.createInvoice(productId)

      // 2. Open Telegram native payment sheet
      const paid = await pay(invoice_url)

      if (paid) {
        // 3. Invalidate all queries so premium content shows up immediately
        await queryClient.invalidateQueries()
      }
      return paid
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Payment failed')
      return false
    } finally {
      setLoading(false)
    }
  }, [pay, queryClient])

  return { purchase, loading, error }
}
