import { useQuery } from '@tanstack/react-query'
import { tarotApi } from '@/services/api'
import { useHaptic } from '@/hooks/useTelegram'
import { MeaningText } from '@/components/ui/MeaningText'
import type { TarotCardDetail } from '@/types'
import { SpreadReading } from './SpreadReading'
import styles from './TarotHistory.module.css'

type SpreadType = 'three_card' | 'celtic_cross' | 'week' | 'relationship'

const SPREAD_NAMES: Record<string, string> = {
  three_card: 'Прошлое · Настоящее · Будущее',
  celtic_cross: 'Кельтский крест',
  week: 'Карты на неделю',
  relationship: 'Отношения',
  single: 'Карта дня',
}

interface Props {
  openId: number | null
  onOpenIdChange: (readingId: number | null) => void
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffH = diffMs / 3_600_000
  if (diffH < 1) return 'только что'
  if (diffH < 24) return `${Math.floor(diffH)} ч назад`
  const diffD = diffH / 24
  if (diffD < 7) return `${Math.floor(diffD)} дн назад`
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

function DailyCardDetail({ card }: { card: TarotCardDetail | undefined }) {
  if (!card) {
    return <div className={styles.loading}>Не удалось загрузить карту дня.</div>
  }

  return (
    <div className={styles.dailyCard}>
      <div
        className={`${styles.dailyCardVisual} ${card.reversed ? styles.dailyCardVisualReversed : ''}`}
      >
        {card.image_url ? (
          <img src={card.image_url} alt={card.name_ru} />
        ) : (
          <div className={styles.dailyCardEmoji}>{card.emoji}</div>
        )}
      </div>

      <div className={styles.dailyCardContent}>
        <div className={styles.dailyCardMeta}>
          <span>{card.arcana === 'major' ? 'Старший аркан' : 'Младший аркан'}</span>
          <span className={card.reversed ? styles.dailyCardReversed : undefined}>
            {card.reversed ? '↓ Перевёрнутое' : '↑ Прямое'}
          </span>
        </div>
        <h4 className={styles.dailyCardName}>{card.name_ru}</h4>
        {card.keywords_ru.length > 0 && (
          <p className={styles.dailyCardKeywords}>
            {card.keywords_ru.slice(0, 3).join(' · ')}
          </p>
        )}
        <div className={styles.dailyCardMeaning}>
          <MeaningText text={card.meaning_ru} />
        </div>
      </div>
    </div>
  )
}

export function TarotHistory({ openId, onOpenIdChange }: Props) {
  const { impact } = useHaptic()

  const listQuery = useQuery({
    queryKey: ['tarot', 'history'],
    queryFn: () => tarotApi.history(),
    staleTime: 60_000,
  })

  const readingQuery = useQuery({
    queryKey: ['tarot', 'reading', openId],
    queryFn: () => tarotApi.getReading(openId!),
    enabled: openId !== null,
    staleTime: Infinity,
  })

  if (openId !== null) {
    return (
      <div className={styles.wrap}>
        <button
          className={styles.backLink}
          onClick={() => {
            impact('light')
            onOpenIdChange(null)
          }}
        >
          ← К списку
        </button>

        {readingQuery.isPending && (
          <div className={styles.loading}>Открываем расклад…</div>
        )}

        {readingQuery.data && (
          <>
            <div className={styles.detailHeader}>
              <h3 className={styles.detailTitle}>
                {SPREAD_NAMES[readingQuery.data.spread_type] ??
                  readingQuery.data.spread_type}
              </h3>
              {listQuery.data && (
                <div className={styles.detailDate}>
                  {formatDate(
                    listQuery.data.find((h) => h.reading_id === openId)
                      ?.created_at ?? '',
                  )}
                </div>
              )}
            </div>
            {readingQuery.data.spread_type === 'single' ? (
              <DailyCardDetail card={readingQuery.data.cards[0]} />
            ) : (
              <SpreadReading
                spreadType={readingQuery.data.spread_type as SpreadType}
                readingId={readingQuery.data.reading_id}
                cards={readingQuery.data.cards}
              />
            )}
          </>
        )}
      </div>
    )
  }

  return (
    <div className={styles.wrap}>
      {listQuery.isPending && (
        <div className={styles.loading}>Загружаем историю…</div>
      )}

      {listQuery.data && listQuery.data.length === 0 && (
        <div className={styles.empty}>
          У вас пока нет раскладов.
          <br />
          Сделайте первый — и он появится здесь.
        </div>
      )}

      {listQuery.data?.map((h) => (
        <div
          key={h.reading_id}
          className={styles.item}
          onClick={() => {
            impact('light')
            onOpenIdChange(h.reading_id)
          }}
        >
          <div className={styles.itemHeader}>
            <h4 className={styles.itemName}>
              {SPREAD_NAMES[h.spread_type] ?? h.spread_type}
            </h4>
            <span className={styles.itemDate}>
              {formatDate(h.created_at)}
            </span>
          </div>
          <div className={styles.itemPreview}>
            {h.card_previews.join(' · ')}
          </div>
          <div className={styles.itemMeta}>{h.card_count} карт</div>
        </div>
      ))}
    </div>
  )
}
