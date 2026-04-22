import { useEffect, useState } from 'react'
import styles from './FanOfCards.module.css'

const CARD_W = 88
const CARD_H = 150

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

  const spreadDeg = Math.min(120, Math.max(55, viewW * 0.082 + 18))

  // Active (non-gone) cards — they form the visible arc
  const active = cards.filter(c => !c.gone)
  const N = active.length
  if (N === 0) return null

  return (
    <div className={styles.fanContainer}>
      {active.map((card, i) => {
        const t = N === 1 ? 0.5 : i / (N - 1)
        const angleDeg = spreadDeg * (t - 0.5)
        const delay = i * 0.038
        return (
          <div
            key={card.id}
            className={styles.fanCardWrapper}
            style={
              {
                '--angle': `${angleDeg}deg`,
                '--appear-delay': `${delay}s`,
                zIndex: i + 1,
              } as React.CSSProperties
            }
            onClick={(e) => {
              const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
              onPick(card.id, rect, angleDeg)
            }}
          >
            <div
              className={styles.fanCardInner}
              style={{ width: CARD_W, height: CARD_H }}
            >
              {renderCard()}
            </div>
          </div>
        )
      })}
    </div>
  )
}
