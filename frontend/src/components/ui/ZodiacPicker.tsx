import { motion } from 'framer-motion'
import type { ZodiacSign } from '@/types'
import { ZODIAC_SIGNS } from '@/types'
import { useHaptic } from '@/hooks/useTelegram'

interface ZodiacPickerProps {
  value: ZodiacSign | null
  onChange: (sign: ZodiacSign) => void
  label?: string
}

export function ZodiacPicker({ value, onChange, label }: ZodiacPickerProps) {
  const { selection } = useHaptic()

  const handleSelect = (sign: ZodiacSign) => {
    selection()
    onChange(sign)
  }

  return (
    <div className="zodiac-picker">
      {label && <div className="form-label">{label}</div>}
      <div className="zodiac-grid">
        {ZODIAC_SIGNS.map((s) => {
          const selected = value === s.value
          return (
            <motion.button
              key={s.value}
              className={`zodiac-btn ${selected ? 'selected' : ''}`}
              onClick={() => handleSelect(s.value)}
              whileTap={{ scale: 0.92 }}
            >
              <span className="zodiac-btn__emoji">{s.emoji}</span>
              <span className="zodiac-btn__name">{s.label}</span>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
