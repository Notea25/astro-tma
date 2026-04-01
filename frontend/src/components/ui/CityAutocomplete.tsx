import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export interface CityOption {
  displayName: string   // shown in dropdown
  cityName: string      // sent to backend
  lat: number
  lng: number
}

interface Props {
  value: string
  onChange: (value: string) => void
  onSelect: (option: CityOption) => void
  placeholder?: string
}

export function CityAutocomplete({ value, onChange, onSelect, placeholder }: Props) {
  const [options, setOptions] = useState<CityOption[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (value.length < 2) {
      setOptions([])
      setOpen(false)
      return
    }

    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      try {
        const resp = await fetch(
          `https://nominatim.openstreetmap.org/search?` +
          `q=${encodeURIComponent(value)}&format=json&limit=5&addressdetails=1`,
          { headers: { 'Accept-Language': 'ru,en' } }
        )
        const data = await resp.json()
        const results: CityOption[] = data
          .filter((p: any) => p.type !== 'administrative' || p.addresstype === 'city')
          .slice(0, 5)
          .map((p: any) => {
            const addr = p.address || {}
            const cityName =
              addr.city || addr.town || addr.village || addr.municipality ||
              addr.county || p.name || value
            const country = addr.country || ''
            const state = addr.state || ''
            const parts = [cityName, state !== cityName ? state : '', country]
              .filter(Boolean)
            return {
              displayName: parts.join(', '),
              cityName,
              lat: parseFloat(p.lat),
              lng: parseFloat(p.lon),
            }
          })
        setOptions(results)
        setOpen(results.length > 0)
      } catch {
        setOptions([])
        setOpen(false)
      } finally {
        setLoading(false)
      }
    }, 350)
  }, [value])

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleSelect = (opt: CityOption) => {
    onChange(opt.displayName)
    onSelect(opt)
    setOpen(false)
    setOptions([])
  }

  return (
    <div ref={containerRef} className="city-autocomplete">
      <div className="city-autocomplete__input-wrap">
        <input
          type="text"
          className="form-input"
          placeholder={placeholder ?? 'Москва, Лондон, Нью-Йорк...'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => options.length > 0 && setOpen(true)}
          autoComplete="off"
        />
        {loading && <span className="city-autocomplete__spinner">⏳</span>}
      </div>

      <AnimatePresence>
        {open && (
          <motion.ul
            className="city-autocomplete__dropdown"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.12 }}
          >
            {options.map((opt, i) => (
              <li
                key={i}
                className="city-autocomplete__option"
                onMouseDown={() => handleSelect(opt)}
              >
                <span className="city-autocomplete__option-icon">📍</span>
                <span className="city-autocomplete__option-text">{opt.displayName}</span>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  )
}
