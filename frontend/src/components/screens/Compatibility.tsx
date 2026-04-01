import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { ZodiacPicker } from '@/components/ui/ZodiacPicker'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { IconHeart, ZODIAC_ICONS } from '@/components/ui/Icons'
import { compatibilityApi } from '@/services/api'
import { useAppStore } from '@/stores/app'
import { useHaptic } from '@/hooks/useTelegram'
import { ZODIAC_SIGNS, type ZodiacSign } from '@/types'

function ScoreCircle({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div className="score-circle">
      <div className="score-circle__ring" style={{ '--score': value, '--color': color } as any}>
        <span className="score-circle__val">{value}%</span>
      </div>
      <span className="score-circle__label">{label}</span>
    </div>
  )
}

export function Compatibility() {
  const { user } = useAppStore()
  const { impact } = useHaptic()

  const userSign = user?.sun_sign as ZodiacSign | undefined
  const [signA, setSignA] = useState<ZodiacSign | null>(userSign ?? null)
  const [signB, setSignB] = useState<ZodiacSign | null>(null)
  const [showPickerFor, setShowPickerFor] = useState<'a' | 'b' | null>(null)
  const [submitted, setSubmitted] = useState(false)

  const { data: result, isLoading } = useQuery({
    queryKey: ['compatibility', signA, signB],
    queryFn: () => compatibilityApi.get(signA!, signB!),
    enabled: submitted && !!signA && !!signB,
    staleTime: Infinity,
  })

  const handleCheck = () => {
    if (!signA || !signB) return
    impact('medium')
    setSubmitted(true)
  }

  const signAInfo = ZODIAC_SIGNS.find(s => s.value === signA)
  const signBInfo = ZODIAC_SIGNS.find(s => s.value === signB)

  return (
    <div className="screen compat-screen">
      <div className="screen-header">
        <h2 className="screen-title">Совместимость</h2>
        <p className="screen-subtitle">Проверьте астрологическую совместимость</p>
      </div>

      <div className="screen-content">
        {/* Sign selectors */}
        <div className="compat-selectors">
          <motion.div
            className={`compat-sign-btn ${signA ? 'has-sign' : ''}`}
            onClick={() => { impact('light'); setShowPickerFor('a') }}
            whileTap={{ scale: 0.94 }}
          >
            <span className="compat-sign-btn__emoji">
              {signA && ZODIAC_ICONS[signA] ? (() => { const Z = ZODIAC_ICONS[signA]; return <Z size={32} /> })() : '?'}
            </span>
            <span className="compat-sign-btn__label">{signAInfo?.label ?? 'Выбрать'}</span>
          </motion.div>

          <div className="compat-heart"><IconHeart size={24} /></div>

          <motion.div
            className={`compat-sign-btn ${signB ? 'has-sign' : ''}`}
            onClick={() => { impact('light'); setShowPickerFor('b') }}
            whileTap={{ scale: 0.94 }}
          >
            <span className="compat-sign-btn__emoji">
              {signB && ZODIAC_ICONS[signB] ? (() => { const Z = ZODIAC_ICONS[signB]; return <Z size={32} /> })() : '?'}
            </span>
            <span className="compat-sign-btn__label">{signBInfo?.label ?? 'Выбрать'}</span>
          </motion.div>
        </div>

        <motion.button
          className="btn-primary"
          onClick={handleCheck}
          disabled={!signA || !signB || isLoading}
          whileTap={{ scale: 0.97 }}
        >
          Проверить совместимость
        </motion.button>

        {/* Results */}
        <AnimatePresence>
          {isLoading && <LoadingSpinner message="Вычисляем совместимость..." />}

          {result && !isLoading && (
            <motion.div
              className="compat-result"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {/* Main score */}
              <div className="compat-overall">
                <motion.div
                  className="compat-overall__score"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 200, delay: 0.2 }}
                >
                  {result.overall}%
                </motion.div>
                <div className={`compat-overall__tier tier-${result.tier}`}>
                  {result.tier === 'high' ? '✨ Высокая' : result.tier === 'medium' ? '🌟 Средняя' : '⚡ Низкая'} совместимость
                </div>
              </div>

              {/* Score breakdown */}
              <div className="score-circles">
                <ScoreCircle value={result.love}          label="Любовь"   color="#c9a84c" />
                <ScoreCircle value={result.communication} label="Общение"  color="#7c5cbf" />
                <ScoreCircle value={result.trust}         label="Доверие"  color="#3dd68c" />
                <ScoreCircle value={result.passion}       label="Страсть"  color="#ff6b6b" />
              </div>

              {/* Description */}
              <p className="compat-description">{result.description_ru}</p>

              {/* Strengths & Challenges */}
              {result.strengths_ru.length > 0 && (
                <div className="compat-list compat-list--strengths">
                  <div className="compat-list__title">💚 Сильные стороны</div>
                  {result.strengths_ru.map((s, i) => (
                    <div key={i} className="compat-list__item">• {s}</div>
                  ))}
                </div>
              )}
              {result.challenges_ru.length > 0 && (
                <div className="compat-list compat-list--challenges">
                  <div className="compat-list__title">⚡ Вызовы</div>
                  {result.challenges_ru.map((c, i) => (
                    <div key={i} className="compat-list__item">• {c}</div>
                  ))}
                </div>
              )}

              <button
                className="btn-secondary"
                onClick={() => { setSubmitted(false); setSignB(null) }}
              >
                Проверить другую пару
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Sign picker modal */}
      <AnimatePresence>
        {showPickerFor && (
          <motion.div
            className="modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowPickerFor(null)}
          >
            <motion.div
              className="modal-sheet"
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="modal-handle" />
              <h3 className="modal-title">Выберите знак</h3>
              <ZodiacPicker
                value={showPickerFor === 'a' ? signA : signB}
                onChange={(sign) => {
                  impact('selection' as any)
                  if (showPickerFor === 'a') setSignA(sign)
                  else setSignB(sign)
                  setShowPickerFor(null)
                  setSubmitted(false)
                }}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
