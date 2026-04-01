import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useState } from 'react'
import { EnergyBars } from '@/components/ui/EnergyBars'
import { PremiumGate } from '@/components/ui/PremiumGate'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { horoscopeApi } from '@/services/api'
import { useAppStore } from '@/stores/app'
import { useHaptic } from '@/hooks/useTelegram'
import { ZODIAC_SIGNS } from '@/types'

type Period = 'today' | 'tomorrow' | 'week' | 'month'

const PERIOD_LABELS: Record<Period, string> = {
  today: 'Сегодня', tomorrow: 'Завтра', week: 'Неделя', month: 'Месяц',
}

const PERIOD_PRODUCTS: Record<Exclude<Period, 'today'>, { id: string; stars: number }> = {
  tomorrow: { id: 'horoscope_tomorrow', stars: 25 },
  week:     { id: 'horoscope_week',     stars: 50 },
  month:    { id: 'horoscope_month',    stars: 75 },
}

const NEWS_ITEMS = [
  { emoji: '♄', title: 'Сатурн в Тельце: что ждёт каждый знак', time: '2 часа назад' },
  { emoji: '☿', title: 'Ретроградный Меркурий завершился: время действовать', time: 'вчера' },
  { emoji: '🌕', title: 'Полнолуние в Весах: кризис или возможность?', time: '3 дня назад' },
]

export function Home() {
  const { user, setScreen } = useAppStore()
  const { impact } = useHaptic()
  const [period, setPeriod] = useState<Period>('today')

  const signInfo = ZODIAC_SIGNS.find(s => s.value === user?.sun_sign)

  const { data: horoscope, isLoading } = useQuery({
    queryKey: ['horoscope', period, user?.id],
    queryFn: () => period === 'today'
      ? horoscopeApi.getToday()
      : horoscopeApi.getPeriod(period),
    staleTime: 1000 * 60 * 30, // 30 min
  })

  const { data: moon } = useQuery({
    queryKey: ['moon'],
    queryFn: horoscopeApi.getMoon,
    staleTime: 1000 * 60 * 60, // 1h
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
      <div className="screen-header">
        <div>
          <h1 className="screen-greeting">
            {greeting}{user?.name ? `, ${user.name}` : ''}
          </h1>
          <p className="screen-date">{today}</p>
        </div>
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
        {period === 'today' ? (
          <motion.div
            key="today"
            className="horoscope-card"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="card-tag">✦ Персональный гороскоп</div>
            <div className="card-sign-row">
              <div className="sign-badge">{signInfo?.emoji ?? '✨'}</div>
              <div>
                <div className="sign-name">{signInfo?.label ?? 'Ваш знак'}</div>
                <div className="sign-dates">{signInfo?.dates}</div>
              </div>
            </div>
            {isLoading ? (
              <LoadingSpinner message="Читаем звёзды..." />
            ) : (
              <>
                <p className="horoscope-text">{horoscope?.text_ru}</p>
                {horoscope?.energy && <EnergyBars scores={horoscope.energy} />}
              </>
            )}
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
              className="horoscope-card"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="card-tag">✦ {PERIOD_LABELS[period]}</div>
              {isLoading
                ? <LoadingSpinner />
                : <p className="horoscope-text">{horoscope?.text_ru}</p>
              }
            </motion.div>
          </PremiumGate>
        )}

        {/* Moon card */}
        {moon && (
          <motion.div
            className="moon-card"
            onClick={() => { impact('light'); setScreen('moon') }}
            whileTap={{ scale: 0.98 }}
          >
            <span className="moon-card__emoji">{moon.emoji}</span>
            <div>
              <div className="moon-card__title">{moon.phase_name_ru}</div>
              <p className="moon-card__desc">{moon.description_ru}</p>
            </div>
          </motion.div>
        )}

        {/* Quick actions */}
        <h3 className="section-title">Исследуйте</h3>
        <div className="quick-grid">
          {[
            { icon: '🃏', label: 'Таро',        sub: 'Расклад на день', screen: 'tarot' },
            { icon: '💫', label: 'Совместимость', sub: 'Проверьте союз',  screen: 'compatibility' },
            { icon: '⭕', label: 'Натальная карта', sub: 'Ваш план',      screen: 'natal' },
            { icon: '🌙', label: 'Лунный календарь', sub: 'Фазы луны',   screen: 'moon' },
          ].map((item) => (
            <motion.div
              key={item.label}
              className="quick-card"
              onClick={() => { impact('light'); setScreen(item.screen as any) }}
              whileTap={{ scale: 0.94 }}
            >
              <span className="quick-card__icon">{item.icon}</span>
              <span className="quick-card__label">{item.label}</span>
              <span className="quick-card__sub">{item.sub}</span>
            </motion.div>
          ))}
        </div>

        {/* News */}
        <h3 className="section-title">Астро-новости</h3>
        {NEWS_ITEMS.map((n, i) => (
          <div key={i} className="news-item">
            <span className="news-emoji">{n.emoji}</span>
            <div>
              <div className="news-title">{n.title}</div>
              <div className="news-time">{n.time}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
