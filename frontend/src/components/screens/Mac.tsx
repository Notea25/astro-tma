import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { macApi } from '@/services/api'
import { useAppStore } from '@/stores/app'
import { useHaptic } from '@/hooks/useTelegram'
import { useTelegramBackButton } from '@/hooks/useTelegram'
import type { MacReadingResponse } from '@/types'


export function Mac() {
  const { setScreen } = useAppStore()
  const { impact } = useHaptic()
  const [reading, setReading] = useState<MacReadingResponse | null>(null)
  const [revealed, setRevealed] = useState(false)

  const handleBack = useCallback(() => {
    if (reading) { setReading(null); setRevealed(false) } else { setScreen('discover', 'back') }
  }, [reading, setScreen])

  useTelegramBackButton(handleBack, true)

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
        <div className="screen-header screen-header--with-back">
          <button className="back-btn" onClick={handleBack} aria-label="Назад">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"><path d="M13 4l-6 6 6 6"/></svg>
          </button>
          <h2 className="screen-title">Зеркало Души</h2>
        </div>
        <div className="screen-content">
          {drawMutation.isPending && <LoadingSpinner message="Выбираем вашу карту..." />}

          {drawMutation.isError && (
            <div className="error-state">
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" opacity="0.5">
                <circle cx="16" cy="16" r="13"/>
                <line x1="16" y1="10" x2="16" y2="17"/>
                <circle cx="16" cy="21" r="1" fill="currentColor" stroke="none"/>
              </svg>
              <p>Не удалось выбрать карту. Попробуйте ещё раз.</p>
              <button className="btn-ghost" onClick={() => drawMutation.reset()}>Повторить</button>
            </div>
          )}

          {!drawMutation.isPending && !drawMutation.isError && (
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
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.35, delay: i * 0.06, ease: 'easeOut' }}
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
  return (
    <div className="screen mac-screen">
      <div className="screen-header screen-header--with-back">
        <button className="back-btn" onClick={handleBack} aria-label="Назад">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"><path d="M13 4l-6 6 6 6"/></svg>
        </button>
        <h2 className="screen-title">Ваша карта</h2>
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
            className="btn-secondary btn-with-icon"
            onClick={() => { setReading(null); setRevealed(false); drawMutation.reset() }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M1.5 7.5A6 6 0 0 1 13 4.5M13.5 7.5A6 6 0 0 1 2 10.5"/>
              <polyline points="11,2 13,4.5 10.5,6.5"/>
              <polyline points="4,12.5 2,10.5 4.5,8.5"/>
            </svg>
            Новая карта
          </motion.button>
        )}
      </div>
    </div>
  )
}
