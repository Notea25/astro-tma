import { useState } from 'react'
import { motion } from 'framer-motion'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { usersApi } from '@/services/api'
import { useAppStore } from '@/stores/app'
import { useHaptic } from '@/hooks/useTelegram'
import { ZODIAC_SIGNS } from '@/types'
import { CityAutocomplete, type CityOption } from '@/components/ui/CityAutocomplete'

export function Profile() {
  const { user, setUser } = useAppStore()
  const { impact, notification } = useHaptic()
  const queryClient = useQueryClient()

  const [editing, setEditing] = useState(false)
  const [birthDate, setBirthDate] = useState('')
  const [birthTime, setBirthTime] = useState('')
  const [birthTimeKnown, setBirthTimeKnown] = useState(user?.birth_time_known ?? false)
  const [birthCity, setBirthCity] = useState(user?.birth_city ?? '')
  const [selectedCoords, setSelectedCoords] = useState<{ lat: number; lng: number } | null>(null)
  const [savedCity, setSavedCity] = useState<string | null>(null)

  const userSign = ZODIAC_SIGNS.find(s => s.value === user?.sun_sign)

  const birthMutation = useMutation({
    mutationFn: usersApi.setupBirth,
    onSuccess: async (resp: any) => {
      notification('success')
      impact('medium')
      setSavedCity(resp.city_resolved ?? birthCity)
      setEditing(false)
      // Refresh user in store
      const updated = await usersApi.upsertMe()
      setUser(updated)
      // Invalidate natal queries so Natal tab re-fetches fresh data
      queryClient.invalidateQueries({ queryKey: ['natal-summary'] })
      queryClient.invalidateQueries({ queryKey: ['natal-full'] })
    },
  })

  const handleSave = () => {
    if (!birthDate || !birthCity) return
    impact('light')
    const datetime = birthTimeKnown && birthTime
      ? `${birthDate}T${birthTime}:00`
      : `${birthDate}T12:00:00`
    birthMutation.mutate({
      birth_date: datetime,
      birth_time_known: birthTimeKnown,
      birth_city: birthCity,
      ...(selectedCoords ?? {}),
    })
  }

  const displayCity = savedCity ?? user?.birth_city

  return (
    <div className="screen profile-screen">
      <div className="screen-header">
        <h2 className="screen-title">Профиль</h2>
        <p className="screen-subtitle">Личный кабинет</p>
      </div>

      <div className="screen-content">
        {/* User card */}
        <motion.div
          className="profile-card"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="profile-avatar">
            {user?.name?.charAt(0)?.toUpperCase() ?? '?'}
          </div>
          <div className="profile-info">
            <div className="profile-name">{user?.name ?? 'Пользователь'}</div>
            <div className="profile-meta">
              {user?.gender && (
                <span>{user.gender === 'male' ? 'М' : 'Ж'}</span>
              )}
              {userSign && <span>{userSign.label}</span>}
            </div>
          </div>
        </motion.div>

        {/* Birth data section */}
        <motion.div
          className="natal-card"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.08 }}
        >
          <div className="natal-card__tag">✦ Данные рождения</div>

          {!editing ? (
            <>
              {displayCity ? (
                <div className="profile-birth-info">
                  <div className="natal-summary-row">
                    <span className="natal-summary-label">📍 Город:</span>
                    <span className="natal-summary-value">{displayCity}</span>
                  </div>
                  <div className="natal-summary-row">
                    <span className="natal-summary-label">⏰ Время:</span>
                    <span className="natal-summary-value">
                      {user?.birth_time_known ? 'Точное' : 'Неизвестно (полдень)'}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="profile-birth-empty">
                  Данные рождения не указаны. Добавьте их для расчёта натальной карты.
                </p>
              )}
              <button
                className="btn-primary"
                style={{ marginTop: '0.75rem' }}
                onClick={() => {
                  impact('light')
                  setBirthCity(displayCity ?? '')
                  setEditing(true)
                }}
              >
                {displayCity ? 'Изменить' : 'Добавить данные'}
              </button>
            </>
          ) : (
            <div className="profile-edit-form">
              <div className="form-group">
                <label className="form-label">Дата рождения</label>
                <input
                  type="date"
                  className="form-input"
                  value={birthDate}
                  onChange={(e) => setBirthDate(e.target.value)}
                  max={new Date().toISOString().split('T')[0]}
                />
              </div>

              <div className="form-group">
                <label className="form-label checkbox-label">
                  <input
                    type="checkbox"
                    checked={birthTimeKnown}
                    onChange={(e) => setBirthTimeKnown(e.target.checked)}
                  />
                  Знаю точное время рождения
                </label>
              </div>

              {birthTimeKnown && (
                <div className="form-group">
                  <label className="form-label">Время рождения</label>
                  <input
                    type="time"
                    className="form-input"
                    value={birthTime}
                    onChange={(e) => setBirthTime(e.target.value)}
                  />
                </div>
              )}

              <div className="form-group">
                <label className="form-label">Город рождения</label>
                <CityAutocomplete
                  value={birthCity}
                  onChange={(v) => { setBirthCity(v); setSelectedCoords(null) }}
                  onSelect={(opt: CityOption) => {
                    setBirthCity(opt.displayName)
                    setSelectedCoords({ lat: opt.lat, lng: opt.lng })
                  }}
                />
                {selectedCoords && (
                  <div className="city-autocomplete__confirmed">
                    ✓ {selectedCoords.lat.toFixed(4)}° {selectedCoords.lat >= 0 ? 'с.ш.' : 'ю.ш.'}
                    &nbsp;&nbsp;{selectedCoords.lng.toFixed(4)}° {selectedCoords.lng >= 0 ? 'в.д.' : 'з.д.'}
                  </div>
                )}
              </div>

              <div className="profile-edit-actions">
                <motion.button
                  className="btn-primary"
                  onClick={handleSave}
                  disabled={!birthDate || !birthCity || birthMutation.isPending}
                  whileTap={{ scale: 0.97 }}
                >
                  {birthMutation.isPending ? '⏳ Считаем карту...' : 'Сохранить'}
                </motion.button>
                <button
                  className="btn-ghost"
                  onClick={() => { impact('light'); setEditing(false) }}
                  disabled={birthMutation.isPending}
                >
                  Отмена
                </button>
              </div>

              {birthMutation.isError && (
                <p className="profile-error">
                  Ошибка сохранения. Проверьте название города.
                </p>
              )}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
