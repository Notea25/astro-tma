/**
 * Global app state — Zustand store.
 * Only truly global, cross-screen state lives here.
 * Server state (horoscope data, tarot readings) stays in React Query.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserProfile, ZodiacSign } from '@/types'

export type Screen = 'onboarding' | 'home' | 'tarot' | 'compatibility' | 'moon' | 'natal'

interface AppState {
  screen: Screen
  setScreen: (s: Screen) => void

  user: UserProfile | null
  setUser: (u: UserProfile) => void
  clearUser: () => void

  onboardingComplete: boolean
  setOnboardingComplete: (v: boolean) => void

  compatSignA: ZodiacSign | null
  compatSignB: ZodiacSign | null
  setCompatSign: (slot: 'a' | 'b', sign: ZodiacSign) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      screen: 'onboarding',
      setScreen: (screen) => set({ screen }),

      user: null,
      setUser: (user) => set({ user }),
      clearUser: () => set({ user: null }),

      onboardingComplete: false,
      setOnboardingComplete: (v) => set({ onboardingComplete: v }),

      compatSignA: null,
      compatSignB: null,
      setCompatSign: (slot, sign) =>
        set(slot === 'a' ? { compatSignA: sign } : { compatSignB: sign }),
    }),
    {
      name: 'astro-app-v1',
      partialize: (state) => ({
        onboardingComplete: state.onboardingComplete,
        compatSignA: state.compatSignA,
        compatSignB: state.compatSignB,
      }),
    }
  )
)
