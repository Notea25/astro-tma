import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useState } from 'react'
import { EnergyBars } from '@/components/ui/EnergyBars'
import { PremiumGate } from '@/components/ui/PremiumGate'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { HoroscopeSkeleton, MoonCardSkeleton } from '@/components/ui/Skeleton'
import { horoscopeApi, tarotApi } from '@/services/api'
import { useAppStore } from '@/stores/app'
import { useHaptic } from '@/hooks/useTelegram'
import { ZODIAC_SIGNS } from '@/types'

type Period = 'today' | 'tomorrow' | 'week' | 'month'

const PERIOD_LABELS: Record<Period, string> = {
  today: 'Сегодня', tomorrow: 'Завтра', week: 'Неделя', month: 'Месяц',
}
const PERIOD_PRODUCTS: Record<Exclude<Period,'today'>, { id: string; stars: number }> = {
  tomorrow: { id: 'horoscope_tomorrow', stars: 25 },
  week:     { id: 'horoscope_week',     stars: 50 },
  month:    { id: 'horoscope_month',    stars: 75 },
}

export function Home() {
  const { user, setScreen } = useAppStore()
  const { impact } = useHaptic()
  const [period, setPeriod] = useState<Period>('today')
  const [cardRevealed, setCardRevealed] = useState(false)

  const signInfo = ZODIAC_SIGNS.find(s => s.value === user?.sun_sign)

  const { data: horoscope, isLoading } = useQuery({
    queryKey: ['horoscope', period, user?.id],
    queryFn: () => period === 'today' ? horoscopeApi.getToday() : horoscopeApi.getPeriod(period),
    staleTime: 1000 * 60 * 30,
  })

  const { data: moon, isLoading: moonLoading } = useQuery({
    queryKey: ['moon'],
    queryFn: horoscopeApi.getMoon,
    staleTime: 1000 * 60 * 60,
  })

  const { data: dailyCard, isLoading: cardLoading } = useQuery({
    queryKey: ['tarot-daily'],
    queryFn: () => tarotApi.draw('single'),
    enabled: cardRevealed,
    staleTime: 1000 * 60 * 60 * 12,
  })

  const greeting = (() => {
    const h = new Date().getHours()
    return h < 12 ? 'Доброе утро' : h < 18 ? 'Добрый день' : 'Добрый вечер'
  })()

  const today = new Date().toLocaleDateString('ru-RU', {
    weekday: 'long', day: 'numeric', month: 'long',
  })

  return (
    <div className="screen home-screen">
      {/* Header */}
      <div className="screen-header home-header">
        <div>
          <h1 className="screen-greeting">
            {greeting}{user?.name ? `, ${user.name}` : ''}
          </h1>
          <p className="screen-date">{today}</p>
        </div>
        <button
          className="header-avatar"
          onClick={() => { impact('light'); setScreen('profile') }}
          aria-label="Профиль"
        >
          {user?.name?.[0]?.toUpperCase() || '?'}
        </button>
      </div>

      {/* Period tabs */}
      <div className="period-tabs">
        {(['today', 'tomorrow', 'week', 'month'] as Period[]).map((p) => (
          <button
            key={p}
            className={`period-tab ${period === p ? 'active' : ''}`}
            onClick={() => { impact('light'); setPeriod(p) }}
          >
            {PERIOD_LABELS[p]}
            {p !== 'today' && !user?.is_premium && (
              <span className="period-tab__lock">✦</span>
            )}
          </button>
        ))}
      </div>

      <div className="screen-content">
        {/* Horoscope card */}
        {isLoading ? (
          <HoroscopeSkeleton />
        ) : period === 'today' ? (
          <motion.div
            key="today"
            className="horoscope-card glass-gold"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="card-tag">✦ Гороскоп на сегодня</div>
            <div className="card-sign-row">
              <div className="sign-badge">{signInfo?.emoji ?? '✦'}</div>
              <div>
                <div className="sign-name">{signInfo?.label ?? 'Ваш знак'}</div>
                <div className="sign-dates">{signInfo?.dates}</div>
              </div>
            </div>
            <p className="horoscope-text">{horoscope?.text_ru}</p>
            {horoscope?.energy && <EnergyBars scores={horoscope.energy} />}
          </motion.div>
        ) : (
          <PremiumGate
            locked={!user?.is_premium}
            productId={PERIOD_PRODUCTS[period as Exclude<Period,'today'>].id}
            productName={`Гороскоп — ${PERIOD_LABELS[period]}`}
            stars={PERIOD_PRODUCTS[period as Exclude<Period,'today'>].stars}
          >
            <motion.div
              key={period}
              className="horoscope-card glass-gold"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="card-tag">✦ {PERIOD_LABELS[period]}</div>
              <p className="horoscope-text">{horoscope?.text_ru}</p>
            </motion.div>
          </PremiumGate>
        )}

        {/* Moon card */}
        {moonLoading && <MoonCardSkeleton />}
        {moon && (
          <motion.div
            className="moon-card glass-purp"
            onClick={() => { impact('light'); setScreen('moon') }}
            whileTap={{ scale: 0.98 }}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 }}
          >
            <span className="moon-card__emoji">{moon.emoji}</span>
            <div>
              <div className="moon-card__title">{moon.phase_name_ru}</div>
              <div className="moon-card__illum">Освещённость {Math.round(moon.illumination * 100)}%</div>
            </div>
            <svg className="moon-card__arrow" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 3l5 5-5 5"/>
            </svg>
          </motion.div>
        )}

        {/* Tarot card of the day */}
        <motion.div
          className="tarot-day-card"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.14 }}
        >
          <div className="card-tag">✦ Карта таро на сегодня</div>
          {!cardRevealed ? (
            <motion.button
              className="tarot-day-card__reveal"
              onClick={() => { impact('medium'); setCardRevealed(true) }}
              whileTap={{ scale: 0.96 }}
            >
              <div className="tarot-day-card__back">
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" opacity="0.4">
                  <rect x="4" y="2" width="24" height="28" rx="3"/>
                  <path d="M16 8 L16 24 M8 16 L24 16"/>
                  <circle cx="16" cy="16" r="5"/>
                </svg>
              </div>
              <span className="tarot-day-card__hint">Нажмите, чтобы открыть</span>
              <span className="tarot-day-card__free">Бесплатно</span>
            </motion.button>
          ) : cardLoading ? (
            <LoadingSpinner message="Карты открываются..." />
          ) : dailyCard?.cards?.[0] ? (
            <div className="tarot-day-card__result">
              <div className="tarot-day-card__name">{dailyCard.cards[0].name_ru}</div>
              <p className="tarot-day-card__text">{dailyCard.cards[0].keywords_ru?.join(' · ')}</p>
            </div>
          ) : null}
        </motion.div>
      </div>
    </div>
  )
}
