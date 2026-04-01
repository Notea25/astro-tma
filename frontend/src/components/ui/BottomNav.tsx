import { motion } from 'framer-motion'
import type { Screen } from '@/stores/app'
import { useAppStore } from '@/stores/app'
import { useHaptic } from '@/hooks/useTelegram'
import { IconHome, IconTarot, IconCompat, IconMoon, IconNatal, IconMirror } from './Icons'

interface NavItem { id: Screen; label: string; Icon: (p: { size?: number }) => JSX.Element }

const NAV_ITEMS: NavItem[] = [
  { id: 'home',          label: 'Главная',  Icon: IconHome },
  { id: 'tarot',         label: 'Таро',     Icon: IconTarot },
  { id: 'compatibility', label: 'Союзы',    Icon: IconCompat },
  { id: 'moon',          label: 'Луна',     Icon: IconMoon },
  { id: 'natal',         label: 'Карта',    Icon: IconNatal },
  { id: 'mac',           label: 'Зеркало',  Icon: IconMirror },
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
            <span className="nav-icon"><item.Icon size={22} /></span>
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
