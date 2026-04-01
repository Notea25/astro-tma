import { useState } from 'react'
import { motion } from 'framer-motion'
import { useMutation } from '@tanstack/react-query'
import { ZodiacPicker } from '@/components/ui/ZodiacPicker'
import { CityAutocomplete, type CityOption } from '@/components/ui/CityAutocomplete'
import { usersApi } from '@/services/api'
import { useAppStore } from '@/stores/app'
import { useHaptic } from '@/hooks/useTelegram'
import type { ZodiacSign } from '@/types'
import { ZODIAC_SIGNS } from '@/types'

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

type Step = 'welcome' | 'gender' | 'birth_date' | 'birth_city' | 'sign_confirm'

function GenderIcon({ type, size = 64 }: { type: 'male' | 'female'; size?: number }) {
  if (type === 'male') {
    return (
      <svg width={size} height={size} viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <circle cx="24" cy="40" r="16" />
        <path d="M36 28L52 12M52 12H40M52 12v12" />
      </svg>
    )
  }
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="32" cy="24" r="16" />
      <path d="M32 40v18M24 50h16" />
    </svg>
  )
}

export function Onboarding() {
  const [step, setStep] = useState<Step>('welcome')
  const [gender, setGender] = useState<'male' | 'female' | null>(null)
  const [birthDay, setBirthDay] = useState('')
  const [birthMonth, setBirthMonth] = useState('')
  const [birthYear, setBirthYear] = useState('')
  const [birthHour, setBirthHour] = useState('')
  const [birthMinute, setBirthMinute] = useState('')
  const [birthTimeKnown, setBirthTimeKnown] = useState(false)
  const [birthCity, setBirthCity] = useState('')
  const [cityCoords, setCityCoords] = useState<{ lat: number; lng: number } | null>(null)
  const [selectedSign, setSelectedSign] = useState<ZodiacSign | null>(null)

  const { setUser, setOnboardingComplete, setScreen } = useAppStore()
  const { impact, notification } = useHaptic()

  const upsertMutation = useMutation({
    mutationFn: usersApi.upsertMe,
    onSuccess: (user) => setUser(user),
  })

  const genderMutation = useMutation({
    mutationFn: (g: string) => usersApi.setGender(g),
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

  const handleGenderSelect = async (g: 'male' | 'female') => {
    impact('medium')
    setGender(g)
    // Ensure user exists, then set gender
    const user = await upsertMutation.mutateAsync()
    setUser(user)
    await genderMutation.mutateAsync(g)
    setStep('birth_date')
  }

  const birthDate = birthYear && birthMonth && birthDay
    ? `${birthYear}-${birthMonth.padStart(2, '0')}-${birthDay.padStart(2, '0')}`
    : ''

  const isBirthDateValid = () => {
    if (!birthDay || !birthMonth || !birthYear) return false
    const d = parseInt(birthDay), m = parseInt(birthMonth), y = parseInt(birthYear)
    if (d < 1 || d > 31 || m < 1 || m > 12 || y < 1900 || y > new Date().getFullYear()) return false
    return true
  }

  const handleDateNext = () => {
    if (!isBirthDateValid()) return
    impact('light')
    const date = new Date(parseInt(birthYear), parseInt(birthMonth) - 1, parseInt(birthDay))
    setSelectedSign(signFromDate(date))
    setStep('birth_city')
  }

  const handleFinish = async () => {
    impact('medium')
    const user = await upsertMutation.mutateAsync()
    setUser(user)

    if (birthDate && birthCity) {
      const timeStr = birthTimeKnown && birthHour && birthMinute
        ? `${birthHour.padStart(2, '0')}:${birthMinute.padStart(2, '0')}`
        : '12:00'
      const datetime = `${birthDate}T${timeStr}:00`

      await birthMutation.mutateAsync({
        birth_date: datetime,
        birth_time_known: birthTimeKnown,
        birth_city: birthCity,
        ...(cityCoords ?? {}),
      })
    } else {
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
            onClick={() => { impact('light'); setStep('gender') }}
            whileTap={{ scale: 0.97 }}
          >
            Начать путешествие
          </motion.button>
        </motion.div>
      )}

      {/* Gender step */}
      {step === 'gender' && (
        <motion.div
          className="onboarding__step"
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <div className="step-header">
            <button className="btn-back" onClick={() => setStep('welcome')}>&#8592;</button>
            <div className="step-dots">
              <span className="dot active" /><span className="dot" /><span className="dot" /><span className="dot" />
            </div>
          </div>
          <h2 className="step-title">Кто вы?</h2>
          <p className="step-desc">Это поможет сделать предсказания точнее</p>

          <div className="gender-grid">
            <motion.button
              className={`gender-card ${gender === 'male' ? 'gender-card--selected' : ''}`}
              onClick={() => handleGenderSelect('male')}
              whileTap={{ scale: 0.95 }}
              disabled={genderMutation.isPending || upsertMutation.isPending}
            >
              <div className="gender-card__icon">
                <GenderIcon type="male" size={56} />
              </div>
              <span className="gender-card__label">Мужчина</span>
            </motion.button>

            <motion.button
              className={`gender-card ${gender === 'female' ? 'gender-card--selected' : ''}`}
              onClick={() => handleGenderSelect('female')}
              whileTap={{ scale: 0.95 }}
              disabled={genderMutation.isPending || upsertMutation.isPending}
            >
              <div className="gender-card__icon">
                <GenderIcon type="female" size={56} />
              </div>
              <span className="gender-card__label">Женщина</span>
            </motion.button>
          </div>
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
            <button className="btn-back" onClick={() => setStep('gender')}>&#8592;</button>
            <div className="step-dots">
              <span className="dot done" /><span className="dot active" /><span className="dot" /><span className="dot" />
            </div>
          </div>
          <h2 className="step-title">Дата рождения</h2>
          <p className="step-desc">Нужна для расчёта персонального гороскопа</p>
          <div className="form-group">
            <label className="form-label">Дата рождения</label>
            <div className="date-inputs">
              <input
                type="text"
                inputMode="numeric"
                className="form-input date-input"
                placeholder="ДД"
                maxLength={2}
                value={birthDay}
                onChange={(e) => {
                  const v = e.target.value.replace(/\D/g, '')
                  setBirthDay(v)
                  if (v.length === 2) (e.target.nextElementSibling as HTMLInputElement)?.focus()
                }}
              />
              <input
                type="text"
                inputMode="numeric"
                className="form-input date-input"
                placeholder="ММ"
                maxLength={2}
                value={birthMonth}
                onChange={(e) => {
                  const v = e.target.value.replace(/\D/g, '')
                  setBirthMonth(v)
                  if (v.length === 2) (e.target.nextElementSibling as HTMLInputElement)?.focus()
                }}
              />
              <input
                type="text"
                inputMode="numeric"
                className="form-input date-input date-input--year"
                placeholder="ГГГГ"
                maxLength={4}
                value={birthYear}
                onChange={(e) => setBirthYear(e.target.value.replace(/\D/g, ''))}
              />
            </div>
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
              <div className="time-inputs">
                <input
                  type="text"
                  inputMode="numeric"
                  className="form-input date-input"
                  placeholder="ЧЧ"
                  maxLength={2}
                  value={birthHour}
                  onChange={(e) => {
                    const v = e.target.value.replace(/\D/g, '')
                    setBirthHour(v)
                    if (v.length === 2) (e.target.nextElementSibling?.nextElementSibling as HTMLInputElement)?.focus()
                  }}
                />
                <span className="time-separator">:</span>
                <input
                  type="text"
                  inputMode="numeric"
                  className="form-input date-input"
                  placeholder="ММ"
                  maxLength={2}
                  value={birthMinute}
                  onChange={(e) => setBirthMinute(e.target.value.replace(/\D/g, ''))}
                />
              </div>
            </div>
          )}
          <motion.button
            className="btn-primary"
            onClick={handleDateNext}
            disabled={!isBirthDateValid()}
            whileTap={{ scale: 0.97 }}
          >
            Далее
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
            <button className="btn-back" onClick={() => setStep('birth_date')}>&#8592;</button>
            <div className="step-dots">
              <span className="dot done" /><span className="dot done" /><span className="dot active" /><span className="dot" />
            </div>
          </div>
          <h2 className="step-title">Город рождения</h2>
          <p className="step-desc">Нужен для точного расчёта домов натальной карты</p>
          <div className="form-group">
            <label className="form-label">Город рождения</label>
            <CityAutocomplete
              value={birthCity}
              onChange={(v) => { setBirthCity(v); setCityCoords(null) }}
              onSelect={(opt: CityOption) => {
                setBirthCity(opt.displayName)
                setCityCoords({ lat: opt.lat, lng: opt.lng })
              }}
            />
            {cityCoords && (
              <div className="city-autocomplete__confirmed">
                {cityCoords.lat.toFixed(4)} {cityCoords.lat >= 0 ? 'N' : 'S'}
                &nbsp;&nbsp;{cityCoords.lng.toFixed(4)} {cityCoords.lng >= 0 ? 'E' : 'W'}
              </div>
            )}
          </div>
          <motion.button
            className="btn-primary"
            onClick={() => { impact('light'); setStep('sign_confirm') }}
            disabled={!birthCity}
            whileTap={{ scale: 0.97 }}
          >
            Далее
          </motion.button>
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
            <button className="btn-back" onClick={() => setStep('birth_city')}>&#8592;</button>
            <div className="step-dots">
              <span className="dot done" /><span className="dot done" /><span className="dot done" /><span className="dot active" />
            </div>
          </div>
          <h2 className="step-title">Подтвердите знак</h2>
          <p className="step-desc">
            {selectedSign
              ? `Ваш знак: ${ZODIAC_SIGNS.find(s => s.value === selectedSign)?.label}`
              : 'Выберите ваш солнечный знак'}
          </p>
          <ZodiacPicker value={selectedSign} onChange={setSelectedSign} />
          <motion.button
            className="btn-primary"
            onClick={handleFinish}
            disabled={!selectedSign || birthMutation.isPending || upsertMutation.isPending}
            whileTap={{ scale: 0.97 }}
          >
            {birthMutation.isPending ? 'Считаем карту...' : 'Начать'}
          </motion.button>
        </motion.div>
      )}
    </div>
  )
}
