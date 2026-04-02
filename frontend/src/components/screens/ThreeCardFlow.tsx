import { useState, useRef, useCallback, useEffect, useMemo } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { tarotApi } from '@/services/api'
import { useHaptic } from '@/hooks/useTelegram'
import type { TarotCardDetail } from '@/types'

const POSITIONS      = ['Прошлое', 'Настоящее', 'Будущее']
const WHEEL_COUNT    = 18
const WHEEL_R        = 125   // orbit radius px
const FLY_W          = 180   // large card width
const FLY_H          = 270   // large card height
const SLOT_W         = 80
const SCALE_SMALL    = 52 / FLY_W  // ~0.289 — wheel card scale

type Phase = 'spinning' | 'fly-in' | 'revealed' | 'fly-out' | 'reading'

interface Props { onReset: () => void }

// Wheel card positions (pre-computed)
const WHEEL_POS = Array.from({ length: WHEEL_COUNT }, (_, i) => {
  const a = (i / WHEEL_COUNT) * 2 * Math.PI
  return { i, x: Math.cos(a) * WHEEL_R, y: Math.sin(a) * WHEEL_R }
})

// ── Mandala SVG inside wheel card ──────────────────────────────────────────
function WheelCardBack() {
  return (
    <div className="wheel-card__back">
      <svg width="30" height="44" viewBox="0 0 30 44" fill="none">
        <circle cx="15" cy="22" r="10" stroke="rgba(201,168,76,0.32)" strokeWidth="0.6"/>
        <circle cx="15" cy="22" r="5"  stroke="rgba(201,168,76,0.44)" strokeWidth="0.6"/>
        <circle cx="15" cy="22" r="2"  fill="rgba(201,168,76,0.38)"/>
        <line x1="15" y1="4"  x2="15" y2="40" stroke="rgba(201,168,76,0.2)" strokeWidth="0.5"/>
        <line x1="1"  y1="22" x2="29" y2="22" stroke="rgba(201,168,76,0.2)" strokeWidth="0.5"/>
        <line x1="5"  y1="10" x2="25" y2="34" stroke="rgba(201,168,76,0.13)" strokeWidth="0.5"/>
        <line x1="25" y1="10" x2="5"  y2="34" stroke="rgba(201,168,76,0.13)" strokeWidth="0.5"/>
        <circle cx="15" cy="22" r="7.5" stroke="rgba(201,168,76,0.15)" strokeWidth="0.4" strokeDasharray="2.5 2"/>
      </svg>
    </div>
  )
}

// ── Front face of a revealed card ──────────────────────────────────────────
function CardFront({ card }: { card: TarotCardDetail }) {
  if (card.image_url) {
    return <img src={card.image_url} alt={card.name_ru} className="reveal-front__img" />
  }
  return (
    <div className="reveal-front__parchment">
      <span className="reveal-front__arcana">
        {card.arcana === 'major' ? 'Старший аркан' : 'Младший аркан'}
      </span>
      <span className="reveal-front__emoji">{card.emoji}</span>
      <span className="reveal-front__name">{card.name_ru}</span>
    </div>
  )
}

// ── Main component ──────────────────────────────────────────────────────────
export function ThreeCardFlow({ onReset }: Props) {
  const { impact } = useHaptic()
  const [phase,        setPhase]        = useState<Phase>('spinning')
  const [drawnCount,   setDrawnCount]   = useState(0)
  const [landedSlots,  setLandedSlots]  = useState<number[]>([])
  const [flyFrom,      setFlyFrom]      = useState<{ x: number; y: number } | null>(null)
  const [flyTo,        setFlyTo]        = useState<{ x: number; y: number } | null>(null)
  const [showGlow,     setShowGlow]     = useState(false)
  const [showText,     setShowText]     = useState(false)
  const [showContinue, setShowContinue] = useState(false)
  const [expandedIdx,  setExpandedIdx]  = useState<number | null>(null)
  const [shownCards,   setShownCards]   = useState<number[]>([])

  const slotRef0 = useRef<HTMLDivElement>(null)
  const slotRef1 = useRef<HTMLDivElement>(null)
  const slotRef2 = useRef<HTMLDivElement>(null)
  const slotRefs = useMemo(() => [slotRef0, slotRef1, slotRef2], [])
  const timers   = useRef<ReturnType<typeof setTimeout>[]>([])

  const drawMutation = useMutation({ mutationFn: () => tarotApi.draw('three_card') })
  const apiCards     = drawMutation.data?.cards ?? []

  useEffect(() => { drawMutation.mutate() }, []) // eslint-disable-line
  useEffect(() => () => { timers.current.forEach(clearTimeout) }, [])

  // Glow appears 1600ms after fly-in starts (= 2000ms from tap)
  useEffect(() => {
    if (phase !== 'fly-in') { setShowGlow(false); return }
    const t = setTimeout(() => setShowGlow(true), 1600)
    timers.current.push(t)
    return () => clearTimeout(t)
  }, [phase])

  // Center position for the large revealed card
  const cardLeft = useMemo(() => Math.round(window.innerWidth  / 2 - FLY_W / 2), [])
  const cardTop  = useMemo(() => Math.round(window.innerHeight * 0.28 - FLY_H / 2), [])

  // ── handlers ────────────────────────────────────────────────────────────
  const handleWheelTap = useCallback((e: React.MouseEvent) => {
    if (phase !== 'spinning' || drawnCount >= 3) return
    if (!drawMutation.isSuccess) return   // wait for API
    impact('medium')
    setShowGlow(false); setShowText(false); setShowContinue(false)
    setFlyFrom({ x: e.clientX, y: e.clientY })
    setPhase('fly-in')
  }, [phase, drawnCount, impact, drawMutation.isSuccess])

  const onFlyInComplete = useCallback(() => {
    setPhase('revealed')
    timers.current.push(setTimeout(() => setShowText(true),     300))
    timers.current.push(setTimeout(() => setShowContinue(true), 700))
  }, [])

  const handleContinue = useCallback(() => {
    impact('light')
    const rect = slotRefs[drawnCount].current?.getBoundingClientRect()
    setFlyTo({
      x: rect ? rect.left + rect.width  / 2 : window.innerWidth  / 2,
      y: rect ? rect.top  + rect.height / 2 : window.innerHeight - 160,
    })
    setShowText(false); setShowContinue(false); setShowGlow(false)
    setPhase('fly-out')
  }, [drawnCount, slotRefs, impact])

  const onFlyOutComplete = useCallback(() => {
    const next = drawnCount + 1
    setLandedSlots(prev => [...prev, drawnCount])
    setDrawnCount(next)
    setFlyFrom(null); setFlyTo(null)
    setPhase(next >= 3 ? 'reading' : 'spinning')
  }, [drawnCount])

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
    timers.current.forEach(clearTimeout); timers.current = []
    setPhase('spinning'); setDrawnCount(0); setLandedSlots([])
    setFlyFrom(null); setFlyTo(null)
    setShowGlow(false); setShowText(false); setShowContinue(false)
    setExpandedIdx(null); setShownCards([])
    drawMutation.reset()
    setTimeout(() => drawMutation.mutate(), 0)
    onReset()
  }, [drawMutation, onReset])

  const currentCard    = apiCards[drawnCount] ?? null
  const isSpinning     = phase === 'spinning'
  const isFlying       = phase === 'fly-in' || phase === 'revealed' || phase === 'fly-out'
  const cardsVisible   = isSpinning  // cards fade out when wheel stops
  const apiReady       = apiCards.length >= 3

  // ── render ───────────────────────────────────────────────────────────────
  return (
    <div className="three-flow">

      {/* ══ WHEEL ══ */}
      <AnimatePresence>
        {phase !== 'reading' && (
          <motion.div
            key="wheel"
            className="wheel-section"
            exit={{ opacity: 0, scale: 0.06, transition: { duration: 0.55, ease: [0.4, 0, 0.2, 1] } }}
          >
            <div
              className={`wheel-outer${isSpinning && apiReady ? ' is-tappable' : ''}`}
              onClick={isSpinning && apiReady ? handleWheelTap : undefined}
            >
              {/* Rotating ring */}
              <div className={`wheel-ring${isSpinning ? ' is-spinning' : ''}`}>
                {WHEEL_POS.map(({ i, x, y }) => (
                  <div
                    key={i}
                    className="wheel-card-slot"
                    style={{ left: `calc(50% + ${x}px)`, top: `calc(50% + ${y}px)` }}
                  >
                    <div className={`wheel-card${isSpinning ? ' is-spinning' : ''}${!cardsVisible ? ' is-hidden' : ''}`}>
                      <WheelCardBack />
                    </div>
                  </div>
                ))}
              </div>

              {/* Center hint */}
              {isSpinning && (
                <div className="wheel-center-hint">
                  <motion.div
                    className="wheel-hint-pill"
                    animate={{ opacity: apiReady ? [0.65, 1, 0.65] : [0.4, 0.7, 0.4] }}
                    transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
                  >
                    {!apiReady
                      ? 'Загрузка...'
                      : drawnCount === 0 ? 'Коснитесь\nколеса'
                      : drawnCount === 1 ? 'Ещё 2 карты'
                      : 'Последняя карта'}
                  </motion.div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ══ SLOTS ══ */}
      <div className={`wheel-slots${phase === 'reading' ? ' wheel-slots--reading' : ''}`}>
        {POSITIONS.map((pos, i) => {
          const hasLanded = landedSlots.includes(i)
          const card      = apiCards[i]
          const isShown   = shownCards.includes(i)
          return (
            <div key={i} className="wheel-slot">
              <div ref={slotRefs[i]} className={`wheel-slot__box${phase === 'reading' ? ' is-reading' : ''}`}>
                {hasLanded ? (
                  <motion.div
                    className="wheel-slot__card"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.2 }}
                    onClick={() => handleCardTap(i)}
                    style={{ cursor: phase === 'reading' ? 'pointer' : 'default' }}
                    whileTap={phase === 'reading' ? { scale: 0.93 } : undefined}
                  >
                    {phase === 'reading' && isShown && card
                      ? card.image_url
                        ? <img src={card.image_url} alt={card.name_ru} className="slot-card__img" />
                        : <div className="slot-card__emoji">{card.emoji}</div>
                      : <div className="card-back-skin" />
                    }
                    {phase === 'reading' && !isShown && <div className="slot-card__tap-ring" />}
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
            key="reading"
            className="reading-content"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.4 }}
          >
            {shownCards.length === 0 && (
              <motion.p className="three-flow__hint" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}>
                Нажмите на карту, чтобы открыть
              </motion.p>
            )}
            <div className="reading-meanings">
              <AnimatePresence>
                {shownCards.map(idx => {
                  const card = apiCards[idx]
                  if (!card) return null
                  return (
                    <motion.div key={idx} className="meaning-block" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
                      <div className="meaning-block__header">
                        <span className="meaning-block__pos">{POSITIONS[idx]}</span>
                        <span className={`meaning-block__orient${card.reversed ? ' rev' : ''}`}>{card.reversed ? '↓' : '↑'}</span>
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
              <motion.button className="btn-secondary btn-with-icon" onClick={handleReset} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>
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

      {/* ══ DARK OVERLAY ══ */}
      <AnimatePresence>
        {isFlying && (
          <motion.div
            key="fly-overlay"
            className="fly-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: phase === 'fly-out' ? 0 : 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8, delay: phase === 'fly-in' ? 0.2 : 0 }}
          />
        )}
      </AnimatePresence>

      {/* ══ GOLD GLOW (during fly-in after 1600ms, during revealed) ══ */}
      <AnimatePresence>
        {(phase === 'fly-in' || phase === 'revealed') && showGlow && (
          <motion.div
            key="glow"
            style={{
              position: 'fixed',
              left: cardLeft - 50, top: cardTop - 50,
              width: FLY_W + 100, height: FLY_H + 100,
              background: 'radial-gradient(ellipse at center, rgba(201,168,76,0.38) 0%, transparent 65%)',
              zIndex: 109,
              pointerEvents: 'none',
              borderRadius: '50%',
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1.2 }}
          />
        )}
      </AnimatePresence>

      {/* ══ FLY-IN (card leaves wheel, flips, lands centre) ══ */}
      <AnimatePresence>
        {phase === 'fly-in' && flyFrom && (
          <motion.div
            key="fly-in-card"
            style={{
              position: 'fixed', left: 0, top: 0,
              width: FLY_W, height: FLY_H,
              borderRadius: 12, overflow: 'hidden',
              zIndex: 110, pointerEvents: 'none',
            }}
            initial={{ x: flyFrom.x - FLY_W / 2, y: flyFrom.y - FLY_H / 2, scale: SCALE_SMALL }}
            animate={{ x: cardLeft, y: cardTop, scale: 1 }}
            transition={{ duration: 2.5, ease: [0.22, 0.61, 0.36, 1] }}
            onAnimationComplete={onFlyInComplete}
          >
            {/* Perspective wrapper for 3D flip */}
            <div style={{ perspective: '900px', width: '100%', height: '100%' }}>
              <motion.div
                style={{ transformStyle: 'preserve-3d', width: '100%', height: '100%', position: 'relative' }}
                initial={{ rotateY: 0 }}
                animate={{ rotateY: 180 }}
                transition={{ duration: 2.5, ease: [0.22, 0.61, 0.36, 1] }}
              >
                {/* Back face */}
                <div style={{ position: 'absolute', inset: 0, backfaceVisibility: 'hidden' }}>
                  <div className="card-back-skin" />
                </div>
                {/* Front face */}
                <div style={{ position: 'absolute', inset: 0, backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}>
                  {currentCard && <CardFront card={currentCard} />}
                </div>
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ══ REVEALED (card rests at center) ══ */}
      {phase === 'revealed' && currentCard && (
        <div
          style={{
            position: 'fixed', left: cardLeft, top: cardTop,
            width: FLY_W, height: FLY_H,
            borderRadius: 12, overflow: 'hidden',
            zIndex: 110,
            border: '1px solid rgba(201,168,76,0.3)',
          }}
        >
          <CardFront card={currentCard} />
        </div>
      )}

      {/* ══ FLY-OUT (card shrinks to slot) ══ */}
      <AnimatePresence>
        {phase === 'fly-out' && flyTo && currentCard && (
          <motion.div
            key="fly-out-card"
            style={{
              position: 'fixed', left: 0, top: 0,
              width: FLY_W, height: FLY_H,
              borderRadius: 12, overflow: 'hidden',
              zIndex: 110, pointerEvents: 'none',
              border: '1px solid rgba(201,168,76,0.3)',
            }}
            initial={{ x: cardLeft, y: cardTop, scale: 1 }}
            animate={{ x: flyTo.x - FLY_W / 2, y: flyTo.y - FLY_H / 2, scale: SLOT_W / FLY_W }}
            transition={{ duration: 0.7, ease: [0.4, 0, 0.2, 1] }}
            onAnimationComplete={onFlyOutComplete}
          >
            <CardFront card={currentCard} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ══ REVEALED TEXT + CONTINUE ══ */}
      <AnimatePresence>
        {phase === 'revealed' && currentCard && (
          <motion.div
            key="reveal-info"
            className="reveal-info"
            style={{ top: cardTop + FLY_H + 18 }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <AnimatePresence>
              {showText && (
                <motion.div
                  className="reveal-info__text"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8 }}
                >
                  <p className="reveal-info__name">
                    {currentCard.reversed ? '↓ ' : ''}{currentCard.name_ru}
                  </p>
                  <p className="reveal-info__keys">
                    {currentCard.keywords_ru?.slice(0, 3).join(' · ')}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
            <AnimatePresence>
              {showContinue && (
                <motion.button
                  className="btn-primary reveal-info__continue"
                  onClick={handleContinue}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6 }}
                  whileTap={{ scale: 0.96 }}
                >
                  {drawnCount === 2 ? 'Читать расклад' : 'Продолжить'}
                </motion.button>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ══ READING EXPANDED OVERLAY ══ */}
      <AnimatePresence>
        {expandedIdx !== null && phase === 'reading' && (() => {
          const card = apiCards[expandedIdx]
          if (!card) return null
          return (
            <motion.div
              key="expanded"
              className="reveal-overlay"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
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
                    : <div className="reveal-card__emoji-fallback">{card.emoji}</div>}
                </div>
                <div className="reveal-card__info">
                  <p className="reveal-card__arcana">{card.arcana === 'major' ? 'Старший аркан' : 'Младший аркан'}</p>
                  <h3 className="reveal-card__name">{card.name_ru}</h3>
                  <p className={`reveal-card__orient${card.reversed ? ' rev' : ''}`}>{card.reversed ? '↓ Перевёрнутое' : '↑ Прямое'}</p>
                  <p className="reveal-card__keys">{card.keywords_ru?.slice(0, 3).join(' · ')}</p>
                  <button className="btn-ghost reveal-card__close" onClick={() => handleCardTap(expandedIdx)}>Вернуть карту</button>
                </div>
              </motion.div>
            </motion.div>
          )
        })()}
      </AnimatePresence>

    </div>
  )
}
