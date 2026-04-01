import { useEffect, useState } from 'react'
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

function SplashScreen() {
  return (
    <motion.div
      className="splash-screen"
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
    >
      <motion.div
        className="splash-content"
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
      >
        <div className="splash-icon">&#9734;</div>
        <h1 className="splash-title">Astro</h1>
        <p className="splash-subtitle">Ваш персональный астролог</p>
        <motion.div
          className="splash-dots"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.2, repeat: Infinity }}
        >
          <span /><span /><span />
        </motion.div>
      </motion.div>
    </motion.div>
  )
}

export default function App() {
  const { screen, setScreen, onboardingComplete, setUser } = useAppStore()
  const [ready, setReady] = useState(false)
  useTelegramReady()

  const syncUser = useMutation({
    mutationFn: usersApi.upsertMe,
    onSuccess: (user) => {
      setUser(user)
      if (onboardingComplete) {
        setScreen('home')
      }
    },
  })

  useEffect(() => {
    syncUser.mutate()
    const timer = setTimeout(() => setReady(true), 2500)
    return () => clearTimeout(timer)
  }, [])

  // Show splash while syncing user (only for returning users)
  if (!ready && onboardingComplete) {
    return (
      <div className="app">
        <AnimatePresence mode="wait">
          <SplashScreen />
        </AnimatePresence>
      </div>
    )
  }

  // New users go straight to onboarding (no splash)
  if (!ready && !onboardingComplete) {
    return (
      <div className="app">
        <AnimatePresence mode="wait">
          <SplashScreen />
        </AnimatePresence>
      </div>
    )
  }

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
