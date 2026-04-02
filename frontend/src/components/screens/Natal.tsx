import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { PremiumGate } from '@/components/ui/PremiumGate'
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
  const { user } = useAppStore()
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
            className="natal-setup-prompt"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="natal-setup-prompt__icon">🌌</div>
            <h3>Добавьте данные рождения</h3>
            <p>Для расчёта натальной карты нужны дата, время и город рождения</p>
            <button className="btn-primary">Указать данные</button>
          </motion.div>
        ) : (
          <>
            {/* Basic (free) — sun/moon/ascendant */}
            <motion.div
              className="natal-card natal-card--basic"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="natal-card__tag">✦ Базовый портрет</div>
              {summaryLoading ? (
                <div className="natal-loading">Вычисление...</div>
              ) : (
                <>
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
                </>
              )}
            </motion.div>

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
