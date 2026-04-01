import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { macApi } from '@/services/api'
import { useAppStore } from '@/stores/app'
import { useHaptic } from '@/hooks/useTelegram'
import { useTelegramBackButton } from '@/hooks/useTelegram'
import type { MacReadingResponse } from '@/types'

const CATEGORY_LABELS: Record<string, string> = {
  emotions: 'Эмоции',
  relationships: 'Отношения',
  self: 'Самопознание',
  shadow: 'Тень',
  resources: 'Ресурсы',
}

const CATEGORY_COLORS: Record<string, string> = {
  emotions: '#e88a9a',
  relationships: '#a08ce8',
  self: '#7ec8e3',
  shadow: '#9b8bba',
  resources: '#8bc89b',
}

export function Mac() {
  const { setScreen } = useAppStore()
  const { impact } = useHaptic()
  const [reading, setReading] = useState<MacReadingResponse | null>(null)
  const [revealed, setRevealed] = useState(false)

  useTelegramBackButton(
    () => { reading ? (setReading(null), setRevealed(false)) : setScreen('home') },
    true
  )

  const drawMutation = useMutation({
    mutationFn: macApi.draw,
    onSuccess: (data) => { impact('success' as any); setReading(data) },
  })

  const handleDraw = () => {
    impact('medium')
    drawMutation.mutate()
  }

  const handleReveal = () => {
    impact('light')
    setRevealed(true)
  }

  // Draw screen
  if (!reading) {
    return (
      <div className="screen mac-screen">
        <div className="screen-header">
          <h2 className="screen-title">Зеркало Души</h2>
          <p className="screen-subtitle">Метафорические карты для самопознания</p>
        </div>
        <div className="screen-content">
          {drawMutation.isPending && <LoadingSpinner message="Выбираем вашу карту..." />}

          {!drawMutation.isPending && (
            <motion.div
              className="mac-draw-prompt"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className="mac-intro">
                <p>Закройте глаза. Сделайте глубокий вдох.</p>
                <p>Задайте себе вопрос — или просто позвольте карте найти вас.</p>
              </div>

              <div className="mac-deck">
                {[3, 2, 1, 0].map((i) => (
                  <motion.div
                    key={i}
                    className="mac-deck-card"
                    style={{
                      transform: `rotate(${(i - 1.5) * 4}deg)`,
                      zIndex: i,
                    }}
                    animate={{ y: [0, -3, 0] }}
                    transition={{ duration: 2, repeat: Infinity, delay: i * 0.3 }}
                  >
                    <span className="mac-deck-symbol">☽</span>
                  </motion.div>
                ))}
              </div>

              <motion.button
                className="btn-primary btn-draw"
                onClick={handleDraw}
                whileTap={{ scale: 0.96 }}
              >
                Вытянуть карту
              </motion.button>
            </motion.div>
          )}
        </div>
      </div>
    )
  }

  // Card result screen
  const { card } = reading
  const catColor = CATEGORY_COLORS[card.category] || '#a08ce8'

  return (
    <div className="screen mac-screen">
      <div className="screen-header">
        <h2 className="screen-title">Ваша карта</h2>
        <p className="screen-subtitle" style={{ color: catColor }}>
          {CATEGORY_LABELS[card.category] || card.category}
        </p>
      </div>

      <div className="screen-content">
        {/* Card */}
        <motion.div
          className={`mac-card ${revealed ? 'mac-card--revealed' : ''}`}
          initial={{ scale: 0.8, opacity: 0, rotateY: 180 }}
          animate={{ scale: 1, opacity: 1, rotateY: 0 }}
          transition={{ duration: 0.8, type: 'spring' }}
          onClick={!revealed ? handleReveal : undefined}
        >
          <div className="mac-card__emoji">{card.emoji}</div>
          <h3 className="mac-card__name">{card.name_ru}</h3>

          <AnimatePresence>
            {revealed && (
              <motion.div
                className="mac-card__content"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                transition={{ duration: 0.5 }}
              >
                <p className="mac-card__description">{card.description_ru}</p>

                <div className="mac-card__question">
                  <span className="mac-card__label">Вопрос для размышления</span>
                  <p>{card.question_ru}</p>
                </div>

                <div className="mac-card__affirmation">
                  <span className="mac-card__label">Аффирмация</span>
                  <p>{card.affirmation_ru}</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {!revealed && (
            <p className="mac-card__tap-hint">Нажмите, чтобы раскрыть</p>
          )}
        </motion.div>

        {/* New draw button */}
        {revealed && (
          <motion.button
            className="btn-secondary"
            onClick={() => { setReading(null); setRevealed(false); drawMutation.reset() }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            ↻ Новая карта
          </motion.button>
        )}
      </div>
    </div>
  )
}
