import type { ReactNode } from 'react'
import styles from './FlipCard.module.css'

interface Props {
  revealed: boolean
  width: number
  height: number
  back: ReactNode
  front: ReactNode
  onClick?: () => void
}

export function FlipCard({ revealed, width, height, back, front, onClick }: Props) {
  return (
    <div
      className={styles.cardPerspective}
      style={{ width, height }}
      onClick={onClick}
    >
      <div className={`${styles.cardInner} ${revealed ? styles.revealed : ''}`}>
        <div className={styles.cardBackFace}>{back}</div>
        <div className={styles.cardFrontFace}>{front}</div>
      </div>
    </div>
  )
}
