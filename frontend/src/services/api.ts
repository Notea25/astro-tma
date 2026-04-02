/**
 * API client — thin wrapper over fetch.
 * Automatically injects X-Init-Data header (Telegram auth).
 * All methods throw on non-2xx — React Query catches them.
 */

import WebApp from '@twa-dev/sdk'

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Init-Data': WebApp.initData || '',  // Telegram auth token
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new ApiError(response.status, detail.detail ?? response.statusText)
  }

  return response.json() as Promise<T>
}

// ── Users ──────────────────────────────────────────────────────────────────────
export const usersApi = {
  upsertMe: () => request<import('@/types').UserProfile>('POST', '/users/me'),
  setGender: (gender: string) =>
    request<import('@/types').UserProfile>('POST', '/users/me/gender', { gender }),
  setupBirth: (data: {
    birth_date: string
    birth_time_known: boolean
    birth_city: string
    lat?: number
    lng?: number
  }) => request('POST', '/users/me/birth', data),
}

// ── Horoscope ──────────────────────────────────────────────────────────────────
export const horoscopeApi = {
  getToday: () => request<import('@/types').HoroscopeResponse>('GET', '/horoscope/today'),
  getPeriod: (period: string) =>
    request<import('@/types').HoroscopeResponse>('GET', `/horoscope/period?period=${period}`),
  getMoon: () => request<import('@/types').MoonPhaseResponse>('GET', '/horoscope/moon'),
  getMoonCalendar: (year: number, month: number) =>
    request<{ year: number; month: number; days: import('@/types').MoonCalendarDay[] }>('GET',
      `/horoscope/moon/calendar?year=${year}&month=${month}`),
}

// ── Natal ──────────────────────────────────────────────────────────────────────
export const natalApi = {
  getSummary: () => request<import('@/types').NatalSummaryResponse>('GET', '/natal/summary'),
  getFull: () => request<import('@/types').NatalFullResponse>('GET', '/natal/full'),
}

// ── Tarot ──────────────────────────────────────────────────────────────────────
export const tarotApi = {
  draw: (spread_type: string) =>
    request<import('@/types').TarotSpreadResponse>('POST', '/tarot/draw', { spread_type }),
}

// ── Compatibility ──────────────────────────────────────────────────────────────
export const compatibilityApi = {
  get: (sign_a: string, sign_b: string) =>
    request<import('@/types').CompatibilityResponse>('POST', '/compatibility', { sign_a, sign_b }),
}

// ── Payments ───────────────────────────────────────────────────────────────────
export const macApi = {
  draw: () => request<import('@/types').MacReadingResponse>('POST', '/mac/draw'),
}

export const paymentsApi = {
  getProducts: () => request<import('@/types').ProductInfo[]>('GET', '/payments/products'),
  createInvoice: (product_id: string) =>
    request<{ invoice_url: string; product_id: string; stars_amount: number }>(
      'POST', '/payments/invoice', { product_id }
    ),
}

export { ApiError }
