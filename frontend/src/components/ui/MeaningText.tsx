import { SVGProps, useMemo } from 'react'

/* ── Inline SVG icons for meaning sections (celestial / astro style) ────── */

const iconProps: SVGProps<SVGSVGElement> = {
  width: 16, height: 16, viewBox: '0 0 24 24',
  fill: 'none', stroke: 'currentColor', strokeWidth: 1.4,
  strokeLinecap: 'round', strokeLinejoin: 'round',
}

function IconLove() {
  return (
    <svg {...iconProps}>
      <path d="M12 21C12 21 3 13.5 3 8.5a4.5 4.5 0 0 1 9 0 4.5 4.5 0 0 1 9 0C21 13.5 12 21 12 21z" strokeWidth="1.3" />
      <circle cx="8" cy="9" r="1" fill="currentColor" stroke="none" opacity="0.3" />
      <circle cx="16" cy="9" r="1" fill="currentColor" stroke="none" opacity="0.3" />
    </svg>
  )
}

function IconCareer() {
  return (
    <svg {...iconProps}>
      <path d="M2 17l10-10 10 10" strokeWidth="1.0" opacity="0.25" />
      <circle cx="12" cy="12" r="9" />
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
      <path d="M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8" strokeWidth="1.0" />
    </svg>
  )
}

function IconHealth() {
  return (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v8M8 12h8" strokeWidth="1.6" />
      <circle cx="12" cy="12" r="4" strokeWidth="0.8" opacity="0.35" />
    </svg>
  )
}

function IconSpirit() {
  return (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="3" />
      <circle cx="12" cy="12" r="9" strokeWidth="1.0" />
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3" strokeWidth="1.0" />
      <path d="M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" strokeWidth="0.8" opacity="0.5" />
    </svg>
  )
}

function IconAdvice() {
  return (
    <svg {...iconProps}>
      <path d="M12 2l2.4 4.8 5.3.8-3.85 3.7.9 5.3L12 14.3 7.25 16.6l.9-5.3L4.3 7.6l5.3-.8L12 2z" />
    </svg>
  )
}

/* ── Emoji → icon mapping ─────────────────────────────────────────────────── */

const EMOJI_MAP: Record<string, { icon: () => JSX.Element; label: string }> = {
  '💕': { icon: IconLove,   label: 'Любовь' },
  '❤️': { icon: IconLove,   label: 'Любовь' },
  '💼': { icon: IconCareer, label: 'Карьера' },
  '🩺': { icon: IconHealth, label: 'Здоровье' },
  '🔮': { icon: IconSpirit, label: 'Духовность' },
  '✨': { icon: IconAdvice, label: 'Совет дня' },
}

// Match emoji at start of line, followed by label and colon
const SECTION_RE = /^(💕|❤️|💼|🩺|🔮|✨)\s*[^:]*:\s*/

interface MeaningSection {
  type: 'intro' | 'topic' | 'advice'
  icon?: () => JSX.Element
  label?: string
  text: string
}

function parseMeaning(raw: string): MeaningSection[] {
  const sections: MeaningSection[] = []
  // Split on double newlines for main paragraphs, then process lines
  const blocks = raw.split(/\n\n+/)

  for (const block of blocks) {
    const lines = block.split('\n')

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue

      const match = trimmed.match(SECTION_RE)
      if (match) {
        const emoji = match[1]
        const entry = EMOJI_MAP[emoji]
        const text = trimmed.replace(SECTION_RE, '').trim()
        if (entry && text) {
          sections.push({
            type: entry.label === 'Совет дня' ? 'advice' : 'topic',
            icon: entry.icon,
            label: entry.label,
            text,
          })
        }
      } else {
        // Regular paragraph — check if it's continuation of intro or standalone
        // Strip any remaining emojis that aren't in our map
        const cleaned = trimmed.replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{27BF}\u{FE00}-\u{FEFF}]/gu, '').trim()
        if (cleaned) {
          sections.push({ type: 'intro', text: cleaned })
        }
      }
    }
  }

  return sections
}

/* ── Component ─────────────────────────────────────────────────────────────── */

interface Props {
  text: string
  compact?: boolean  // For card-of-the-day (clamped lines)
}

export function MeaningText({ text, compact }: Props) {
  const sections = useMemo(() => parseMeaning(text), [text])

  if (compact) {
    // Compact mode: just show intro paragraphs, skip emoji sections
    const intros = sections.filter(s => s.type === 'intro')
    return (
      <div className="meaning-styled meaning-styled--compact">
        {intros.map((s, i) => (
          <p key={i} className="meaning-styled__intro">{s.text}</p>
        ))}
      </div>
    )
  }

  return (
    <div className="meaning-styled">
      {sections.map((s, i) => {
        if (s.type === 'intro') {
          return <p key={i} className="meaning-styled__intro">{s.text}</p>
        }
        if (s.type === 'advice') {
          return (
            <div key={i} className="meaning-styled__advice">
              {s.icon && (
                <span className="meaning-styled__icon meaning-styled__icon--advice">
                  <s.icon />
                </span>
              )}
              <div>
                <span className="meaning-styled__label">{s.label}</span>
                <p className="meaning-styled__body">{s.text}</p>
              </div>
            </div>
          )
        }
        // topic
        return (
          <div key={i} className="meaning-styled__topic">
            {s.icon && (
              <span className="meaning-styled__icon">
                <s.icon />
              </span>
            )}
            <div>
              <span className="meaning-styled__label">{s.label}</span>
              <p className="meaning-styled__body">{s.text}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
