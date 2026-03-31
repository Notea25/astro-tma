import { motion } from 'framer-motion'
import { PremiumGate } from '@/components/ui/PremiumGate'
import { useAppStore } from '@/stores/app'
import { ZODIAC_SIGNS } from '@/types'

const PLANET_ROWS = [
  { key: 'sun',     label: '☉ Солнце',    desc: 'Ядро личности, творческая сила' },
  { key: 'moon',    label: '☽ Луна',      desc: 'Эмоции, интуиция, подсознание' },
  { key: 'mercury', label: '☿ Меркурий',  desc: 'Мышление, коммуникация' },
  { key: 'venus',   label: '♀ Венера',    desc: 'Любовь, ценности, красота' },
  { key: 'mars',    label: '♂ Марс',      desc: 'Энергия, действие, желание' },
  { key: 'jupiter', label: '♃ Юпитер',   desc: 'Удача, рост, философия' },
  { key: 'saturn',  label: '♄ Сатурн',   desc: 'Дисциплина, уроки, структура' },
]

export function Natal() {
  const { user } = useAppStore()
  const hasBirthData = !!user?.birth_city
  const isPremium = user?.is_premium

  const userSign = ZODIAC_SIGNS.find(s => s.value === user?.sun_sign)

  return (
    <div className="screen natal-screen">
      <div className="screen-header">
        <h2 className="screen-title">⭕ Натальная карта</h2>
        <p className="screen-subtitle">Ваш космический портрет</p>
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
            <button className="btn-primary" onClick={() => {/* TODO: open birth data edit */}}>
              Указать данные
            </button>
          </motion.div>
        ) : (
          <>
            {/* Basic (free) — sun sign info */}
            <motion.div
              className="natal-card natal-card--basic"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="natal-card__tag">✦ Базовый портрет</div>
              <div className="natal-sign-row">
                <span className="natal-sign-emoji">{userSign?.emoji}</span>
                <div>
                  <div className="natal-sign-name">{userSign?.label}</div>
                  <div className="natal-sign-dates">{userSign?.dates}</div>
                </div>
              </div>
              <p className="natal-card__text">
                Ваш солнечный знак определяет ядро вашей личности —
                то, как вы проявляете себя в мире и к чему стремитесь.
              </p>
            </motion.div>

            {/* Full natal — premium */}
            <PremiumGate
              locked={!isPremium}
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
                <div className="planet-table">
                  {PLANET_ROWS.map((row) => (
                    <div key={row.key} className="planet-row">
                      <span className="planet-row__symbol">{row.label}</span>
                      <div>
                        <div className="planet-row__sign">— Загрузка...</div>
                        <div className="planet-row__desc">{row.desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            </PremiumGate>
          </>
        )}
      </div>
    </div>
  )
}
