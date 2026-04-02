import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { PremiumGate } from '@/components/ui/PremiumGate'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { tarotApi } from '@/services/api'
import { useAppStore } from '@/stores/app'
import { useHaptic } from '@/hooks/useTelegram'
import { useTelegramBackButton } from '@/hooks/useTelegram'
import type { TarotSpreadResponse, TarotCardDetail } from '@/types'

type SpreadType = 'three_card' | 'celtic_cross' | 'week' | 'relationship'

interface SpreadOption {
  id: SpreadType
  name: string
  cardCount: number
  premium: boolean
  productId: string
  stars: number
}

const SPREADS: SpreadOption[] = [
  { id: 'three_card',    name: 'Прошлое · Настоящее · Будущее', cardCount: 3,  premium: false, productId: '', stars: 0 },
  { id: 'celtic_cross',  name: 'Кельтский Крест',                cardCount: 10, premium: true,  productId: 'tarot_celtic', stars: 30 },
  { id: 'week',          name: 'Карта на каждый день',           cardCount: 7,  premium: true,  productId: 'tarot_week',   stars: 40 },
  { id: 'relationship',  name: 'Расклад на отношения',           cardCount: 5,  premium: true,  productId: 'tarot_celtic', stars: 30 },
]

function TarotCardFlip({ card, index }: { card: TarotCardDetail; index: number }) {
  const [flipped, setFlipped] = useState(false)
  const { impact } = useHaptic()

  return (
    <motion.div
      className="tarot-card-wrap"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      <p className="tarot-card__position">{card.position_name_ru}</p>
      <div
        className={`tarot-card-flip ${flipped ? 'is-flipped' : ''} ${card.reversed ? 'reversed' : ''}`}
        onClick={() => { if (!flipped) { impact('medium'); setFlipped(true) } }}
      >
        <div className="tarot-card-flip__front">
          <div className="tarot-card__back-pattern">✦</div>
          <p className="tarot-card__tap-hint">Нажмите</p>
        </div>
        <div className="tarot-card-flip__back">
          {card.image_url
            ? <img
                src={card.image_url}
                alt={card.name_ru}
                className={`tarot-card__img ${card.reversed ? 'tarot-card__img--reversed' : ''}`}
              />
            : <span className="tarot-card__emoji">{card.emoji}</span>
          }
          <p className="tarot-card__name">
            {card.name_ru}
            {card.reversed && <span className="tarot-card__rev"> ↓</span>}
          </p>
        </div>
      </div>

      <AnimatePresence>
        {flipped && (
          <motion.div
            className="tarot-card__meaning"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            transition={{ duration: 0.4 }}
          >
            <p className="tarot-card__meaning-text">{card.meaning_ru}</p>
            <div className="tarot-card__keywords">
              {card.keywords_ru.slice(0, 3).map((kw) => (
                <span key={kw} className="keyword-chip">{kw}</span>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function Tarot() {
  const { user, setScreen } = useAppStore()
  const { impact } = useHaptic()
  const [selectedSpread, setSelectedSpread] = useState<SpreadType | null>(null)
  const [reading, setReading] = useState<TarotSpreadResponse | null>(null)

  const handleBack = useCallback(() => {
    if (reading) setReading(null)
    else if (selectedSpread) setSelectedSpread(null)
    else setScreen('discover', 'back')
  }, [reading, selectedSpread, setScreen])

  useTelegramBackButton(handleBack, true)

  const drawMutation = useMutation({
    mutationFn: tarotApi.draw,
    onSuccess: (data) => { impact('success' as any); setReading(data) },
  })

  const handleSelectSpread = (spread: SpreadOption) => {
    impact('light')
    setSelectedSpread(spread.id)
  }

  const handleDraw = () => {
    if (!selectedSpread) return
    impact('medium')
    drawMutation.mutate(selectedSpread)
  }

  // Spread selection view
  if (!selectedSpread) {
    return (
      <div className="screen tarot-screen">
        <div className="screen-header screen-header--with-back">
          <button className="back-btn" onClick={() => setScreen('discover', 'back')} aria-label="Назад">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"><path d="M13 4l-6 6 6 6"/></svg>
          </button>
          <h2 className="screen-title">Таро</h2>
        </div>
        <div className="screen-content">
          {SPREADS.map((spread) => (
            <PremiumGate
              key={spread.id}
              locked={spread.premium && !user?.is_premium}
              productId={spread.productId}
              productName={spread.name}
              stars={spread.stars}
            >
              <motion.div
                className="spread-option"
                onClick={() => handleSelectSpread(spread)}
                whileTap={{ scale: 0.97 }}
              >
                <div className="spread-option__info">
                  <div className="spread-option__name">{spread.name}</div>
                  <div className="spread-option__count">{spread.cardCount} карт</div>
                </div>
                {spread.premium && (
                  <span className="premium-badge">✦ Pro</span>
                )}
              </motion.div>
            </PremiumGate>
          ))}
        </div>
      </div>
    )
  }

  // Reading view
  const spreadInfo = SPREADS.find(s => s.id === selectedSpread)!

  return (
    <div className="screen tarot-screen">
      <div className="screen-header screen-header--with-back">
        <button className="back-btn" onClick={handleBack} aria-label="Назад">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"><path d="M13 4l-6 6 6 6"/></svg>
        </button>
        <h2 className="screen-title">{spreadInfo.name}</h2>
      </div>

      <div className="screen-content">
        {drawMutation.isPending && <LoadingSpinner message="Тасуем колоду..." />}

        {drawMutation.isError && (
          <div className="error-state">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" opacity="0.5">
              <circle cx="16" cy="16" r="13"/>
              <line x1="16" y1="10" x2="16" y2="17"/>
              <circle cx="16" cy="21" r="1" fill="currentColor" stroke="none"/>
            </svg>
            <p>Не удалось загрузить расклад. Попробуйте ещё раз.</p>
            <button className="btn-ghost" onClick={() => drawMutation.reset()}>Повторить</button>
          </div>
        )}

        {!reading && !drawMutation.isPending && !drawMutation.isError && (
          <motion.div
            className="draw-prompt"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <div className="deck-preview">
              {[2, 1, 0].map((i) => (
                <div key={i} className="deck-card" style={{ transform: `rotate(${(i - 1) * 6}deg) translateY(${i * -4}px)` }}>
                  ✦
                </div>
              ))}
            </div>
            <motion.button
              className="btn-primary btn-draw"
              onClick={handleDraw}
              whileTap={{ scale: 0.96 }}
            >
              Тянуть карты
            </motion.button>
          </motion.div>
        )}

        {reading && (
          <>
            <div className="tarot-cards-grid">
              {reading.cards.map((card, i) => (
                <TarotCardFlip key={card.id} card={card} index={i} />
              ))}
            </div>
            <motion.button
              className="btn-secondary btn-with-icon"
              onClick={() => { setReading(null); drawMutation.reset() }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M1.5 7.5A6 6 0 0 1 13 4.5M13.5 7.5A6 6 0 0 1 2 10.5"/>
                <polyline points="11,2 13,4.5 10.5,6.5"/>
                <polyline points="4,12.5 2,10.5 4.5,8.5"/>
              </svg>
              Новый расклад
            </motion.button>
          </>
        )}
      </div>
    </div>
  )
}
