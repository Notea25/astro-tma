import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { PremiumGate } from '@/components/ui/PremiumGate'
import { NatalBasicSkeleton } from '@/components/ui/Skeleton'
import { useAppStore } from '@/stores/app'
import { natalApi } from '@/services/api'
import { ZODIAC_SIGNS } from '@/types'

// Render LLM reading: split by **Section** markers into visual blocks
function ReadingBlocks({ text }: { text: string }) {
  // Remove leading # header line if present
  const cleaned = text.replace(/^#[^\n]*\n?/, '').trim()

  // Split into segments: ["intro text", "SectionTitle", "body", "SectionTitle", "body", ...]
  const parts = cleaned.split(/\*\*([^*]+)\*\*/)

  const blocks: { title?: string; body: string }[] = []
  let i = 0

  // If text starts before first **, treat as intro
  if (parts[0].trim()) {
    blocks.push({ body: parts[0].trim() })
  }
  i = 1

  while (i < parts.length) {
    const title = parts[i]?.trim()
    const body = parts[i + 1]?.trim() ?? ''
    if (title) blocks.push({ title, body })
    i += 2
  }

  return (
    <div className="natal-reading-blocks">
      {blocks.map((block, idx) => (
        <div key={idx} className={block.title ? 'natal-reading-section' : 'natal-reading-intro'}>
          {block.title && <div className="natal-reading-section__title">{block.title}</div>}
          {block.body && <p className="natal-reading-section__body">{block.body}</p>}
        </div>
      ))}
    </div>
  )
}

// Backend returns English sign names — translate to Russian
const SIGN_EN_TO_RU: Record<string, string> = {
  Aries: 'Овен', Taurus: 'Телец', Gemini: 'Близнецы', Cancer: 'Рак',
  Leo: 'Лев', Virgo: 'Дева', Libra: 'Весы', Scorpio: 'Скорпион',
  Sagittarius: 'Стрелец', Capricorn: 'Козерог', Aquarius: 'Водолей', Pisces: 'Рыбы',
}
const toRu = (s: string | null | undefined) => (s ? (SIGN_EN_TO_RU[s] ?? s) : '—')

// ── Zodiac sign positions on wheel (30° each) ─────────────────────────────
const ZODIAC_SYMBOLS = ['♈','♉','♊','♋','♌','♍','♎','♏','♐','♑','♒','♓']
const ZODIAC_NAMES_EN = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']

const ELEMENTS: Record<string, { label: string; emoji: string; signs: string[] }> = {
  fire:  { label: 'Огонь', emoji: '🔥', signs: ['Aries','Leo','Sagittarius'] },
  earth: { label: 'Земля', emoji: '🌍', signs: ['Taurus','Virgo','Capricorn'] },
  air:   { label: 'Воздух', emoji: '💨', signs: ['Gemini','Libra','Aquarius'] },
  water: { label: 'Вода', emoji: '💧', signs: ['Cancer','Scorpio','Pisces'] },
}

const SIGN_TRAITS: Record<string, string[]> = {
  Aries: ['Смелый','Энергичный','Лидер','Импульсивный','Прямолинейный','Нетерпеливый'],
  Taurus: ['Стабильный','Чувственный','Практичный','Верный','Упрямый','Надёжный'],
  Gemini: ['Общительный','Любознательный','Остроумный','Переменчивый','Адаптивный','Двойственный'],
  Cancer: ['Заботливый','Интуитивный','Эмоциональный','Защитник','Домашний','Чувствительный'],
  Leo: ['Харизматичный','Творческий','Щедрый','Гордый','Драматичный','Вдохновляющий'],
  Virgo: ['Аналитичный','Практичный','Трудолюбивый','Скромный','Перфекционист','Внимательный'],
  Libra: ['Гармоничный','Дипломатичный','Справедливый','Эстетичный','Нерешительный','Обаятельный'],
  Scorpio: ['Страстный','Глубокий','Проницательный','Сильный','Магнетичный','Трансформатор'],
  Sagittarius: ['Свободный','Оптимист','Философ','Искатель','Честный','Авантюрный'],
  Capricorn: ['Амбициозный','Дисциплинированный','Терпеливый','Ответственный','Стратег','Серьёзный'],
  Aquarius: ['Оригинальный','Независимый','Гуманист','Визионер','Бунтарь','Прогрессивный'],
  Pisces: ['Интуитивный','Мечтательный','Сострадательный','Творческий','Эмпатичный','Мистический'],
}

// ── SVG Natal Wheel ────────────────────────────────────────────────────────
function NatalWheel({ sunSign, moonSign, ascSign }: { sunSign?: string; moonSign?: string; ascSign?: string }) {
  const signIdx = (s?: string) => ZODIAC_NAMES_EN.indexOf(s ?? '')

  const planetDot = (sign?: string, r: number = 55, color: string = '#f0d48a') => {
    const idx = signIdx(sign)
    if (idx < 0) return null
    const angle = (idx * 30 + 15) * Math.PI / 180 - Math.PI / 2
    return <circle cx={100 + Math.cos(angle) * r} cy={100 + Math.sin(angle) * r} r="4" fill={color} opacity="0.9" />
  }

  return (
    <div className="natal-wheel-wrap">
      <svg viewBox="0 0 200 200" width="170" height="170" className="natal-wheel">
        {/* Circles */}
        <circle cx="100" cy="100" r="92" fill="none" stroke="rgba(212,178,84,0.12)" strokeWidth="0.5"/>
        <circle cx="100" cy="100" r="70" fill="none" stroke="rgba(212,178,84,0.08)" strokeWidth="0.5"/>
        <circle cx="100" cy="100" r="42" fill="none" stroke="rgba(212,178,84,0.06)" strokeWidth="0.5"/>
        {/* 12 segment lines */}
        {Array.from({length: 12}, (_, i) => {
          const a = (i * 30) * Math.PI / 180 - Math.PI / 2
          return <line key={i} x1={100 + Math.cos(a)*42} y1={100 + Math.sin(a)*42} x2={100 + Math.cos(a)*92} y2={100 + Math.sin(a)*92} stroke="rgba(212,178,84,0.06)" strokeWidth="0.5"/>
        })}
        {/* Zodiac symbols on outer ring */}
        {ZODIAC_SYMBOLS.map((sym, i) => {
          const a = (i * 30 + 15) * Math.PI / 180 - Math.PI / 2
          const x = 100 + Math.cos(a) * 81
          const y = 100 + Math.sin(a) * 81
          return <text key={i} x={x} y={y} textAnchor="middle" dominantBaseline="central" fontSize="8" fill="rgba(212,178,84,0.35)">{sym}</text>
        })}
        {/* Planet dots */}
        {planetDot(sunSign, 55, '#f0d48a')}
        {planetDot(moonSign, 55, '#d0c4f5')}
        {planetDot(ascSign, 55, '#b08ef0')}
        {/* Center sun symbol */}
        <text x="100" y="100" textAnchor="middle" dominantBaseline="central" fontSize="22" fill="rgba(212,178,84,0.6)">
          {ZODIAC_SYMBOLS[signIdx(sunSign)] ?? '☉'}
        </text>
      </svg>
    </div>
  )
}

const PLANET_ROWS = [
  { key: 'sun',     label: '☉ Солнце',   desc: 'Ядро личности, творческая сила' },
  { key: 'moon',    label: '☽ Луна',     desc: 'Эмоции, интуиция, подсознание' },
  { key: 'mercury', label: '☿ Меркурий', desc: 'Мышление, коммуникация' },
  { key: 'venus',   label: '♀ Венера',   desc: 'Любовь, ценности, красота' },
  { key: 'mars',    label: '♂ Марс',     desc: 'Энергия, действие, желание' },
  { key: 'jupiter', label: '♃ Юпитер',  desc: 'Удача, рост, философия' },
  { key: 'saturn',  label: '♄ Сатурн',  desc: 'Дисциплина, уроки, структура' },
]

export function Natal() {
  const { user, setScreen } = useAppStore()
  const hasBirthData = !!user?.birth_city

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['natal-summary'],
    queryFn: natalApi.getSummary,
    enabled: hasBirthData,
    staleTime: 1000 * 60 * 10,
  })

  const { data: full, isLoading: fullLoading } = useQuery({
    queryKey: ['natal-full'],
    queryFn: natalApi.getFull,
    enabled: hasBirthData && (summary?.has_chart ?? false),
    staleTime: 1000 * 60 * 60,
  })

  const sunSign = summary?.sun_sign ?? user?.sun_sign
  const userSign = ZODIAC_SIGNS.find(s => s.value === sunSign)

  return (
    <div className="screen natal-screen">
      <div className="screen-header">
        <h2 className="screen-title">Натальная карта</h2>
      </div>

      <div className="screen-content">
        {!hasBirthData ? (
          <motion.div
            className="empty-state"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <svg className="empty-state__illustration" width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="40" cy="40" r="38" stroke="currentColor" strokeWidth="1" strokeDasharray="4 3" opacity="0.2"/>
              <circle cx="40" cy="40" r="26" stroke="currentColor" strokeWidth="1" opacity="0.3"/>
              <circle cx="40" cy="40" r="14" stroke="currentColor" strokeWidth="1.2" opacity="0.5"/>
              <circle cx="40" cy="40" r="3" fill="currentColor" opacity="0.6"/>
              <line x1="40" y1="2" x2="40" y2="14" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.5"/>
              <line x1="40" y1="66" x2="40" y2="78" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.5"/>
              <line x1="2" y1="40" x2="14" y2="40" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.5"/>
              <line x1="66" y1="40" x2="78" y2="40" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.5"/>
              <circle cx="60" cy="20" r="4" stroke="currentColor" strokeWidth="1" opacity="0.4"/>
              <circle cx="20" cy="60" r="3" stroke="currentColor" strokeWidth="1" opacity="0.3"/>
              <circle cx="20" cy="20" r="2" fill="currentColor" opacity="0.3"/>
            </svg>
            <h3 className="empty-state__title">Добавьте данные рождения</h3>
            <p className="empty-state__desc">Для расчёта натальной карты нужны<br/>дата, время и город рождения</p>
            <button className="btn-primary" onClick={() => setScreen('profile')}>Указать данные</button>
          </motion.div>
        ) : (
          <>
            {/* Basic (free) — sun/moon/ascendant */}
            {summaryLoading ? (
              <NatalBasicSkeleton />
            ) : (
              <>
              {/* ── SVG Wheel ── */}
              <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5 }}>
                <NatalWheel sunSign={summary?.sun_sign ?? undefined} moonSign={summary?.moon_sign ?? undefined} ascSign={summary?.ascendant_sign ?? undefined} />
              </motion.div>

              {/* ── Elements distribution ── */}
              {summary?.sun_sign && (() => {
                const planets = [summary.sun_sign, summary.moon_sign, summary.ascendant_sign].filter(Boolean) as string[]
                return (
                  <div className="natal-elements">
                    {Object.entries(ELEMENTS).map(([key, el]) => {
                      const count = planets.filter(p => el.signs.includes(p)).length
                      return (
                        <div key={key} className="natal-element-card">
                          <span className="natal-element-card__emoji">{el.emoji}</span>
                          <span className="natal-element-card__label">{el.label}</span>
                          <span className="natal-element-card__count">{count}/{planets.length}</span>
                        </div>
                      )
                    })}
                  </div>
                )
              })()}

              {/* ── Personality traits ── */}
              {summary?.sun_sign && SIGN_TRAITS[summary.sun_sign] && (
                <div className="natal-traits">
                  {SIGN_TRAITS[summary.sun_sign].map(trait => (
                    <span key={trait} className="natal-trait-pill">{trait}</span>
                  ))}
                </div>
              )}

              <motion.div
                className="natal-card natal-card--basic"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="natal-card__tag">✦ Базовый портрет</div>
                <div className="natal-sign-row">
                  <span className="natal-sign-emoji">{userSign?.emoji ?? '☉'}</span>
                  <div>
                    <div className="natal-sign-name">{userSign?.label ?? toRu(sunSign)}</div>
                    <div className="natal-sign-dates">{userSign?.dates}</div>
                  </div>
                </div>
                <div className="natal-chips">
                  {summary?.moon_sign && (
                    <div className="natal-chip">
                      <span className="natal-chip__symbol">☽</span>
                      <div>
                        <div className="natal-chip__label">Луна</div>
                        <div className="natal-chip__value">{toRu(summary.moon_sign)}</div>
                      </div>
                    </div>
                  )}
                  {summary?.ascendant_sign && (
                    <div className="natal-chip">
                      <span className="natal-chip__symbol">AC</span>
                      <div>
                        <div className="natal-chip__label">Асцендент</div>
                        <div className="natal-chip__value">{toRu(summary.ascendant_sign)}</div>
                      </div>
                    </div>
                  )}
                </div>
                {summary?.birth_city && (
                  <div className="natal-location">
                    <span className="natal-location__symbol">◎</span>
                    <div>
                      <div className="natal-location__city">{summary.birth_city}</div>
                      {summary?.birth_lat != null && summary?.birth_lng != null && (
                        <div className="natal-location__coords">
                          {summary.birth_lat.toFixed(2)}° {summary.birth_lat >= 0 ? 'с.ш.' : 'ю.ш.'}
                          {'  '}{summary.birth_lng.toFixed(2)}° {summary.birth_lng >= 0 ? 'в.д.' : 'з.д.'}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </motion.div>
              </>
            )}

            {/* Full natal — premium */}
            <PremiumGate
              locked={false}
              productId="natal_full"
              productName="Полная натальная карта"
              stars={150}
            >
              <motion.div
                className="natal-card natal-card--full"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <div className="natal-card__tag">✦ Полная карта</div>
                {fullLoading ? (
                  <div className="natal-loading">Вычисление планет...</div>
                ) : full ? (
                  <div className="planet-table">
                    {PLANET_ROWS.map((row) => {
                      const planet = full.planets?.[row.key]
                      const signText = planet
                        ? `${planet.sign_ru} ${Math.floor(planet.sign_degree)}°${planet.retrograde ? ' ℞' : ''} • Дом ${planet.house}`
                        : '—'
                      return (
                        <div key={row.key} className="planet-row">
                          <span className="planet-row__symbol">{row.label}</span>
                          <div>
                            <div className="planet-row__sign">{signText}</div>
                            <div className="planet-row__desc">{row.desc}</div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="natal-loading">Нет данных — добавьте дату рождения</div>
                )}

                {/* LLM Reading */}
                {full?.reading && (
                  <div className="natal-reading">
                    <div className="natal-card__tag" style={{ marginTop: '1.25rem' }}>✦ Персональная интерпретация</div>
                    <ReadingBlocks text={full.reading} />
                  </div>
                )}

                {/* Interpretations */}
                {full?.interpretations && full.interpretations.length > 0 && (
                  <div className="natal-interpretations">
                    <div className="natal-card__tag" style={{ marginTop: '1rem' }}>✦ Интерпретации</div>
                    {full.interpretations.map((interp, i) => (
                      <div key={i} className="natal-interp-item">
                        <div className="natal-interp-item__title">{interp.planet} · {interp.category}</div>
                        <p className="natal-interp-item__text">{interp.text}</p>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            </PremiumGate>
          </>
        )}
      </div>
    </div>
  )
}
