import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useState } from 'react'
import { EnergyBars } from '@/components/ui/EnergyBars'
import { PremiumGate } from '@/components/ui/PremiumGate'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { HoroscopeSkeleton, MoonCardSkeleton } from '@/components/ui/Skeleton'
import { MeaningText } from '@/components/ui/MeaningText'
import { horoscopeApi, tarotApi } from '@/services/api'
import { useAppStore } from '@/stores/app'
import { useHaptic } from '@/hooks/useTelegram'
import { ZODIAC_SIGNS } from '@/types'

const POWER_EMOJIS: Record<string, string[]> = {
  aries: ['🔥','⚡','🗡️','🏆','🚀','💥'],
  taurus: ['🌿','💎','🍯','🏔️','🌸','💰'],
  gemini: ['🦋','💬','📚','🎭','✨','🌀'],
  cancer: ['🌙','🏠','💧','🐚','🌊','💫'],
  leo: ['☀️','👑','🦁','🔥','💛','⭐'],
  virgo: ['🌾','💚','📋','🌿','🔬','✅'],
  libra: ['⚖️','🌹','💎','🎨','💕','🕊️'],
  scorpio: ['🦂','🔮','🌑','💀','🖤','🌌'],
  sagittarius: ['🏹','🌍','🔥','🗺️','🐎','🎯'],
  capricorn: ['🏔️','⛰️','🧱','💼','🪨','🏗️'],
  aquarius: ['💡','🌐','⚡','🔭','🛸','🌈'],
  pisces: ['🐟','🌊','💜','🔮','🎵','🌙'],
}

function getPowerEmoji(sign?: string): string {
  if (!sign) return '✨'
  const emojis = POWER_EMOJIS[sign.toLowerCase()] ?? ['✨']
  const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000)
  return emojis[dayOfYear % emojis.length]
}

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
              <svg className="period-tab__lock" width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                <rect x="1.5" y="4.5" width="7" height="5" rx="1"/>
                <path d="M3 4.5V3a2 2 0 0 1 4 0v1.5"/>
              </svg>
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
            <div className="power-emoji-row">
              <span className="power-emoji-row__icon">{getPowerEmoji(user?.sun_sign ?? undefined)}</span>
              <span className="power-emoji-row__text">Ваша энергия дня</span>
            </div>
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
          <div className="tarot-flip" style={{ perspective: '1000px' }}>
            <motion.div
              className="tarot-flip__inner"
              animate={{ rotateY: cardRevealed ? 180 : 0 }}
              transition={{ duration: 0.7, ease: [0.4, 0, 0.2, 1] }}
              style={{ transformStyle: 'preserve-3d', position: 'relative' }}
            >
              {/* Back face */}
              <div
                className="tarot-flip__face tarot-flip__face--back"
                style={{ backfaceVisibility: 'hidden', WebkitBackfaceVisibility: 'hidden' }}
                onClick={() => { impact('medium'); setCardRevealed(true) }}
              >
                <div className="tarot-flip__back-ornament">
                  <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="0.8" opacity="0.5">
                    <rect x="4" y="4" width="40" height="40" rx="4" strokeDasharray="3 3"/>
                    <circle cx="24" cy="24" r="12"/>
                    <circle cx="24" cy="24" r="6"/>
                    <path d="M24 4 L24 12 M24 36 L24 44 M4 24 L12 24 M36 24 L44 24"/>
                    <path d="M24 18 L26.4 22.7 L31.4 23.5 L27.7 27.1 L28.6 32.1 L24 29.6 L19.4 32.1 L20.3 27.1 L16.6 23.5 L21.6 22.7 Z" strokeWidth="0.6"/>
                  </svg>
                </div>
                <span className="tarot-flip__hint">Нажмите, чтобы открыть</span>
                <span className="tarot-flip__free">Бесплатно</span>
              </div>

              {/* Front face */}
              <div
                className="tarot-flip__face tarot-flip__face--front"
                style={{ backfaceVisibility: 'hidden', WebkitBackfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
              >
                {cardLoading ? (
                  <div className="tarot-flip__loading">
                    <LoadingSpinner message="Карты открываются..." />
                  </div>
                ) : dailyCard?.cards?.[0] ? (() => {
                  const card = dailyCard.cards[0]
                  return (
                    <>
                      <div className="tarot-flip__img-wrap">
                        {card.image_url ? (
                          <img src={card.image_url} alt={card.name_ru} className="tarot-flip__img" loading="lazy" />
                        ) : (
                          <div className="tarot-flip__img-fallback">{card.emoji}</div>
                        )}
                        <span className={`tarot-flip__orientation ${card.reversed ? 'tarot-flip__orientation--rev' : ''}`}>
                          {card.reversed ? '↓ Перевёрнутое' : '↑ Прямое'}
                        </span>
                      </div>
                      <div className="tarot-flip__info">
                        <div className="tarot-flip__arcana">{card.arcana === 'major' ? 'Старший аркан' : 'Младший аркан'}</div>
                        <div className="tarot-flip__name">{card.name_ru}</div>
                        <p className="tarot-flip__keywords">{card.keywords_ru?.slice(0, 3).join(' · ')}</p>
                        <MeaningText text={card.meaning_ru} compact />
                      </div>
                    </>
                  )
                })() : null}
              </div>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
