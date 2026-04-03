import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useHaptic } from '@/hooks/useTelegram'
import { MeaningText } from '@/components/ui/MeaningText'
import type { TarotCardDetail } from '@/types'

/* ── Layout maps ─────────────────────────────────────────────────────────── */

interface SlotDef {
  slot: number
  x: number
  y: number
  label: string
  rotate?: number
}

const LAYOUTS: Record<string, { slots: SlotDef[]; w: number; h: number }> = {
  relationship: {
    w: 240,
    h: 390,
    slots: [
      { slot: 1, x: 20,  y: 0,   label: 'Вы' },
      { slot: 2, x: 164, y: 0,   label: 'Партнёр' },
      { slot: 3, x: 92,  y: 100, label: 'Связь' },
      { slot: 4, x: 92,  y: 196, label: 'Вызов' },
      { slot: 5, x: 92,  y: 292, label: 'Потенциал' },
    ],
  },
  celtic_cross: {
    w: 340,
    h: 500,
    // Card=56x84. Cross center at x=100. Column at x=272.
    // Vertical gaps=96 (84+12). Horizontal gaps=68 (56+12).
    slots: [
      { slot: 1,  x: 100, y: 192, label: 'Ситуация' },
      { slot: 2,  x: 86,  y: 220, label: 'Препятствие', rotate: 90 },
      { slot: 3,  x: 100, y: 300, label: 'Корни' },
      { slot: 4,  x: 100, y: 84,  label: 'Прошлое влияние' },
      { slot: 5,  x: 20,  y: 192, label: 'Прошлое' },
      { slot: 6,  x: 180, y: 192, label: 'Будущее' },
      { slot: 7,  x: 272, y: 396, label: 'Вы' },
      { slot: 8,  x: 272, y: 300, label: 'Окружение' },
      { slot: 9,  x: 272, y: 192, label: 'Надежды' },
      { slot: 10, x: 272, y: 84,  label: 'Итог' },
    ],
  },
  week: {
    w: 310,
    h: 220,
    slots: [
      { slot: 1, x: 0,   y: 0,   label: 'Пн' },
      { slot: 2, x: 78,  y: 0,   label: 'Вт' },
      { slot: 3, x: 156, y: 0,   label: 'Ср' },
      { slot: 4, x: 234, y: 0,   label: 'Чт' },
      { slot: 5, x: 38,  y: 110, label: 'Пт' },
      { slot: 6, x: 116, y: 110, label: 'Сб' },
      { slot: 7, x: 194, y: 110, label: 'Вс' },
    ],
  },
}

const CARD_W = 56
const CARD_H = 84

/* ── Component ───────────────────────────────────────────────────────────── */

interface Props {
  spreadType: string
  cards: TarotCardDetail[]
}

export function SpreadLayout({ spreadType, cards }: Props) {
  const { impact } = useHaptic()
  const [flipped, setFlipped] = useState<Set<number>>(new Set())
  const [selected, setSelected] = useState<number | null>(null)
  const detailRef = useRef<HTMLDivElement>(null)

  const layout = LAYOUTS[spreadType]
  if (!layout) return null

  const handleFlip = (idx: number) => {
    if (flipped.has(idx)) {
      setSelected(idx)
      return
    }
    impact('medium')
    setFlipped(prev => new Set(prev).add(idx))
    setSelected(idx)
    setTimeout(() => {
      detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }, 400)
  }

  const selectedCard = selected !== null ? cards[selected] : null
  const selectedSlot = selected !== null ? layout.slots[selected] : null

  return (
    <div className="spread-layout">
      {/* ── Card map ── */}
      <div
        className="spread-container"
        style={{ width: layout.w, height: layout.h }}
      >
        {layout.slots.map((slot, idx) => {
          const card = cards[idx]
          if (!card) return null
          const isFlipped = flipped.has(idx)
          const isSelected = selected === idx
          const isCross = !!slot.rotate

          return (
            <motion.div
              key={slot.slot}
              className={`spread-slot${isCross ? ' spread-slot--cross' : ''}${isSelected ? ' spread-slot--selected' : ''}`}
              style={{
                left: slot.x,
                top: slot.y,
                width: isCross ? CARD_H : CARD_W,
                height: isCross ? CARD_W : CARD_H,
                zIndex: isCross ? 2 : undefined,
              }}
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.12, duration: 0.3 }}
              onClick={() => handleFlip(idx)}
            >
              <div className={`spread-slot__flipper${isFlipped ? ' is-flipped' : ''}${isCross ? ' spread-slot__flipper--cross' : ''}`}>
                {/* Back (face-down) */}
                <div className={`spread-slot__back${isCross ? ' spread-slot__back--cross' : ''}`}>
                  <span className="spread-slot__number">{slot.slot}</span>
                </div>
                {/* Front (face-up) */}
                <div className={`spread-slot__front${isCross ? ' spread-slot__front--cross' : ''}`}>
                  {card.image_url ? (
                    <img
                      src={card.image_url}
                      alt={card.name_ru}
                      className={`spread-slot__img${card.reversed ? ' spread-slot__img--reversed' : ''}`}
                    />
                  ) : (
                    <span className="spread-slot__emoji">{card.emoji}</span>
                  )}
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* ── Selected card detail ── */}
      <div ref={detailRef}>
        <AnimatePresence mode="wait">
          {selectedCard && selectedSlot && flipped.has(selected!) && (
            <motion.div
              key={selected}
              className="spread-detail"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
            >
              <div className="spread-detail__header">
                <span className="spread-detail__pos">{selectedSlot.slot}. {selectedSlot.label}</span>
                <span className={`spread-detail__orient${selectedCard.reversed ? ' rev' : ''}`}>
                  {selectedCard.reversed ? '↓ Перевёрнутая' : '↑ Прямая'}
                </span>
              </div>
              <h3 className="spread-detail__name">{selectedCard.name_ru}</h3>
              <p className="spread-detail__keys">{selectedCard.keywords_ru?.slice(0, 3).join(' · ')}</p>
              <MeaningText text={selectedCard.meaning_ru} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
