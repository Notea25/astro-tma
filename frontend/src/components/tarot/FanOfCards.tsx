import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { FAN_CARD_H, FAN_CARD_W } from '@/data/spread-config'
import styles from './FanOfCards.module.css'

export interface FanCard {
  id: number
  gone?: boolean
}

interface Props {
  cards: FanCard[]
  onPick: (id: number, rect: DOMRect, angleDeg: number) => void
  renderCard: () => React.ReactNode
}

export function FanOfCards({ cards, onPick, renderCard }: Props) {
  const [viewW, setViewW] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth : 375,
  )

  useEffect(() => {
    const h = () => setViewW(window.innerWidth)
    window.addEventListener('resize', h)
    return () => window.removeEventListener('resize', h)
  }, [])

  const spreadDeg = Math.min(200, Math.max(110, viewW * 0.164 + 36))

  // Active (non-gone) cards form the visible arc.
  const active = cards.filter((card) => !card.gone)
  const N = active.length

  return (
    <div className={styles.fanContainer}>
      {active.map((card, i) => {
        const t = N === 1 ? 0.5 : i / (N - 1)
        const angleDeg = spreadDeg * (t - 0.5)
        const delay = i * 0.032
        return (
          <motion.div
            key={card.id}
            className={styles.fanCardWrapper}
            initial={{ opacity: 0, y: 72, scale: 0.82, rotate: angleDeg }}
            animate={{ opacity: 1, y: 0, scale: 1, rotate: angleDeg }}
            whileHover={{ y: -34, scale: 1.035, zIndex: 200 }}
            whileTap={{ scale: 0.96 }}
            transition={{
              delay,
              duration: 0.52,
              ease: [0.22, 0.61, 0.36, 1],
            }}
            style={
              {
                '--fan-card-half': `${FAN_CARD_W / 2}px`,
                zIndex: i + 1,
              } as React.CSSProperties
            }
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect()
              onPick(card.id, rect, angleDeg)
            }}
          >
            <div
              className={styles.fanCardInner}
              style={{ width: FAN_CARD_W, height: FAN_CARD_H }}
            >
              {renderCard()}
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
