import { useEffect, useState } from 'react'
import styles from './FanOfCards.module.css'

const CARD_W = 88
const CARD_H = 150

interface Props {
  cards: { id: number }[]
  onPick: (id: number) => void
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
  const N = cards.length
  if (N === 0) return null

  return (
    <div className={styles.fanContainer}>
      {cards.map((card, i) => {
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
            onClick={() => onPick(card.id)}
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
