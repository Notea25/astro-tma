/**
 * Telegram WebApp SDK hooks.
 * Centralises all WebApp interactions — components never import SDK directly.
 */

import { useEffect, useCallback } from 'react'
import WebApp from '@twa-dev/sdk'

export function useTelegramUser() {
  const user = WebApp.initDataUnsafe?.user
  return {
    id: user?.id ?? 0,
    firstName: user?.first_name ?? '',
    lastName: user?.last_name,
    username: user?.username,
    isPremium: user?.is_premium ?? false,
    photoUrl: user?.photo_url,
    languageCode: user?.language_code ?? 'ru',
  }
}

export function useTelegramTheme() {
  return {
    colorScheme: WebApp.colorScheme,           // 'light' | 'dark'
    bgColor: WebApp.backgroundColor,
    themeParams: WebApp.themeParams,
  }
}

export function useTelegramBackButton(onBack: () => void, enabled = true) {
  useEffect(() => {
    if (!enabled) {
      WebApp.BackButton.hide()
      return
    }
    WebApp.BackButton.show()
    WebApp.BackButton.onClick(onBack)
    return () => {
      WebApp.BackButton.offClick(onBack)
      WebApp.BackButton.hide()
    }
  }, [onBack, enabled])
}

export function useHaptic() {
  return {
    impact: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft' = 'light') =>
      WebApp.HapticFeedback.impactOccurred(style),
    notification: (type: 'error' | 'success' | 'warning') =>
      WebApp.HapticFeedback.notificationOccurred(type),
    selection: () => WebApp.HapticFeedback.selectionChanged(),
  }
}

export function useStarsPayment() {
  const { impact, notification } = useHaptic()

  const pay = useCallback(async (invoiceUrl: string): Promise<boolean> => {
    return new Promise((resolve) => {
      impact('medium')
      WebApp.openInvoice(invoiceUrl, (status) => {
        if (status === 'paid') {
          notification('success')
          resolve(true)
        } else {
          // 'cancelled' | 'failed' | 'pending'
          notification(status === 'cancelled' ? 'warning' : 'error')
          resolve(false)
        }
      })
    })
  }, [impact, notification])

  return { pay }
}

export function useTelegramReady() {
  useEffect(() => {
    WebApp.ready()
    WebApp.expand()
  }, [])
}
