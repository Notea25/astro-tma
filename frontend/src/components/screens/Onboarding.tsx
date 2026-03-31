import { useState } from 'react'
import { motion } from 'framer-motion'
import { useMutation } from '@tanstack/react-query'
import { ZodiacPicker } from '@/components/ui/ZodiacPicker'
import { usersApi } from '@/services/api'
import { useAppStore } from '@/stores/app'
import { useHaptic } from '@/hooks/useTelegram'
import type { ZodiacSign } from '@/types'
import { ZODIAC_SIGNS } from '@/types'

// Map sign to approximate birth month range for auto-detection
function signFromDate(date: Date): ZodiacSign {
  const m = date.getMonth() + 1
  const d = date.getDate()
  if ((m === 3 && d >= 21) || (m === 4 && d <= 19)) return 'aries'
  if ((m === 4 && d >= 20) || (m === 5 && d <= 20)) return 'taurus'
  if ((m === 5 && d >= 21) || (m === 6 && d <= 20)) return 'gemini'
  if ((m === 6 && d >= 21) || (m === 7 && d <= 22)) return 'cancer'
  if ((m === 7 && d >= 23) || (m === 8 && d <= 22)) return 'leo'
  if ((m === 8 && d >= 23) || (m === 9 && d <= 22)) return 'virgo'
  if ((m === 9 && d >= 23) || (m === 10 && d <= 22)) return 'libra'
  if ((m === 10 && d >= 23) || (m === 11 && d <= 21)) return 'scorpio'
  if ((m === 11 && d >= 22) || (m === 12 && d <= 21)) return 'sagittarius'
  if ((m === 12 && d >= 22) || (m === 1 && d <= 19)) return 'capricorn'
  if ((m === 1 && d >= 20) || (m === 2 && d <= 18)) return 'aquarius'
  return 'pisces'
}

type Step = 'welcome' | 'birth_date' | 'birth_city' | 'sign_confirm'

export function Onboarding() {
  const [step, setStep] = useState<Step>('welcome')
  const [birthDate, setBirthDate] = useState('')
  const [birthTime, setBirthTime] = useState('')
  const [birthTimeKnown, setBirthTimeKnown] = useState(false)
  const [birthCity, setBirthCity] = useState('')
  const [selectedSign, setSelectedSign] = useState<ZodiacSign | null>(null)

  const { setUser, setOnboardingComplete, setScreen } = useAppStore()
  const { impact, notification } = useHaptic()

  const upsertMutation = useMutation({
    mutationFn: usersApi.upsertMe,
    onSuccess: (user) => setUser(user),
  })

  const birthMutation = useMutation({
    mutationFn: usersApi.setupBirth,
    onSuccess: () => {
      notification('success')
      setOnboardingComplete(true)
      setScreen('home')
    },
  })

  const handleDateNext = () => {
    if (!birthDate) return
    impact('light')
    const date = new Date(birthDate)
    setSelectedSign(signFromDate(date))
    setStep('birth_city')
  }

  const handleFinish = async () => {
    impact('medium')
    // Ensure user exists first
    const user = await upsertMutation.mutateAsync()
    setUser(user)

    if (birthDate && birthCity) {
      const datetime = birthTimeKnown && birthTime
        ? `${birthDate}T${birthTime}:00`
        : `${birthDate}T12:00:00`

      await birthMutation.mutateAsync({
        birth_date: datetime,
        birth_time_known: birthTimeKnown,
        birth_city: birthCity,
      })
    } else {
      // Skip birth data — go straight to home
      setOnboardingComplete(true)
      setScreen('home')
    }
  }

  return (
    <div className="onboarding">
      {/* Welcome step */}
      {step === 'welcome' && (
        <motion.div
          className="onboarding__step"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <motion.div
            className="onboarding__moon"
            animate={{ y: [0, -12, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
          />
          <h1 className="onboarding__title">Astro</h1>
          <p className="onboarding__subtitle">Астрология & Гороскоп</p>
          <p className="onboarding__desc">
            Персональные гороскопы, таро и лунный календарь — всё написано в звёздах
          </p>
          <motion.button
            className="btn-primary"
            onClick={() => { impact('light'); setStep('birth_date') }}
            whileTap={{ scale: 0.97 }}
          >
            Начать путешествие ✦
          </motion.button>
          <button
            className="btn-ghost"
            onClick={async () => {
              const user = await upsertMutation.mutateAsync()
              setUser(user)
              setOnboardingComplete(true)
              setScreen('home')
            }}
          >
            Пропустить
          </button>
        </motion.div>
      )}

      {/* Birth date step */}
      {step === 'birth_date' && (
        <motion.div
          className="onboarding__step"
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <div className="step-header">
            <button className="btn-back" onClick={() => setStep('welcome')}>←</button>
            <div className="step-dots">
              <span className="dot active" /><span className="dot" /><span className="dot" />
            </div>
          </div>
          <h2 className="step-title">Дата рождения</h2>
          <p className="step-desc">Нужна для расчёта персонального гороскопа</p>
          <div className="form-group">
            <label className="form-label">Дата рождения</label>
            <input
              type="date"
              className="form-input"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
              max={new Date().toISOString().split('T')[0]}
            />
          </div>
          <div className="form-group">
            <label className="form-label checkbox-label">
              <input
                type="checkbox"
                checked={birthTimeKnown}
                onChange={(e) => setBirthTimeKnown(e.target.checked)}
              />
              Знаю точное время рождения
            </label>
          </div>
          {birthTimeKnown && (
            <div className="form-group">
              <label className="form-label">Время рождения</label>
              <input
                type="time"
                className="form-input"
                value={birthTime}
                onChange={(e) => setBirthTime(e.target.value)}
              />
            </div>
          )}
          <motion.button
            className="btn-primary"
            onClick={handleDateNext}
            disabled={!birthDate}
            whileTap={{ scale: 0.97 }}
          >
            Далее →
          </motion.button>
        </motion.div>
      )}

      {/* Birth city step */}
      {step === 'birth_city' && (
        <motion.div
          className="onboarding__step"
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <div className="step-header">
            <button className="btn-back" onClick={() => setStep('birth_date')}>←</button>
            <div className="step-dots">
              <span className="dot done" /><span className="dot active" /><span className="dot" />
            </div>
          </div>
          <h2 className="step-title">Город рождения</h2>
          <p className="step-desc">Нужен для точного расчёта домов натальной карты</p>
          <div className="form-group">
            <label className="form-label">Город рождения</label>
            <input
              type="text"
              className="form-input"
              placeholder="Москва, Лондон, Нью-Йорк..."
              value={birthCity}
              onChange={(e) => setBirthCity(e.target.value)}
            />
          </div>
          <motion.button
            className="btn-primary"
            onClick={() => { impact('light'); setStep('sign_confirm') }}
            disabled={!birthCity}
            whileTap={{ scale: 0.97 }}
          >
            Далее →
          </motion.button>
          <button className="btn-ghost" onClick={() => { setStep('sign_confirm') }}>
            Пропустить
          </button>
        </motion.div>
      )}

      {/* Sign confirmation step */}
      {step === 'sign_confirm' && (
        <motion.div
          className="onboarding__step"
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <div className="step-header">
            <button className="btn-back" onClick={() => setStep('birth_city')}>←</button>
            <div className="step-dots">
              <span className="dot done" /><span className="dot done" /><span className="dot active" />
            </div>
          </div>
          <h2 className="step-title">Подтвердите знак</h2>
          <p className="step-desc">
            {selectedSign
              ? `Ваш знак: ${ZODIAC_SIGNS.find(s => s.value === selectedSign)?.emoji} ${ZODIAC_SIGNS.find(s => s.value === selectedSign)?.label}`
              : 'Выберите ваш солнечный знак'}
          </p>
          <ZodiacPicker value={selectedSign} onChange={setSelectedSign} />
          <motion.button
            className="btn-primary"
            onClick={handleFinish}
            disabled={!selectedSign || birthMutation.isPending || upsertMutation.isPending}
            whileTap={{ scale: 0.97 }}
          >
            {birthMutation.isPending ? '⏳ Считаем карту...' : 'Начать ✦'}
          </motion.button>
        </motion.div>
      )}
    </div>
  )
}
