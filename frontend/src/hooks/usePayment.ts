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
        // Telegram tells us "paid" right when the user taps "Pay", but the
        // successful_payment webhook + our DB write take a beat after that.
        // Wait briefly so the next refetch sees the new purchase row;
        // otherwise React Query refetches too fast, /horoscope returns 402
        // and the gate stays locked even though the user paid.
        await new Promise((r) => setTimeout(r, 1500))
        // Force the entitlement query to refetch so PremiumGate sees the
        // new purchase, plus invalidate everything else so any 402'd
        // queries retry and succeed.
        await queryClient.invalidateQueries({ queryKey: ['my-purchases'] })
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
