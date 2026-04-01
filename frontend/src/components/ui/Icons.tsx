import { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement> & { size?: number }

const defaults = (size = 24): SVGProps<SVGSVGElement> => ({
  width: size, height: size,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.5,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
})

// ── Navigation Icons ──────────────────────────────────────────────────────────

export function IconHome({ size, ...p }: IconProps) {
  return (
    <svg {...defaults(size)} {...p}>
      <path d="M3 10.5L12 3l9 7.5V21a1 1 0 01-1 1H4a1 1 0 01-1-1V10.5z" />
      <path d="M9 22V12h6v10" />
    </svg>
  )
}

export function IconTarot({ size, ...p }: IconProps) {
  return (
    <svg {...defaults(size)} {...p}>
      <rect x="4" y="2" width="16" height="20" rx="2" />
      <path d="M12 7v4M10 9h4" />
      <circle cx="12" cy="16" r="2" />
      <path d="M9 6l6 12M15 6l-6 12" strokeWidth="0.8" opacity="0.4" />
    </svg>
  )
}

export function IconCompat({ size, ...p }: IconProps) {
  return (
    <svg {...defaults(size)} {...p}>
      <circle cx="8.5" cy="10" r="4" />
      <circle cx="15.5" cy="10" r="4" />
      <path d="M12 18c-2-1.5-5-3-7-3M12 18c2-1.5 5-3 7-3" />
    </svg>
  )
}

export function IconMoon({ size, ...p }: IconProps) {
  return (
    <svg {...defaults(size)} {...p}>
      <path d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z" />
    </svg>
  )
}

export function IconNatal({ size, ...p }: IconProps) {
  return (
    <svg {...defaults(size)} {...p}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
      <path d="M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" strokeWidth="1" />
    </svg>
  )
}

export function IconMirror({ size, ...p }: IconProps) {
  return (
    <svg {...defaults(size)} {...p}>
      <circle cx="12" cy="10" r="7" />
      <path d="M12 17v5M9 20h6" />
      <path d="M9.5 8a3 3 0 014 0" strokeWidth="1.2" />
      <circle cx="12" cy="11" r="1" fill="currentColor" stroke="none" />
    </svg>
  )
}

// ── Zodiac Signs ──────────────────────────────────────────────────────────────

export function ZodiacAries({ size = 28, ...p }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {...p}>
      <path d="M16 28V8M16 8c0-3-2.5-5-5-5S6 5 6 8s3 6 5 8M16 8c0-3 2.5-5 5-5s5 2 5 5-3 6-5 8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function ZodiacTaurus({ size = 28, ...p }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {...p}>
      <circle cx="16" cy="20" r="8" stroke="currentColor" strokeWidth="1.8" />
      <path d="M7 6c2 4 5 6 9 6s7-2 9-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function ZodiacGemini({ size = 28, ...p }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {...p}>
      <path d="M6 5c3 2 7 3 10 3s7-1 10-3M6 27c3-2 7-3 10-3s7 1 10 3M11 8v16M21 8v16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function ZodiacCancer({ size = 28, ...p }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {...p}>
      <path d="M6 14a10 10 0 0120 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M26 18a10 10 0 01-20 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="10" cy="14" r="3" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="22" cy="18" r="3" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  )
}

export function ZodiacLeo({ size = 28, ...p }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {...p}>
      <circle cx="12" cy="20" r="5" stroke="currentColor" strokeWidth="1.8" />
      <path d="M17 20c0-6 3-10 6-12s3 4 1 6-4 4-4 8c0 3 2 5 5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function ZodiacVirgo({ size = 28, ...p }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {...p}>
      <path d="M6 8v16M6 8c0 8 5 8 5 16M11 8c0 8 5 8 5 16M16 8c0 8 5 8 5 16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M21 20c2 0 4 1 5 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function ZodiacLibra({ size = 28, ...p }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {...p}>
      <path d="M6 24h20M6 18h20" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M16 18V8M10 14a6 6 0 0112 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function ZodiacScorpio({ size = 28, ...p }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {...p}>
      <path d="M6 8v16M6 8c0 8 5 8 5 16M11 8c0 8 5 8 5 16M16 8c0 8 5 8 5 16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M21 24l25 20 21 24" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function ZodiacSagittarius({ size = 28, ...p }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {...p}>
      <path d="M6 26L26 6M26 6h-8M26 6v8M10 18l4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function ZodiacCapricorn({ size = 28, ...p }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {...p}>
      <path d="M6 8v12c0 4 3 6 6 6s5-2 5-5V8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M17 16c3 0 6 2 6 6a4 4 0 01-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function ZodiacAquarius({ size = 28, ...p }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {...p}>
      <path d="M4 12l4-4 4 4 4-4 4 4 4-4 4 4M4 20l4-4 4 4 4-4 4 4 4-4 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function ZodiacPisces({ size = 28, ...p }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" {...p}>
      <path d="M10 4c-4 4-4 10-4 12s0 8 4 12M22 4c4 4 4 10 4 12s0 8-4 12M6 16h20" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

// ── Zodiac Map ────────────────────────────────────────────────────────────────

export const ZODIAC_ICONS: Record<string, (p: IconProps) => JSX.Element> = {
  aries: ZodiacAries,
  taurus: ZodiacTaurus,
  gemini: ZodiacGemini,
  cancer: ZodiacCancer,
  leo: ZodiacLeo,
  virgo: ZodiacVirgo,
  libra: ZodiacLibra,
  scorpio: ZodiacScorpio,
  sagittarius: ZodiacSagittarius,
  capricorn: ZodiacCapricorn,
  aquarius: ZodiacAquarius,
  pisces: ZodiacPisces,
}

// ── UI Icons ──────────────────────────────────────────────────────────────────

export function IconStar({ size, ...p }: IconProps) {
  return (
    <svg {...defaults(size)} {...p}>
      <path d="M12 2l2.9 5.9L21 9l-4.5 4.4 1 6.6L12 17l-5.5 3 1-6.6L3 9l6.1-1.1L12 2z" fill="currentColor" stroke="none" />
    </svg>
  )
}

export function IconSparkle({ size = 16, ...p }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" {...p}>
      <path d="M8 0l1.5 5.5L16 8l-6.5 2.5L8 16l-1.5-5.5L0 8l6.5-2.5z" />
    </svg>
  )
}

export function IconCards({ size, ...p }: IconProps) {
  return (
    <svg {...defaults(size)} {...p}>
      <rect x="3" y="4" width="12" height="16" rx="2" />
      <rect x="7" y="2" width="12" height="16" rx="2" />
      <path d="M13 8v4M11 10h4" strokeWidth="1.2" />
    </svg>
  )
}

export function IconHeart({ size, ...p }: IconProps) {
  return (
    <svg {...defaults(size)} {...p}>
      <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" />
    </svg>
  )
}

export function IconCalendar({ size, ...p }: IconProps) {
  return (
    <svg {...defaults(size)} {...p}>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M3 10h18M8 2v4M16 2v4" />
      <circle cx="12" cy="16" r="1.5" fill="currentColor" stroke="none" />
    </svg>
  )
}

export function IconChart({ size, ...p }: IconProps) {
  return (
    <svg {...defaults(size)} {...p}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="4" strokeWidth="1" />
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4" strokeWidth="1" />
    </svg>
  )
}

export function IconEye({ size, ...p }: IconProps) {
  return (
    <svg {...defaults(size)} {...p}>
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}
