import { motion } from 'framer-motion'
import type { Screen } from '@/stores/app'
import { useAppStore } from '@/stores/app'
import { useHaptic } from '@/hooks/useTelegram'

// Which tab should be "active" for a given screen
const SCREEN_TO_TAB: Partial<Record<Screen, string>> = {
  home:          'home',
  discover:      'discover',
  tarot:         'discover',
  compatibility: 'discover',
  moon:          'discover',
  mac:           'discover',
  natal:         'natal',
  profile:       'profile',
}

const NAV_ITEMS = [
  {
    id: 'home' as Screen,
    label: 'Сегодня',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="10" cy="10" r="4"/>
        <line x1="10" y1="1" x2="10" y2="3"/>
        <line x1="10" y1="17" x2="10" y2="19"/>
        <line x1="1" y1="10" x2="3" y2="10"/>
        <line x1="17" y1="10" x2="19" y2="10"/>
        <line x1="3.22" y1="3.22" x2="4.64" y2="4.64"/>
        <line x1="15.36" y1="15.36" x2="16.78" y2="16.78"/>
        <line x1="3.22" y1="16.78" x2="4.64" y2="15.36"/>
        <line x1="15.36" y1="4.64" x2="16.78" y2="3.22"/>
      </svg>
    ),
  },
  {
    id: 'discover' as Screen,
    label: 'Практики',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="10" cy="10" r="8.5"/>
        <polygon points="13.5,6.5 8,9 6.5,13.5 12,11"/>
        <circle cx="10" cy="10" r="1" fill="currentColor" stroke="none"/>
      </svg>
    ),
  },
  {
    id: 'natal' as Screen,
    label: 'Моя карта',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="10" cy="10" r="8.5"/>
        <circle cx="10" cy="10" r="5"/>
        <circle cx="10" cy="10" r="1.5"/>
        <line x1="10" y1="1.5" x2="10" y2="5"/>
        <line x1="10" y1="15" x2="10" y2="18.5"/>
        <line x1="1.5" y1="10" x2="5" y2="10"/>
        <line x1="15" y1="10" x2="18.5" y2="10"/>
      </svg>
    ),
  },
  {
    id: 'profile' as Screen,
    label: 'Профиль',
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="10" cy="7" r="3.5"/>
        <path d="M2.5 18c0-4.142 3.358-7 7.5-7s7.5 2.858 7.5 7"/>
      </svg>
    ),
  },
]

export function BottomNav() {
  const { screen, setScreen } = useAppStore()
  const { selection } = useHaptic()

  const activeTab = SCREEN_TO_TAB[screen] ?? 'home'

  const handleNav = (id: Screen) => {
    if (id === screen) return
    selection()
    setScreen(id)
  }

  return (
    <nav className="bottom-nav">
      {NAV_ITEMS.map((item) => {
        const active = activeTab === item.id
        return (
          <button
            key={item.id}
            className={`nav-item ${active ? 'active' : ''}`}
            onClick={() => handleNav(item.id)}
          >
            {active && (
              <motion.div
                className="nav-indicator"
                layoutId="nav-indicator"
                transition={{ type: 'spring', stiffness: 500, damping: 40 }}
              />
            )}
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
