import { useState, useRef, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { FanOfCards, type FanCard } from './FanOfCards'
import { FlipCard } from './FlipCard'
import { CelticCrossReading } from './CelticCrossReading'
import { TarotCardBack } from './TarotCardBack'
import { useHaptic } from '@/hooks/useTelegram'
import type { TarotCardDetail } from '@/types'
import styles from './CelticCrossFlow.module.css'

const CARD_W = 88
const CARD_H = 150
const LAYOUT_W = 720
const LAYOUT_H = 720
const INITIAL_FAN_COUNT = 15

const SLOTS: { slot: number; x: number; y: number; label: string; rotate?: number }[] = [
  { slot: 1,  x: 200, y: 280, label: 'Суть' },
  { slot: 2,  x: 200, y: 280, label: 'Препятствие', rotate: 90 },
  { slot: 3,  x: 200, y: 100, label: 'Идеал' },
  { slot: 4,  x: 200, y: 460, label: 'Основа' },
  { slot: 5,  x: 40,  y: 280, label: 'Прошлое' },
  { slot: 6,  x: 360, y: 280, label: 'Будущее' },
  { slot: 7,  x: 560, y: 560, label: 'Вы сами' },
  { slot: 8,  x: 560, y: 380, label: 'Окружение' },
  { slot: 9,  x: 560, y: 200, label: 'Надежды' },
  { slot: 10, x: 560, y: 20,  label: 'Исход' },
]

type Phase = 'idle' | 'shuffle' | 'fan' | 'reading' | 'complete'

interface FlyCardState {
  left: number
  top: number
  dx: number
  dy: number
  startRot: number
  targetIdx: number
}

interface PlacedState {
  justLanded: boolean
}

interface Props {
  readingId: number
  cards: TarotCardDetail[]
  onNewReading: () => void
}

export function CelticCrossFlow({ readingId, cards, onNewReading }: Props) {
  const { impact } = useHaptic()
  const [phase, setPhase] = useState<Phase>('idle')
  const [fanCards, setFanCards] = useState<FanCard[]>([])
  const [placed, setPlaced] = useState<Map<number, PlacedState>>(new Map())
  const [flyCard, setFlyCard] = useState<FlyCardState | null>(null)
  const [revealedCount, setRevealedCount] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [scale, setScale] = useState(1)

  const areaRef = useRef<HTMLDivElement>(null)
  const slotRefs = useRef<Map<number, HTMLDivElement>>(new Map())
  const detailRef = useRef<HTMLDivElement>(null)

  const placedCount = placed.size
  const isAllPlaced = placedCount >= SLOTS.length
  const isAllRevealed = revealedCount >= SLOTS.length

  // Responsive scale for the 720×720 spread container
  useEffect(() => {
    const el = areaRef.current
    if (!el) return
    const update = () => {
      const avail = el.clientWidth
      if (!avail) return
      setScale(Math.min(1, avail / LAYOUT_W))
    }
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  /* ── Phase transitions ─────────────────────────────────────────────── */

  const handleDeckClick = useCallback(() => {
    if (phase !== 'idle') return
    impact('medium')
    setPhase('shuffle')
    setTimeout(() => {
      setFanCards(
        Array.from({ length: INITIAL_FAN_COUNT }, (_, i) => ({ id: i })),
      )
      setPhase('fan')
    }, 2400)
  }, [phase, impact])

  const handleFanPick = useCallback(
    (id: number, rect: DOMRect, startRot: number) => {
      if (flyCard || placedCount >= SLOTS.length) return

      const targetEl = slotRefs.current.get(placedCount)
      if (!targetEl) return
      const targetRect = targetEl.getBoundingClientRect()

      impact('light')

      // Mark picked card as gone — fan redistributes remaining cards
      setFanCards((prev) =>
        prev.map((c) => (c.id === id ? { ...c, gone: true } : c)),
      )

      // Compute fly start/target centers
      const startCenterX = rect.left + rect.width / 2
      const startCenterY = rect.top + rect.height / 2
      const targetCenterX = targetRect.left + targetRect.width / 2
      const targetCenterY = targetRect.top + targetRect.height / 2

      setFlyCard({
        left: startCenterX - CARD_W / 2,
        top: startCenterY - CARD_H / 2,
        dx: targetCenterX - startCenterX,
        dy: targetCenterY - startCenterY,
        startRot,
        targetIdx: placedCount,
      })
    },
    [flyCard, placedCount, impact],
  )

  const handleFlyEnd = useCallback(() => {
    if (!flyCard) return
    const idx = flyCard.targetIdx
    setPlaced((prev) => new Map(prev).set(idx, { justLanded: true }))
    setFlyCard(null)
    // Clear justLanded flag after land animation completes
    setTimeout(() => {
      setPlaced((prev) => {
        const next = new Map(prev)
        next.set(idx, { justLanded: false })
        return next
      })
    }, 500)
  }, [flyCard])

  // fan → reading once all 10 placed
  useEffect(() => {
    if (phase === 'fan' && isAllPlaced) {
      const t = setTimeout(() => setPhase('reading'), 700)
      return () => clearTimeout(t)
    }
  }, [phase, isAllPlaced])

  // reading → complete once all revealed
  useEffect(() => {
    if (phase === 'reading' && isAllRevealed) {
      const t = setTimeout(() => setPhase('complete'), 500)
      return () => clearTimeout(t)
    }
  }, [phase, isAllRevealed])

  const handleOverlayClick = useCallback(() => {
    if (phase !== 'reading') return
    if (revealedCount >= SLOTS.length) return
    impact('medium')
    setRevealedCount((n) => n + 1)
  }, [phase, revealedCount, impact])

  const handleSlotClick = useCallback(
    (idx: number) => {
      if (phase !== 'complete') return
      if (idx >= revealedCount) return
      setSelected(idx)
      setTimeout(() => {
        detailRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        })
      }, 200)
    },
    [phase, revealedCount],
  )

  const handleRestart = useCallback(() => {
    impact('medium')
    setPhase('idle')
    setFanCards([])
    setPlaced(new Map())
    setFlyCard(null)
    setRevealedCount(0)
    setSelected(null)
    onNewReading()
  }, [impact, onNewReading])

  /* ── Render helpers ────────────────────────────────────────────────── */

  const prompt =
    phase === 'idle'
      ? 'Нажмите на колоду, чтобы перемешать карты'
      : phase === 'shuffle'
        ? 'Карты перемешиваются…'
        : phase === 'fan' && !isAllPlaced
          ? placedCount === 0
            ? 'Выберите карту, которую чувствуете'
            : `Выбрано ${placedCount} из ${SLOTS.length}`
          : phase === 'reading' && !isAllRevealed
            ? 'Нажмите в любом месте, чтобы открыть карту'
            : ''

  const containerPadded = phase === 'idle' || phase === 'shuffle' || phase === 'fan'

  return (
    <div
      className={`${styles.flowContainer} ${containerPadded ? '' : styles.noPad}`}
    >
      <p className={styles.prompt} style={{ minHeight: 20 }}>
        {prompt}
      </p>

      {/* ── Slot grid (always visible) ── */}
      <div className={styles.spreadArea} ref={areaRef}>
        <div
          className={styles.spreadFit}
          style={{ width: LAYOUT_W * scale, height: LAYOUT_H * scale }}
        >
          <div
            className={styles.spreadContainer}
            style={{
              width: LAYOUT_W,
              height: LAYOUT_H,
              transform: `scale(${scale})`,
            }}
          >
            {SLOTS.map((slot, idx) => {
              const isPlaced = placed.has(idx)
              const isRevealed = idx < revealedCount
              const justLanded = placed.get(idx)?.justLanded
              const isCross = !!slot.rotate
              const card = cards[idx]

              return (
                <div
                  key={slot.slot}
                  className={`${styles.slot} ${isCross ? styles.slotCross : ''}`}
                  ref={(el) => {
                    if (el) slotRefs.current.set(idx, el)
                    else slotRefs.current.delete(idx)
                  }}
                  style={{
                    left: slot.x,
                    top: slot.y,
                    width: CARD_W,
                    height: CARD_H,
                  }}
                  onClick={() =>
                    phase === 'complete' && isRevealed && handleSlotClick(idx)
                  }
                >
                  <div
                    className={styles.rotor}
                    style={
                      isCross
                        ? { transform: `rotate(${slot.rotate}deg)` }
                        : undefined
                    }
                  >
                    {!isPlaced ? (
                      <div className={styles.placeholder} />
                    ) : (
                      <div className={justLanded ? styles.cardLand : ''}>
                        <FlipCard
                          revealed={isRevealed}
                          width={CARD_W}
                          height={CARD_H}
                          back={<TarotCardBack />}
                          front={
                            card?.image_url ? (
                              <img
                                src={card.image_url}
                                alt={card.name_ru}
                                style={{
                                  width: '100%',
                                  height: '100%',
                                  objectFit: 'cover',
                                  display: 'block',
                                  transform: card.reversed
                                    ? 'rotate(180deg)'
                                    : undefined,
                                }}
                              />
                            ) : (
                              <div
                                style={{
                                  width: '100%',
                                  height: '100%',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  fontSize: 28,
                                  background: 'rgba(212,178,84,0.06)',
                                  border: '1.5px solid rgba(212,178,84,0.45)',
                                }}
                              >
                                {card?.emoji}
                              </div>
                            )
                          }
                        />
                      </div>
                    )}
                  </div>
                  {(!isCross || !isPlaced) && (
                    <span
                      className={`${styles.slotLabel} ${isCross ? styles.slotLabelInside : ''}`}
                    >
                      {slot.label}
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* ── Deck (idle + shuffle phases) ── */}
      {(phase === 'idle' || phase === 'shuffle') && (
        <div className={styles.deckWrap}>
          <div
            className={`${styles.deck} ${phase === 'shuffle' ? styles.deckShuffling : ''}`}
            onClick={handleDeckClick}
          >
            {[3, 2, 1, 0].map((i) => (
              <div
                key={i}
                className={styles.deckLayer}
                style={{
                  left: i * 2,
                  top: i * 2,
                  zIndex: 4 - i,
                  opacity: 0.55 + i * 0.12,
                }}
              >
                <TarotCardBack />
              </div>
            ))}
            <div
              className={styles.deckLayer}
              style={{ left: 7, top: 7, zIndex: 10 }}
            >
              <TarotCardBack />
            </div>
          </div>
          {phase === 'idle' && (
            <span className={styles.deckLabel}>КОЛОДА</span>
          )}
        </div>
      )}

      {/* ── Fan (fan phase only) ── */}
      {phase === 'fan' && fanCards.filter((c) => !c.gone).length > 0 && (
        <FanOfCards
          cards={fanCards}
          onPick={handleFanPick}
          renderCard={() => <TarotCardBack />}
        />
      )}

      {/* ── Flying card ── */}
      {flyCard && (
        <div
          className={styles.flyingCard}
          style={
            {
              left: flyCard.left,
              top: flyCard.top,
              width: CARD_W,
              height: CARD_H,
              '--dx': `${flyCard.dx}px`,
              '--dy': `${flyCard.dy}px`,
              '--start-rot': `${flyCard.startRot}deg`,
              '--final-scale': `${scale}`,
            } as React.CSSProperties
          }
          onAnimationEnd={handleFlyEnd}
        >
          <TarotCardBack />
        </div>
      )}

      {/* ── Reading-phase tap-anywhere overlay ── */}
      {phase === 'reading' && !isAllRevealed && (
        <div className={styles.revealOverlay} onClick={handleOverlayClick} />
      )}

      {/* ── Completion banner ── */}
      {phase === 'complete' && !selected && (
        <div className={styles.completeBanner}>
          ✦ Расклад завершён ✦
        </div>
      )}

      {/* ── LLM narrative reading (complete phase) ── */}
      {phase === 'complete' && (
        <CelticCrossReading readingId={readingId} cards={cards} />
      )}

      {/* ── Restart button (complete phase) ── */}
      {phase === 'complete' && (
        <motion.button
          className="btn-secondary btn-with-icon"
          onClick={handleRestart}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          style={{ marginTop: 16 }}
        >
          <svg
            width="15"
            height="15"
            viewBox="0 0 15 15"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M1.5 7.5A6 6 0 0 1 13 4.5M13.5 7.5A6 6 0 0 1 2 10.5" />
            <polyline points="11,2 13,4.5 10.5,6.5" />
            <polyline points="4,12.5 2,10.5 4.5,8.5" />
          </svg>
          Новый расклад
        </motion.button>
      )}
    </div>
  )
}
