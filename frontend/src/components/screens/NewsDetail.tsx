import { useQuery } from "@tanstack/react-query";
import { useAppStore } from "@/stores/app";
import { newsApi } from "@/services/api";

const CATEGORY_LABEL: Record<string, string> = {
  aspect: "Аспект",
  ingress: "Переход",
  moon: "Луна",
  event: "Событие",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  const months = [
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
  ];
  return `${d.getDate()} ${months[d.getMonth()]}`;
}

export function NewsDetail() {
  const { setScreen, newsId } = useAppStore();

  const { data, isLoading, error } = useQuery({
    queryKey: ["news-item", newsId],
    queryFn: () => newsApi.get(newsId!),
    enabled: !!newsId,
    staleTime: 1000 * 60 * 30,
  });

  return (
    <div className="screen">
      <div className="screen-header screen-header--with-back">
        <button
          className="back-btn"
          onClick={() => setScreen("news", "back")}
          aria-label="Назад"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M13 4l-6 6 6 6" />
          </svg>
        </button>
        <h2 className="screen-title">Новость</h2>
      </div>

      <div className="screen-content">
        {isLoading && (
          <p style={{ color: "var(--text-secondary)", textAlign: "center" }}>
            Загрузка...
          </p>
        )}
        {error && (
          <p style={{ color: "var(--text-secondary)", textAlign: "center" }}>
            Не найдено.
          </p>
        )}
        {data && (
          <div className="horoscope-card">
            <div className="horoscope-card__period" style={{ marginBottom: 8 }}>
              {CATEGORY_LABEL[data.category] ?? data.category} ·{" "}
              {formatDate(data.date)}
            </div>
            <h3 style={{ fontSize: 18, marginBottom: 12, lineHeight: 1.3 }}>
              {data.title_ru}
            </h3>
            <div
              style={{
                fontSize: 14,
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
                color: "var(--text-primary)",
              }}
            >
              {data.body_md}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
