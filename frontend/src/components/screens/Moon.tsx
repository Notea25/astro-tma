import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { horoscopeApi } from '@/services/api'
import { useHaptic } from '@/hooks/useTelegram'

const PHASE_ENERGY: Record<string, string> = {
  'Новолуние': 'Время намерений и нового начала. Сажайте семена желаний — Луна поддержит любой старт.',
  'Растущий серп': 'Энергия нарастает. Действуйте, стройте планы, двигайтесь вперёд.',
  'Первая четверть': 'Момент решений. Преодолевайте препятствия — сила на вашей стороне.',
  'Растущая Луна': 'Прилив сил. Занимайтесь творчеством, общением, новыми проектами.',
  'Полнолуние': 'Пик энергии. Завершайте начатое, практикуйте благодарность, отпускайте лишнее.',
  'Убывающая Луна': 'Время осмысления. Делитесь знаниями и опытом. Отдавайте то, что накопили, — это освобождает пространство для нового.',
  'Последняя четверть': 'Очищение и отпускание. Избавляйтесь от ненужного — физического и эмоционального.',
  'Убывающий серп': 'Отдых и восстановление. Прислушайтесь к себе, замедлитесь перед новым циклом.',
}

export function Moon() {
  const { impact } = useHaptic()
  const now = new Date()
  const [year] = useState(now.getFullYear())
  const [month] = useState(now.getMonth() + 1)
  const [selectedDay, setSelectedDay] = useState(now.getDate())

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

  const todayNum = now.getDate()
  const selectedData = calendar?.find(d => d.day === selectedDay)
  const isToday = selectedDay === todayNum

  const DAY_NAMES = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс']

  return (
    <div className="screen moon-screen">
      <div className="screen-header">
        <h2 className="screen-title">Лунный календарь</h2>
      </div>

      <div className="screen-content">
        {/* Big moon */}
        <div className="moon-hero">
          <motion.div
            key={selectedData?.emoji}
            className="moon-hero__emoji"
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
          >
            {selectedData?.emoji ?? moonPhase?.emoji ?? '🌙'}
          </motion.div>
        </div>

        {/* Phase info for selected day */}
        {(selectedData || moonPhase) && (
          <div className="moon-phase-card">
            {!isToday && (
              <div className="moon-phase-card__date">{selectedDay} {['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'][month - 1]}</div>
            )}
            <div className="moon-phase-card__name">
              {selectedData?.phase_name_ru ?? moonPhase?.phase_name_ru}
            </div>
            <div className="moon-phase-card__illum">
              Освещённость: {Math.round((selectedData?.illumination ?? moonPhase?.illumination ?? 0) * 100)}%
            </div>
            {PHASE_ENERGY[selectedData?.phase_name_ru ?? moonPhase?.phase_name_ru ?? ''] && (
              <p className="moon-phase-card__desc">
                {PHASE_ENERGY[selectedData?.phase_name_ru ?? moonPhase?.phase_name_ru ?? '']}
              </p>
            )}
          </div>
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
                const isTodayCell = day.day === todayNum
                const isSelected = day.day === selectedDay
                return (
                  <motion.div
                    key={day.day}
                    className={`moon-calendar__cell${isTodayCell ? ' today' : ''}${isSelected && !isTodayCell ? ' selected' : ''}`}
                    onClick={() => { impact('light'); setSelectedDay(day.day) }}
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

      </div>
    </div>
  )
}
