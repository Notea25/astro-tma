import { useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { Onboarding }    from '@/components/screens/Onboarding'
import { Home }          from '@/components/screens/Home'
import { Tarot }         from '@/components/screens/Tarot'
import { Compatibility } from '@/components/screens/Compatibility'
import { Moon }          from '@/components/screens/Moon'
import { Natal }         from '@/components/screens/Natal'
import { Mac }           from '@/components/screens/Mac'
import { Profile }       from '@/components/screens/Profile'
import { BottomNav }     from '@/components/ui/BottomNav'
import { usersApi }      from '@/services/api'
import { useAppStore }   from '@/stores/app'
import { useTelegramReady } from '@/hooks/useTelegram'

export default function App() {
  const { screen, setScreen, onboardingComplete, setUser } = useAppStore()
  useTelegramReady()

  // Sync user on every app open
  const syncUser = useMutation({
    mutationFn: usersApi.upsertMe,
    onSuccess: (user) => {
      setUser(user)
      if (onboardingComplete && screen === 'onboarding') {
        setScreen('home')
      }
    },
  })

  useEffect(() => {
    syncUser.mutate()
  }, [])

  const showNav = screen !== 'onboarding'

  return (
    <div className="app">
      <AnimatePresence mode="wait">
        <motion.div
          key={screen}
          className="screen-container"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.22, ease: 'easeInOut' }}
        >
          {screen === 'onboarding'    && <Onboarding />}
          {screen === 'home'          && <Home />}
          {screen === 'tarot'         && <Tarot />}
          {screen === 'compatibility' && <Compatibility />}
          {screen === 'moon'          && <Moon />}
          {screen === 'natal'         && <Natal />}
          {screen === 'mac'           && <Mac />}
          {screen === 'profile'       && <Profile />}
        </motion.div>
      </AnimatePresence>

      {showNav && <BottomNav />}
    </div>
  )
}
