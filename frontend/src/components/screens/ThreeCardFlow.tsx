import { useState, useRef, useCallback, useEffect, useMemo } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { tarotApi } from '@/services/api'
import { useHaptic } from '@/hooks/useTelegram'

const TOTAL_CARDS = 78
const POSITIONS = ['Прошлое', 'Настоящее', 'Будущее']
const CARD_W = 80   // slot/flying card width
const CARD_H = 116  // slot/flying card height

type Phase = 'spinning' | 'collapsing' | 'reading'

interface FlyingCard {
  id: number
  from: { x: number; y: number }
  to:   { x: number; y: number }
  slotIdx: number
}

interface Props {
  onReset: () => void
}

// Pre-compute 78 card positions around the circle once
const WHEEL_CARDS = Array.from({ length: TOTAL_CARDS }, (_, i) => {
  const angle    = (i / TOTAL_CARDS) * 360
  const rad      = (angle - 90) * (Math.PI / 180)
  const xPct     = Math.cos(rad) * 43  // % of container half-width
  const yPct     = Math.sin(rad) * 43
  return { i, angle, xPct, yPct }
})

export function ThreeCardFlow({ onReset }: Props) {
  const { impact } = useHaptic()
  const [phase,       setPhase]       = useState<Phase>('spinning')
  const [drawnCount,  setDrawnCount]  = useState(0)
  const [flyingCards, setFlyingCards] = useState<FlyingCard[]>([])
  const [landedSlots, setLandedSlots] = useState<number[]>([])
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null)
  const [shownCards,  setShownCards]  = useState<number[]>([])

  const wheelRef = useRef<HTMLDivElement>(null)
  const slotRef0 = useRef<HTMLDivElement>(null)
  const slotRef1 = useRef<HTMLDivElement>(null)
  const slotRef2 = useRef<HTMLDivElement>(null)
  const slotRefs = useMemo(() => [slotRef0, slotRef1, slotRef2], [])
  const collapseStarted = useRef(false)

  const drawMutation = useMutation({
    mutationFn: () => tarotApi.draw('three_card'),
  })
  const apiCards = drawMutation.data?.cards ?? []

  // Fire API call on mount
  useEffect(() => {
    drawMutation.mutate()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Collapse once all 3 drawn AND api has returned
  useEffect(() => {
    if (drawnCount < 3 || collapseStarted.current) return
    if (!drawMutation.isSuccess && !drawMutation.isError) return
    collapseStarted.current = true
    const t1 = setTimeout(() => setPhase('collapsing'), 250)
    const t2 = setTimeout(() => setPhase('reading'), 900)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [drawnCount, drawMutation.isSuccess, drawMutation.isError])

  /* ── helpers ── */
  const getEjectPoint = useCallback(() => {
    const rect = wheelRef.current?.getBoundingClientRect()
    if (!rect) return { x: window.innerWidth / 2, y: 140 }
    const radius = rect.width * 0.43
    return {
      x: rect.left + rect.width  / 2,
      y: rect.top  + rect.height / 2 - radius + 8,
    }
  }, [])

  const getSlotCenter = useCallback((idx: number) => {
    const rect = slotRefs[idx].current?.getBoundingClientRect()
    if (!rect) return { x: window.innerWidth / 2, y: window.innerHeight - 150 }
    return {
      x: rect.left + rect.width  / 2,
      y: rect.top  + rect.height / 2,
    }
  }, [slotRefs])

  /* ── interactions ── */
  const handleTap = useCallback(() => {
    if (phase !== 'spinning' || drawnCount >= 3) return
    impact('medium')
    const slotIdx = drawnCount
    const from    = getEjectPoint()
    const to      = getSlotCenter(slotIdx)
    setFlyingCards(prev => [...prev, { id: Date.now(), from, to, slotIdx }])
    setDrawnCount(prev => prev + 1)
  }, [phase, drawnCount, impact, getEjectPoint, getSlotCenter])

  const handleCardTap = useCallback((idx: number) => {
    if (phase !== 'reading') return
    if (expandedIdx === idx) {
      setExpandedIdx(null)
      setShownCards(prev => prev.includes(idx) ? prev : [...prev, idx])
    } else {
      impact('medium')
      setExpandedIdx(idx)
    }
  }, [phase, expandedIdx, impact])

  const handleReset = useCallback(() => {
    collapseStarted.current = false
    setPhase('spinning')
    setDrawnCount(0)
    setFlyingCards([])
    setLandedSlots([])
    setExpandedIdx(null)
    setShownCards([])
    drawMutation.reset()
    setTimeout(() => drawMutation.mutate(), 0)
    onReset()
  }, [drawMutation, onReset])

  /* ── render ── */
  return (
    <div className="three-flow">

      {/* ══ WHEEL (spinning + collapsing) ══ */}
      <AnimatePresence>
        {phase !== 'reading' && (
          <motion.div
            key="wheel-wrap"
            className="wheel-section"
            exit={{ opacity: 0, scale: 0.08, transition: { duration: 0.6, ease: [0.4, 0, 0.2, 1] } }}
          >
            <motion.div
              className={`card-wheel-wrap${phase === 'spinning' && drawnCount < 3 ? ' is-tappable' : ''}`}
              onClick={handleTap}
              whileTap={phase === 'spinning' && drawnCount < 3 ? { scale: 0.97 } : undefined}
            >
              {/* The spinning ring */}
              <div
                ref={wheelRef}
                className={`card-wheel${phase === 'spinning' ? ' is-spinning' : ''}`}
              >
                {WHEEL_CARDS.map(({ i, angle, xPct, yPct }) => (
                  <div
                    key={i}
                    className={`card-wheel__card${i < drawnCount ? ' card-wheel__card--gone' : ''}`}
                    style={{
                      left:      `calc(50% + ${xPct}%)`,
                      top:       `calc(50% + ${yPct}%)`,
                      transform: `translate(-50%, -50%) rotate(${angle + 90}deg)`,
                    }}
                  />
                ))}

                {/* Center pulse */}
                {phase === 'spinning' && drawnCount < 3 && (
                  <div className="card-wheel__center">
                    <motion.div
                      className="wheel-pulse"
                      animate={{ scale: [1, 1.15, 1], opacity: [0.6, 1, 0.6] }}
                      transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
                    >
                      {drawnCount === 0 ? 'Коснитесь' : drawnCount === 1 ? 'Ещё 2' : 'Ещё 1'}
                    </motion.div>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ══ SLOTS (all phases) ══ */}
      <div className={`wheel-slots${phase === 'reading' ? ' wheel-slots--reading' : ''}`}>
        {POSITIONS.map((pos, i) => {
          const hasLanded = landedSlots.includes(i)
          const card      = apiCards[i]
          const isShown   = shownCards.includes(i)
          return (
            <div key={i} className="wheel-slot">
              <div
                ref={slotRefs[i]}
                className={`wheel-slot__box${phase === 'reading' ? ' is-reading' : ''}`}
              >
                {hasLanded ? (
                  <motion.div
                    className="wheel-slot__card"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.15 }}
                    onClick={() => handleCardTap(i)}
                    style={{ cursor: phase === 'reading' ? 'pointer' : 'default' }}
                    whileTap={phase === 'reading' ? { scale: 0.93 } : undefined}
                  >
                    {phase === 'reading' && isShown && card ? (
                      card.image_url
                        ? <img src={card.image_url} alt={card.name_ru} className="slot-card__img" />
                        : <div className="slot-card__emoji">{card.emoji}</div>
                    ) : (
                      <div className="card-back-skin" />
                    )}
                    {phase === 'reading' && !isShown && (
                      <div className="slot-card__tap-ring" />
                    )}
                  </motion.div>
                ) : (
                  <div className="wheel-slot__empty">
                    <span className="slot-number">{i + 1}</span>
                  </div>
                )}
              </div>
              <span className="wheel-slot__label">{pos}</span>
            </div>
          )
        })}
      </div>

      {/* ══ READING CONTENT ══ */}
      <AnimatePresence>
        {phase === 'reading' && (
          <motion.div
            key="reading-content"
            className="reading-content"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25, duration: 0.4, ease: 'easeOut' }}
          >
            {shownCards.length === 0 && (
              <motion.p
                className="three-flow__hint"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                Нажмите на карту, чтобы открыть
              </motion.p>
            )}

            <div className="reading-meanings">
              <AnimatePresence>
                {shownCards.map(idx => {
                  const card = apiCards[idx]
                  if (!card) return null
                  return (
                    <motion.div
                      key={idx}
                      className="meaning-block"
                      initial={{ opacity: 0, y: 16 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.35 }}
                    >
                      <div className="meaning-block__header">
                        <span className="meaning-block__pos">{POSITIONS[idx]}</span>
                        <span className={`meaning-block__orient${card.reversed ? ' rev' : ''}`}>
                          {card.reversed ? '↓' : '↑'}
                        </span>
                        <span className="meaning-block__name">{card.name_ru}</span>
                      </div>
                      <p className="meaning-block__keys">{card.keywords_ru?.slice(0, 3).join(' · ')}</p>
                      <p className="meaning-block__text">{card.meaning_ru}</p>
                    </motion.div>
                  )
                })}
              </AnimatePresence>
            </div>

            {shownCards.length === 3 && (
              <motion.button
                className="btn-secondary btn-with-icon"
                onClick={handleReset}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
              >
                <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1.5 7.5A6 6 0 0 1 13 4.5M13.5 7.5A6 6 0 0 1 2 10.5"/>
                  <polyline points="11,2 13,4.5 10.5,6.5"/>
                  <polyline points="4,12.5 2,10.5 4.5,8.5"/>
                </svg>
                Новый расклад
              </motion.button>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ══ FLYING CARDS (fixed overlay) ══ */}
      <AnimatePresence>
        {flyingCards.map(fc => (
          <motion.div
            key={fc.id}
            style={{
              position: 'fixed',
              left: 0, top: 0,
              width:  CARD_W,
              height: CARD_H,
              borderRadius: 10,
              overflow: 'hidden',
              zIndex: 99,
              pointerEvents: 'none',
              border: '1px solid rgba(201,168,76,0.35)',
            }}
            initial={{
              x:       fc.from.x - CARD_W / 2,
              y:       fc.from.y - CARD_H / 2,
              scale:   0.55,
              opacity: 0,
              rotate:  -8,
            }}
            animate={{
              x:       fc.to.x - CARD_W / 2,
              y:       fc.to.y - CARD_H / 2,
              scale:   1,
              opacity: 1,
              rotate:  0,
            }}
            transition={{ type: 'spring', damping: 18, stiffness: 160 }}
            onAnimationComplete={() => {
              setFlyingCards(prev => prev.filter(f => f.id !== fc.id))
              setLandedSlots(prev => prev.includes(fc.slotIdx) ? prev : [...prev, fc.slotIdx])
            }}
          >
            <div className="card-back-skin" />
          </motion.div>
        ))}
      </AnimatePresence>

      {/* ══ EXPANDED CARD OVERLAY ══ */}
      <AnimatePresence>
        {expandedIdx !== null && phase === 'reading' && (() => {
          const card = apiCards[expandedIdx]
          if (!card) return null
          return (
            <motion.div
              key="overlay"
              className="reveal-overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.22 }}
              onClick={() => handleCardTap(expandedIdx)}
            >
              <motion.div
                className="reveal-card"
                initial={{ scale: 0.45, opacity: 0, y: 40 }}
                animate={{ scale: 1,    opacity: 1, y: 0  }}
                exit={{    scale: 0.45, opacity: 0, y: 40 }}
                transition={{ type: 'spring', damping: 22, stiffness: 260 }}
                onClick={e => e.stopPropagation()}
              >
                <div className="reveal-card__img-wrap">
                  {card.image_url
                    ? <img src={card.image_url} alt={card.name_ru} className="reveal-card__img" />
                    : <div className="reveal-card__emoji-fallback">{card.emoji}</div>
                  }
                </div>
                <div className="reveal-card__info">
                  <p className="reveal-card__arcana">
                    {card.arcana === 'major' ? 'Старший аркан' : 'Младший аркан'}
                  </p>
                  <h3 className="reveal-card__name">{card.name_ru}</h3>
                  <p className={`reveal-card__orient${card.reversed ? ' rev' : ''}`}>
                    {card.reversed ? '↓ Перевёрнутое' : '↑ Прямое'}
                  </p>
                  <p className="reveal-card__keys">
                    {card.keywords_ru?.slice(0, 3).join(' · ')}
                  </p>
                  <button
                    className="btn-ghost reveal-card__close"
                    onClick={() => handleCardTap(expandedIdx)}
                  >
                    Вернуть карту
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )
        })()}
      </AnimatePresence>

    </div>
  )
}
