import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
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
      <motion.div
        className={styles.cardInner}
        animate={{ rotateY: revealed ? 180 : 0 }}
        transition={{
          duration: 0.65,
          ease: [0.22, 0.61, 0.36, 1],
        }}
      >
        <div className={styles.cardBackFace}>{back}</div>
        <div className={styles.cardFrontFace}>{front}</div>
      </motion.div>
    </div>
  )
}
