import { motion } from 'framer-motion'
import type { EnergyScores } from '@/types'

const LABELS: { key: keyof EnergyScores; label: string }[] = [
  { key: 'love',   label: 'Любовь'  },
  { key: 'career', label: 'Карьера' },
  { key: 'health', label: 'Здоровье'},
  { key: 'luck',   label: 'Удача'   },
]

export function EnergyBars({ scores }: { scores: EnergyScores }) {
  return (
    <div className="energy-bars">
      {LABELS.map(({ key, label }) => (
        <div key={key} className="energy-row">
          <span className="energy-label">{label}</span>
          <div className="energy-track">
            <motion.div
              className="energy-fill"
              initial={{ width: 0 }}
              animate={{ width: `${scores[key]}%` }}
              transition={{ duration: 0.8, ease: 'easeOut', delay: 0.1 }}
            />
          </div>
          <span className="energy-val">{scores[key]}%</span>
        </div>
      ))}
    </div>
  )
}
