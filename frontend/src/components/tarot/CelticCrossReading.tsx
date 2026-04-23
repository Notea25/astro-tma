import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { useQuery } from '@tanstack/react-query'
import { tarotApi } from '@/services/api'
import { useHaptic } from '@/hooks/useTelegram'
import type { TarotCardDetail } from '@/types'
import styles from './CelticCrossReading.module.css'

const POSITION_NAMES: Record<number, string> = {
  1: 'Суть',
  2: 'Препятствие',
  3: 'Идеал',
  4: 'Основа',
  5: 'Прошлое',
  6: 'Будущее',
  7: 'Вы сами',
  8: 'Окружение',
  9: 'Надежды и страхи',
  10: 'Исход',
}

interface Props {
  readingId: number
  cards: TarotCardDetail[]
}

export function CelticCrossReading({ readingId, cards }: Props) {
  const { impact } = useHaptic()
  const [zoomedIdx, setZoomedIdx] = useState<number | null>(null)

  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ['tarot', 'interpret', readingId],
    queryFn: () => tarotApi.interpret(readingId),
    staleTime: Infinity,
    gcTime: Infinity,
    retry: 1,
  })

  // Close lightbox on Escape
  useEffect(() => {
    if (zoomedIdx === null) return
    const h = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setZoomedIdx(null)
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [zoomedIdx])

  if (isPending) {
    return (
      <div className={styles.readingWrap}>
        <div className={styles.loader}>
          Астролог читает ваш расклад…
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className={styles.readingWrap}>
        <div className={styles.errorBlock}>
          <p>Не удалось подготовить интерпретацию.</p>
          <button className={styles.retryBtn} onClick={() => refetch()}>
            Попробовать снова
          </button>
        </div>
      </div>
    )
  }

  const openZoom = (idx: number) => {
    impact('light')
    setZoomedIdx(idx)
  }

  const zoomedCard = zoomedIdx !== null ? cards[zoomedIdx] : null

  return (
    <div className={styles.readingWrap}>
      <p className={styles.subtitle}>Интерпретация расклада</p>

      {data.positions.map((pos) => {
        const idx = pos.n - 1
        const card = cards[idx]
        if (!card) return null
        return (
          <div key={pos.n} className={styles.block}>
            <div
              className={`${styles.cardThumb} ${card.reversed ? styles.cardThumbReversed : ''}`}
              onClick={() => openZoom(idx)}
            >
              {card.image_url ? (
                <img src={card.image_url} alt={card.name_ru} loading="lazy" />
              ) : (
                <div className={styles.cardEmoji}>{card.emoji}</div>
              )}
            </div>
            <div className={styles.blockBody}>
              <span className={styles.posLabel}>
                Позиция {pos.n}
              </span>
              <h4 className={styles.posTitle}>{POSITION_NAMES[pos.n]}</h4>
              <div className={styles.cardName}>
                {card.name_ru}
                {card.reversed && (
                  <span className={styles.reversed}> · перевёрнута</span>
                )}
              </div>
              <p className={styles.narrative}>{pos.narrative}</p>
            </div>
          </div>
        )
      })}

      {data.summary && (
        <div className={styles.summaryBlock}>
          <h3 className={styles.summaryTitle}>✦ Итог ✦</h3>
          <p className={styles.summaryText}>{data.summary}</p>
        </div>
      )}

      {/* Lightbox */}
      {zoomedCard &&
        createPortal(
          <div
            className={styles.lightbox}
            onClick={() => setZoomedIdx(null)}
          >
            <div
              className={`${styles.lightboxCard} ${zoomedCard.reversed ? styles.reversed : ''}`}
            >
              {zoomedCard.image_url ? (
                <img src={zoomedCard.image_url} alt={zoomedCard.name_ru} />
              ) : (
                <div className={styles.cardEmoji}>{zoomedCard.emoji}</div>
              )}
            </div>
            <div className={styles.lightboxCaption}>
              {zoomedCard.name_ru}
              {zoomedCard.reversed ? ' · перевёрнута' : ''}
            </div>
          </div>,
          document.body,
        )}
    </div>
  )
}
