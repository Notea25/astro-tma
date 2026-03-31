// ── API Response types (mirror backend Pydantic schemas) ──────────────────────

export interface UserProfile {
  id: number
  name: string
  sun_sign: string | null
  birth_city: string | null
  birth_time_known: boolean
  push_enabled: boolean
  is_premium: boolean
  created_at: string
}

export interface EnergyScores {
  love: number
  career: number
  health: number
  luck: number
}

export interface HoroscopeResponse {
  sign: string
  sign_ru: string
  date: string
  period: string
  text_ru: string
  energy: EnergyScores
  is_personalised: boolean
}

export interface MoonPhaseResponse {
  phase_name: string
  phase_name_ru: string
  emoji: string
  description_ru: string
  illumination: number
  date: string
}

export interface MoonCalendarDay {
  day: number
  phase_name: string
  phase_name_ru: string
  emoji: string
  illumination: number
}

export interface TarotCardDetail {
  id: number
  name_ru: string
  name_en: string
  emoji: string
  arcana: string
  reversed: boolean
  meaning_ru: string
  position_name_ru: string
  position_meaning_ru: string | null
  keywords_ru: string[]
}

export interface TarotSpreadResponse {
  reading_id: number
  spread_type: string
  cards: TarotCardDetail[]
  is_premium: boolean
}

export interface CompatibilityResponse {
  sign_a: string
  sign_b: string
  overall: number
  love: number
  communication: number
  trust: number
  passion: number
  tier: string
  description_ru: string
  strengths_ru: string[]
  challenges_ru: string[]
  is_deep_analysis: boolean
}

export interface ProductInfo {
  id: string
  name: string
  description: string
  stars: number
  type: string
}

export type ZodiacSign =
  | 'aries' | 'taurus' | 'gemini' | 'cancer'
  | 'leo' | 'virgo' | 'libra' | 'scorpio'
  | 'sagittarius' | 'capricorn' | 'aquarius' | 'pisces'

export const ZODIAC_SIGNS: { value: ZodiacSign; label: string; emoji: string; dates: string }[] = [
  { value: 'aries',       label: 'Овен',      emoji: '♈', dates: '21 мар — 19 апр' },
  { value: 'taurus',      label: 'Телец',     emoji: '♉', dates: '20 апр — 20 май' },
  { value: 'gemini',      label: 'Близнецы',  emoji: '♊', dates: '21 май — 20 июн' },
  { value: 'cancer',      label: 'Рак',       emoji: '♋', dates: '21 июн — 22 июл' },
  { value: 'leo',         label: 'Лев',       emoji: '♌', dates: '23 июл — 22 авг' },
  { value: 'virgo',       label: 'Дева',      emoji: '♍', dates: '23 авг — 22 сен' },
  { value: 'libra',       label: 'Весы',      emoji: '♎', dates: '23 сен — 22 окт' },
  { value: 'scorpio',     label: 'Скорпион',  emoji: '♏', dates: '23 окт — 21 ноя' },
  { value: 'sagittarius', label: 'Стрелец',   emoji: '♐', dates: '22 ноя — 21 дек' },
  { value: 'capricorn',   label: 'Козерог',   emoji: '♑', dates: '22 дек — 19 янв' },
  { value: 'aquarius',    label: 'Водолей',   emoji: '♒', dates: '20 янв — 18 фев' },
  { value: 'pisces',      label: 'Рыбы',      emoji: '♓', dates: '19 фев — 20 мар' },
]
