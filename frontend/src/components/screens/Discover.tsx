import { motion } from 'framer-motion'
import { useAppStore } from '@/stores/app'
import { useHaptic } from '@/hooks/useTelegram'

interface DiscoverCard {
  label: string
  desc: string
  icon: JSX.Element
  screen?: string
  locked?: boolean
  accentColor?: string
}

function DiscoverItem({ item, index, onClick }: { item: DiscoverCard; index: number; onClick: () => void }) {
  return (
    <motion.button
      className={`discover-card${item.locked ? ' discover-card--locked' : ''}`}
      onClick={onClick}
      whileTap={{ scale: 0.96 }}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      style={item.accentColor ? { '--card-accent': item.accentColor } as any : undefined}
    >
      <span className="discover-card__icon">{item.icon}</span>
      <span className="discover-card__label">{item.label}</span>
      <span className="discover-card__desc">{item.desc}</span>
      {item.locked && <span className="discover-card__lock">✦</span>}
    </motion.button>
  )
}

export function Discover() {
  const { setScreen } = useAppStore()
  const { impact } = useHaptic()

  const navigate = (screen: string) => {
    impact('light')
    setScreen(screen as any)
  }

  const sections: { title: string; cards: DiscoverCard[] }[] = [
    {
      title: 'Карты',
      cards: [
        {
          label: 'Таро',
          desc: 'Расклады и предсказания',
          screen: 'tarot',
          accentColor: '#c9a84c',
          icon: (
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round">
              <rect x="4" y="1" width="10" height="14" rx="1.5"/>
              <rect x="8" y="7" width="10" height="14" rx="1.5"/>
              <line x1="7" y1="5" x2="11" y2="5"/>
              <line x1="7" y1="8" x2="11" y2="8"/>
            </svg>
          ),
        },
        {
          label: 'МАК-карты',
          desc: 'Метафорические карты',
          screen: 'mac',
          accentColor: '#a07de8',
          icon: (
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="2" width="18" height="18" rx="3"/>
              <circle cx="11" cy="11" r="5"/>
              <circle cx="11" cy="11" r="2"/>
            </svg>
          ),
        },
      ],
    },
    {
      title: 'Отношения',
      cards: [
        {
          label: 'Совместимость',
          desc: 'Астрологический союз',
          screen: 'compatibility',
          accentColor: '#c5b8f0',
          icon: (
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="7.5" cy="11" r="5.5"/>
              <circle cx="14.5" cy="11" r="5.5"/>
            </svg>
          ),
        },
        {
          label: 'Синастрия',
          desc: 'Карта отношений',
          locked: true,
          accentColor: '#e8c97e',
          icon: (
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 19.5C11 19.5 2.5 14 2.5 8a4.5 4.5 0 019 0 4.5 4.5 0 019 0c0 6-8.5 11.5-8.5 11.5z"/>
            </svg>
          ),
        },
      ],
    },
    {
      title: 'Луна и циклы',
      cards: [
        {
          label: 'Лунный календарь',
          desc: 'Фазы и ритмы',
          screen: 'moon',
          accentColor: '#c5b8f0',
          icon: (
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 13.5A8 8 0 018.5 4 8 8 0 1018 13.5z"/>
            </svg>
          ),
        },
        {
          label: 'Транзиты',
          desc: 'Планеты сейчас',
          locked: true,
          accentColor: '#9e9ab5',
          icon: (
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="4" width="18" height="15" rx="2"/>
              <line x1="7" y1="2" x2="7" y2="6"/>
              <line x1="15" y1="2" x2="15" y2="6"/>
              <line x1="2" y1="10" x2="20" y2="10"/>
            </svg>
          ),
        },
      ],
    },
    {
      title: 'Знания',
      cards: [
        {
          label: 'Астро-новости',
          desc: 'События и прогнозы',
          locked: true,
          accentColor: '#8bc89b',
          icon: (
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 4h14a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2z"/>
              <line x1="6" y1="9" x2="16" y2="9"/>
              <line x1="6" y1="13" x2="12" y2="13"/>
            </svg>
          ),
        },
        {
          label: 'Глоссарий',
          desc: 'Термины астрологии',
          locked: true,
          accentColor: '#7ec8e3',
          icon: (
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19V5a2 2 0 012-2h12v14H6a2 2 0 000 4h12"/>
              <line x1="8" y1="7" x2="14" y2="7"/>
              <line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
          ),
        },
      ],
    },
  ]

  let cardIndex = 0

  return (
    <div className="screen discover-screen">
      <div className="screen-header">
        <h2 className="screen-title">Открыть</h2>
      </div>

      <div className="screen-content">
        {sections.map((section) => (
          <div key={section.title} className="discover-section">
            <h3 className="discover-section__title">{section.title}</h3>
            <div className="discover-grid">
              {section.cards.map((card) => {
                const idx = cardIndex++
                return (
                  <DiscoverItem
                    key={card.label}
                    item={card}
                    index={idx}
                    onClick={() => card.screen && !card.locked ? navigate(card.screen) : impact('light')}
                  />
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
