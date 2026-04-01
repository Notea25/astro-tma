import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { horoscopeApi } from '@/services/api'
import { useHaptic } from '@/hooks/useTelegram'

export function Moon() {
  const { impact } = useHaptic()
  const now = new Date()
  const [year] = useState(now.getFullYear())
  const [month] = useState(now.getMonth() + 1)

  const { data: moonPhase } = useQuery({
    queryKey: ['moon-phase'],
    queryFn: horoscopeApi.getMoon,
    staleTime: 1000 * 60 * 60,
  })

  const { data: calendarResp } = useQuery({
    queryKey: ['moon-calendar', year, month],
    queryFn: () => horoscopeApi.getMoonCalendar(year, month),
    staleTime: 1000 * 60 * 60 * 24,
  })
  const calendar = calendarResp?.days

  const MONTH_NAMES = [
    'Январь','Февраль','Март','Апрель','Май','Июнь',
    'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь',
  ]
  const DAY_NAMES = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс']

  return (
    <div className="screen moon-screen">
      <div className="screen-header">
        <h2 className="screen-title">Лунный календарь</h2>
        <p className="screen-subtitle">{MONTH_NAMES[month - 1]} {year}</p>
      </div>

      <div className="screen-content">
        {/* Big moon */}
        <div className="moon-hero">
          <motion.div
            className="moon-hero__emoji"
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
          >
            {moonPhase?.emoji ?? '🌙'}
          </motion.div>
        </div>

        {/* Current phase info */}
        {moonPhase && (
          <motion.div
            className="moon-phase-card"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="moon-phase-card__name">{moonPhase.phase_name_ru}</div>
            <div className="moon-phase-card__illum">
              Освещённость: {Math.round(moonPhase.illumination * 100)}%
            </div>
            <p className="moon-phase-card__desc">{moonPhase.description_ru}</p>
          </motion.div>
        )}

        {/* Monthly calendar grid */}
        {calendar && (
          <div className="moon-calendar">
            <div className="moon-calendar__days-header">
              {DAY_NAMES.map(d => (
                <div key={d} className="moon-calendar__day-label">{d}</div>
              ))}
            </div>
            <div className="moon-calendar__grid">
              {/* Calculate leading empty cells for month start */}
              {(() => {
                const firstDay = new Date(year, month - 1, 1).getDay()
                const leadingCells = firstDay === 0 ? 6 : firstDay - 1
                const empties = Array.from({ length: leadingCells }, (_, i) => (
                  <div key={`e${i}`} className="moon-calendar__cell moon-calendar__cell--empty" />
                ))
                return empties
              })()}
              {calendar.map((day) => {
                const isToday = day.day === now.getDate() && month === now.getMonth() + 1
                return (
                  <motion.div
                    key={day.day}
                    className={`moon-calendar__cell ${isToday ? 'today' : ''}`}
                    onClick={() => impact('light')}
                    whileTap={{ scale: 0.88 }}
                    title={day.phase_name_ru}
                  >
                    <span className="moon-calendar__phase">{day.emoji}</span>
                    <span className="moon-calendar__num">{day.day}</span>
                  </motion.div>
                )
              })}
            </div>
          </div>
        )}

        {/* Energy tip */}
        <div className="moon-tip">
          <span className="moon-tip__icon">⚡</span>
          <div>
            <div className="moon-tip__title">Энергия дня</div>
            <p className="moon-tip__text">
              {moonPhase?.description_ru ?? 'Прислушайтесь к лунным ритмам. Синхронизируйтесь с природными циклами.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
