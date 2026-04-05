import { useState } from 'react'
import { motion } from 'framer-motion'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { usersApi, natalApi } from '@/services/api'
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
  const [gender, setGender] = useState(user?.gender ?? '')

  const userSign = ZODIAC_SIGNS.find(s => s.value === user?.sun_sign)

  const { data: natalSummary } = useQuery({
    queryKey: ['natal-summary'],
    queryFn: natalApi.getSummary,
    enabled: !!user?.birth_city,
    staleTime: 1000 * 60 * 10,
  })

  const SIGN_RU: Record<string, string> = {
    Aries: 'Овен', Taurus: 'Телец', Gemini: 'Близнецы', Cancer: 'Рак',
    Leo: 'Лев', Virgo: 'Дева', Libra: 'Весы', Scorpio: 'Скорпион',
    Sagittarius: 'Стрелец', Capricorn: 'Козерог', Aquarius: 'Водолей', Pisces: 'Рыбы',
  }

  const birthMutation = useMutation({
    mutationFn: usersApi.setupBirth,
    onSuccess: async (resp: any) => {
      notification('success')
      impact('medium')
      setSavedCity(resp.city_resolved ?? birthCity)
      setEditing(false)
      const updated = await usersApi.upsertMe()
      setUser(updated)
      queryClient.invalidateQueries({ queryKey: ['natal-summary'] })
      queryClient.invalidateQueries({ queryKey: ['natal-full'] })
    },
  })

  const genderMutation = useMutation({
    mutationFn: (g: string) => usersApi.setGender(g),
    onSuccess: async (updated: any) => {
      setUser(updated)
    },
  })

  const handleSave = async () => {
    impact('light')
    if (gender && gender !== user?.gender) {
      await genderMutation.mutateAsync(gender)
    }
    if (birthDate && birthCity) {
      const datetime = birthTimeKnown && birthTime
        ? `${birthDate}T${birthTime}:00`
        : `${birthDate}T12:00:00`
      birthMutation.mutate({
        birth_date: datetime,
        birth_time_known: birthTimeKnown,
        birth_city: birthCity,
        ...(selectedCoords ?? {}),
      })
    } else if (gender && gender !== user?.gender) {
      // Only gender was changed — close editing
      notification('success')
      setEditing(false)
    }
  }

  const displayCity = savedCity ?? user?.birth_city

  return (
    <div className="screen profile-screen">
      <div className="screen-header">
        <h2 className="screen-title">Профиль</h2>
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
                <span>{user.gender === 'male' ? 'Мужской' : 'Женский'}</span>
              )}
              {userSign && <span>{userSign.label}</span>}
            </div>
            {natalSummary?.moon_sign && (
              <div className="profile-signs-triple">
                <span>☉ {(natalSummary.sun_sign && SIGN_RU[natalSummary.sun_sign]) ?? userSign?.label}</span>
                <span>·</span>
                <span>☽ {SIGN_RU[natalSummary.moon_sign]}</span>
                {natalSummary.ascendant_sign && (
                  <><span>·</span><span>↑ {SIGN_RU[natalSummary.ascendant_sign]}</span></>
                )}
              </div>
            )}
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
                    <span className="natal-summary-label">
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M7 1C4.79 1 3 2.79 3 5c0 3.25 4 8 4 8s4-4.75 4-8c0-2.21-1.79-4-4-4z"/>
                        <circle cx="7" cy="5" r="1.2"/>
                      </svg>
                      Город
                    </span>
                    <span className="natal-summary-value">{displayCity}</span>
                  </div>
                  <div className="natal-summary-row">
                    <span className="natal-summary-label">
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="7" cy="7" r="5.5"/>
                        <polyline points="7,4 7,7 9,8"/>
                      </svg>
                      Время
                    </span>
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
                <label className="form-label">Пол</label>
                <div className="gender-toggle">
                  <button
                    type="button"
                    className={`gender-btn${gender === 'male' ? ' active' : ''}`}
                    onClick={() => setGender('male')}
                  >
                    Мужской
                  </button>
                  <button
                    type="button"
                    className={`gender-btn${gender === 'female' ? ' active' : ''}`}
                    onClick={() => setGender('female')}
                  >
                    Женский
                  </button>
                </div>
              </div>

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
                <button
                  type="button"
                  className="toggle-row"
                  onClick={() => setBirthTimeKnown(v => !v)}
                  aria-pressed={birthTimeKnown}
                >
                  <span className="toggle-row__label">Знаю точное время рождения</span>
                  <span className={`toggle-switch${birthTimeKnown ? ' toggle-switch--on' : ''}`}>
                    <span className="toggle-switch__thumb" />
                  </span>
                </button>
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
                  disabled={(!gender && !birthDate) || (birthDate && !birthCity) || birthMutation.isPending || genderMutation.isPending}
                  whileTap={{ scale: 0.97 }}
                >
                  {birthMutation.isPending ? 'Считаем карту...' : 'Сохранить'}
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
