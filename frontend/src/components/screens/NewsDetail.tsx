import { useQuery } from "@tanstack/react-query";
import { useAppStore } from "@/stores/app";
import { newsApi } from "@/services/api";
import { cleanMarkdownText } from "@/utils/text";

const CATEGORY_LABEL: Record<string, string> = {
  aspect: "Аспект",
  ingress: "Переход планеты",
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

/**
 * Split a markdown-ish body into an array of paragraphs. We don't run a
 * full markdown parser — backend currently returns plain prose with empty
 * lines between paragraphs, so a simple split is enough. Markdown-style
 * markers are stripped by cleanMarkdownText upstream.
 */
function splitParagraphs(body: string): string[] {
  return cleanMarkdownText(body)
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);
}

export function NewsDetail() {
  const { setScreen, newsId } = useAppStore();

  const { data, isLoading, error } = useQuery({
    queryKey: ["news-item", newsId],
    queryFn: () => newsApi.get(newsId!),
    enabled: !!newsId,
    staleTime: 1000 * 60 * 30,
  });

  const paragraphs = data ? splitParagraphs(data.body_md) : [];
  const firstChar = paragraphs[0]?.charAt(0) ?? "";
  const firstRest = paragraphs[0]?.slice(1) ?? "";

  return (
    <div className="screen news-screen">
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
          <p style={{ color: "var(--text-dim)", textAlign: "center" }}>
            Загрузка...
          </p>
        )}
        {error && (
          <p style={{ color: "var(--text-dim)", textAlign: "center" }}>
            Не найдено.
          </p>
        )}
        {data && (
          <article className="gx-article">
            <div className="gx-article__eyebrow">
              {CATEGORY_LABEL[data.category] ?? data.category} ·{" "}
              {formatDate(data.date)}
            </div>
            <h1 className="gx-article__title">
              {cleanMarkdownText(data.title_ru)}
            </h1>
            <div className="gx-article__rule" />
            <div className="gx-article__body">
              {paragraphs.length > 0 && (
                <p>
                  <span className="gx-article__dropcap">{firstChar}</span>
                  {firstRest}
                </p>
              )}
              {paragraphs.slice(1).map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
          </article>
        )}
      </div>
    </div>
  );
}
