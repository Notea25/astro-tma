import { motion } from 'framer-motion'
import type { Screen } from '@/stores/app'
import { useAppStore } from '@/stores/app'
import { useHaptic } from '@/hooks/useTelegram'

interface NavItem { id: Screen; label: string; icon: string }

const NAV_ITEMS: NavItem[] = [
  { id: 'home',          label: 'Главная',  icon: '🏠' },
  { id: 'tarot',         label: 'Таро',     icon: '🃏' },
  { id: 'compatibility', label: 'Союзы',    icon: '💫' },
  { id: 'moon',          label: 'Луна',     icon: '🌙' },
  { id: 'natal',         label: 'Карта',    icon: '⭕' },
  { id: 'mac',           label: 'Зеркало',  icon: '🔮' },
  { id: 'profile',      label: 'Профиль',  icon: '👤' },
]

export function BottomNav() {
  const { screen, setScreen } = useAppStore()
  const { selection } = useHaptic()

  const handleNav = (id: Screen) => {
    if (id === screen) return
    selection()
    setScreen(id)
  }

  return (
    <nav className="bottom-nav">
      {NAV_ITEMS.map((item) => {
        const active = screen === item.id
        return (
          <button
            key={item.id}
            className={`nav-item ${active ? 'active' : ''}`}
            onClick={() => handleNav(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
            {active && (
              <motion.div
                className="nav-indicator"
                layoutId="nav-indicator"
                transition={{ type: 'spring', stiffness: 500, damping: 40 }}
              />
            )}
          </button>
        )
      })}
    </nav>
  )
}
