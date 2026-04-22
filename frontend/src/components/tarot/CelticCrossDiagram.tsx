import { useEffect, useRef, useState } from 'react'
import styles from './CelticCrossDiagram.module.css'

const CARD_W = 88
const CARD_H = 150
const LAYOUT_W = 720
const LAYOUT_H = 720
const MAX_W = 340

const SLOTS: { n: number; x: number; y: number; rotate?: number }[] = [
  { n: 1,  x: 200, y: 280 },
  { n: 2,  x: 200, y: 280, rotate: 90 },
  { n: 3,  x: 200, y: 100 },
  { n: 4,  x: 200, y: 460 },
  { n: 5,  x: 40,  y: 280 },
  { n: 6,  x: 360, y: 280 },
  { n: 7,  x: 560, y: 560 },
  { n: 8,  x: 560, y: 380 },
  { n: 9,  x: 560, y: 200 },
  { n: 10, x: 560, y: 20  },
]

export function CelticCrossDiagram() {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(0.35)

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const update = () => {
      const w = Math.min(el.clientWidth, MAX_W)
      if (!w) return
      setScale(w / LAYOUT_W)
    }
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  return (
    <div className={styles.diagramWrap} ref={wrapRef}>
      <div
        style={{ width: LAYOUT_W * scale, height: LAYOUT_H * scale, position: 'relative' }}
      >
        <div
          className={styles.diagram}
          style={{
            width: LAYOUT_W,
            height: LAYOUT_H,
            transform: `scale(${scale})`,
          }}
        >
          {SLOTS.map((s) => {
            const isCross = !!s.rotate
            return (
              <div
                key={s.n}
                className={`${styles.slot} ${isCross ? styles.slotCross : ''}`}
                style={{
                  left: s.x,
                  top: s.y,
                  width: CARD_W,
                  height: CARD_H,
                }}
              >
                <div
                  className={styles.rotor}
                  style={isCross ? { transform: `rotate(${s.rotate}deg)` } : undefined}
                >
                  {s.n}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
