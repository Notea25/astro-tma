/**
 * Wraps premium content. Shows paywall overlay if user isn't premium
 * and hasn't purchased the specific product.
 */

import { motion } from 'framer-motion'
import { usePayment } from '@/hooks/usePayment'
import { useAppStore } from '@/stores/app'

interface PremiumGateProps {
  productId: string
  productName: string
  stars: number
  children: React.ReactNode
  locked: boolean
}

export function PremiumGate({ productId, productName, stars, children, locked }: PremiumGateProps) {
  const { purchase, loading } = usePayment()

  if (!locked) return <>{children}</>

  return (
    <div className="premium-gate">
      <div className="premium-gate__blur">{children}</div>
      <motion.div
        className="premium-gate__overlay"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="premium-gate__badge">✦ Premium</div>
        <h3 className="premium-gate__title">{productName}</h3>
        <p className="premium-gate__desc">Разблокируйте доступ за звёзды Telegram</p>
        <button
          className="btn-stars"
          onClick={() => purchase(productId)}
          disabled={loading}
        >
          {loading ? '⏳ Открываем...' : `⭐ ${stars} Stars`}
        </button>
      </motion.div>
    </div>
  )
}
