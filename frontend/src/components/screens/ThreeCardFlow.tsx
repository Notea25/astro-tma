import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion'
import { tarotApi } from '@/services/api'
import { useHaptic } from '@/hooks/useTelegram'

const POSITIONS = ['Прошлое', 'Настоящее', 'Будущее']

type Phase = 'idle' | 'shuffling' | 'drawing' | 'collapsing' | 'reading'

// Card back skin — uses tarot-back.jpg rotated via child element
function CardBackSkin() {
  return <div className="card-back-skin" />
}

interface Props {
  onReset: () => void
}

export function ThreeCardFlow({ onReset }: Props) {
  const { impact } = useHaptic()
  const [phase, setPhase] = useState<Phase>('idle')
  const [drawnCount, setDrawnCount] = useState(0)
  const [revealedIdx, setRevealedIdx] = useState<number | null>(null)
  const [shownCards, setShownCards] = useState<number[]>([])

  const drawMutation = useMutation({
    mutationFn: () => tarotApi.draw('three_card'),
    onSuccess: () => setPhase('drawing'),
  })

  const cards = drawMutation.data?.cards ?? []
  const remaining = 3 - drawnCount

  const handleStart = useCallback(() => {
    impact('medium')
    setPhase('shuffling')
    drawMutation.mutate()
  }, [impact, drawMutation])

  const handleTapDeck = useCallback(() => {
    if (phase !== 'drawing') return
    impact('medium')
    const next = drawnCount + 1
    setDrawnCount(next)
    if (next === 3) {
      setPhase('collapsing')
      setTimeout(() => setPhase('reading'), 650)
    }
  }, [phase, drawnCount, impact])

  const handleTapCard = useCallback((i: number) => {
    if (phase !== 'reading') return
    if (revealedIdx === i) {
      setRevealedIdx(null)
      setShownCards(prev => prev.includes(i) ? prev : [...prev, i])
    } else {
      impact('medium')
      setRevealedIdx(i)
    }
  }, [phase, revealedIdx, impact])

  const handleReset = useCallback(() => {
    setPhase('idle')
    setDrawnCount(0)
    setRevealedIdx(null)
    setShownCards([])
    drawMutation.reset()
    onReset()
  }, [drawMutation, onReset])

  return (
    <LayoutGroup>
      <div className="three-flow">

        {/* ── IDLE ── */}
        <AnimatePresence>
          {phase === 'idle' && (
            <motion.div
              key="idle"
              className="three-flow__idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, scale: 0.88, transition: { duration: 0.25 } }}
            >
              <div className="three-flow__static-deck">
                {[2, 1, 0].map(i => (
                  <div key={i} className="deck-card-static" style={{
                    zIndex: 3 - i,
                    transform: `rotate(${(i - 1) * 5}deg) translateY(${i * -6}px)`,
                  }}>
                    <CardBackSkin />
                  </div>
                ))}
              </div>
              <motion.button
                className="btn-primary btn-draw"
                onClick={handleStart}
                whileTap={{ scale: 0.96 }}
              >
                Тянуть карты
              </motion.button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── SHUFFLING / DRAWING / COLLAPSING ── */}
        <AnimatePresence>
          {(phase === 'shuffling' || phase === 'drawing' || phase === 'collapsing') && (
            <motion.div
              key="active"
              className="three-flow__active"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, transition: { duration: 0.35 } }}
            >
              {/* Deck */}
              <AnimatePresence>
                {phase !== 'collapsing' && remaining > 0 && (
                  <motion.div
                    key="deck"
                    className={`three-flow__deck ${phase === 'drawing' ? 'is-ready' : ''}`}
                    exit={{ scale: 0, opacity: 0, transition: { duration: 0.45, ease: 'easeInOut' } }}
                    onClick={handleTapDeck}
                    whileTap={phase === 'drawing' ? { scale: 0.94 } : {}}
                  >
                    <div className="deck-stack">
                      {Array.from({ length: remaining }).map((_, stackIdx) => {
                        const cardSlotIdx = drawnCount + stackIdx
                        const offset = stackIdx
                        return (
                          <motion.div
                            key={cardSlotIdx}
                            layoutId={`card-slot-${cardSlotIdx}`}
                            className="deck-stack__card"
                            style={{ zIndex: remaining - stackIdx }}
                            animate={phase === 'shuffling' ? {
                              rotate: [(offset - 1) * 4, (offset - 1) * 4 + 14, (offset - 1) * 4 - 9, (offset - 1) * 4],
                              y: [offset * -5, offset * -5 - 18, offset * -5 + 4, offset * -5],
                              x: [(offset - 1) * 3, (offset - 1) * 3 + 11, (offset - 1) * 3 - 5, (offset - 1) * 3],
                            } : {
                              rotate: (offset - 1) * 4,
                              y: offset * -5,
                              x: (offset - 1) * 3,
                            }}
                            transition={phase === 'shuffling' ? {
                              duration: 1.6,
                              repeat: Infinity,
                              delay: stackIdx * 0.52,
                              ease: 'easeInOut',
                            } : { duration: 0.3, ease: 'easeOut' }}
                          >
                            <CardBackSkin />
                          </motion.div>
                        )
                      })}
                    </div>

                    {/* Hint */}
                    <p className="three-flow__deck-hint">
                      {phase === 'shuffling'
                        ? <motion.span
                            animate={{ opacity: [0.5, 1, 0.5] }}
                            transition={{ duration: 1.8, repeat: Infinity }}
                          >Тасуем колоду...</motion.span>
                        : drawnCount === 0 ? 'Нажмите, чтобы вытянуть'
                        : drawnCount === 1 ? 'Ещё 2 карты'
                        : 'Последняя карта'
                      }
                    </p>

                    {/* Glow ring when ready */}
                    {phase === 'drawing' && (
                      <motion.div
                        className="deck-ready-ring"
                        animate={{ opacity: [0.4, 0.9, 0.4], scale: [0.95, 1.05, 0.95] }}
                        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                      />
                    )}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Three slots */}
              <div className="three-flow__slots">
                {POSITIONS.map((pos, i) => (
                  <div key={i} className="three-flow__slot">
                    <div className="three-flow__slot-box">
                      {i < drawnCount ? (
                        <motion.div
                          layoutId={`card-slot-${i}`}
                          className="three-flow__slot-card"
                        >
                          <CardBackSkin />
                        </motion.div>
                      ) : (
                        <div className="three-flow__slot-empty">
                          <span className="slot-number">{i + 1}</span>
                        </div>
                      )}
                    </div>
                    <span className="three-flow__slot-label">{pos}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── READING ── */}
        <AnimatePresence>
          {phase === 'reading' && (
            <motion.div
              key="reading"
              className="three-flow__reading"
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, ease: 'easeOut' }}
            >
              {/* Cards row */}
              <div className="reading-row">
                {POSITIONS.map((pos, i) => {
                  const card = cards[i]
                  const isShown = shownCards.includes(i)
                  return (
                    <motion.div
                      key={i}
                      className={`reading-slot ${isShown ? 'is-shown' : ''}`}
                      onClick={() => handleTapCard(i)}
                      whileTap={{ scale: 0.94 }}
                    >
                      <div className="reading-slot__card">
                        {isShown && card ? (
                          <motion.div
                            className="reading-slot__front"
                            initial={{ rotateY: -90 }}
                            animate={{ rotateY: 0 }}
                            transition={{ duration: 0.4, ease: 'easeOut' }}
                            style={{ transformStyle: 'preserve-3d' }}
                          >
                            {card.image_url
                              ? <img src={card.image_url} alt={card.name_ru} className="reading-slot__img" />
                              : <span className="reading-slot__emoji">{card.emoji}</span>
                            }
                          </motion.div>
                        ) : (
                          <CardBackSkin />
                        )}
                      </div>
                      <span className="reading-slot__label">{pos}</span>
                    </motion.div>
                  )
                })}
              </div>

              {/* Hint */}
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

              {/* Meanings */}
              <div className="reading-meanings">
                <AnimatePresence>
                  {shownCards.map(i => {
                    const card = cards[i]
                    if (!card) return null
                    return (
                      <motion.div
                        key={i}
                        className="meaning-block"
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.35 }}
                      >
                        <div className="meaning-block__header">
                          <span className="meaning-block__pos">{POSITIONS[i]}</span>
                          <span className={`meaning-block__orient ${card.reversed ? 'rev' : ''}`}>
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

              {/* Reset button */}
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

        {/* ── REVEAL OVERLAY ── */}
        <AnimatePresence>
          {revealedIdx !== null && phase === 'reading' && (() => {
            const card = cards[revealedIdx]
            if (!card) return null
            return (
              <motion.div
                key="overlay"
                className="reveal-overlay"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                onClick={() => handleTapCard(revealedIdx)}
              >
                <motion.div
                  className="reveal-card"
                  initial={{ scale: 0.3, rotateY: -90, opacity: 0 }}
                  animate={{ scale: 1, rotateY: 0, opacity: 1 }}
                  exit={{ scale: 0.3, opacity: 0, transition: { duration: 0.2 } }}
                  transition={{ type: 'spring', damping: 22, stiffness: 280 }}
                  style={{ transformStyle: 'preserve-3d', perspective: '800px' }}
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
                    <p className={`reveal-card__orient ${card.reversed ? 'rev' : ''}`}>
                      {card.reversed ? '↓ Перевёрнутое' : '↑ Прямое'}
                    </p>
                    <p className="reveal-card__keys">
                      {card.keywords_ru?.slice(0, 3).join(' · ')}
                    </p>
                    <button
                      className="btn-ghost reveal-card__close"
                      onClick={() => handleTapCard(revealedIdx)}
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
    </LayoutGroup>
  )
}
