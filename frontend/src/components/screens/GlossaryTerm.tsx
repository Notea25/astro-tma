import { useQuery } from "@tanstack/react-query";
import { useAppStore } from "@/stores/app";
import { glossaryApi } from "@/services/api";

const CATEGORY_LABEL: Record<string, string> = {
  planet: "Планета",
  sign: "Знак",
  house: "Дом",
  aspect: "Аспект",
  concept: "Понятие",
};

export function GlossaryTerm() {
  const { setScreen, glossarySlug, setGlossarySlug } = useAppStore();

  const { data, isLoading, error } = useQuery({
    queryKey: ["glossary-term", glossarySlug],
    queryFn: () => glossaryApi.get(glossarySlug!),
    enabled: !!glossarySlug,
    staleTime: 1000 * 60 * 60,
  });

  const openRelated = (slug: string) => {
    setGlossarySlug(slug);
  };

  return (
    <div className="screen glossary-screen">
      <div className="screen-header screen-header--with-back">
        <button
          className="back-btn"
          onClick={() => setScreen("glossary", "back")}
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
        <h2 className="screen-title">{data?.title_ru ?? "Термин"}</h2>
      </div>

      <div className="screen-content">
        {isLoading && (
          <p style={{ color: "var(--text-dim)", textAlign: "center" }}>
            Загрузка...
          </p>
        )}
        {error && (
          <p style={{ color: "var(--text-dim)", textAlign: "center" }}>
            Термин не найден.
          </p>
        )}
        {data && (
          <>
            <div className="horoscope-card">
              <div
                className="horoscope-card__period"
                style={{ marginBottom: 8 }}
              >
                {CATEGORY_LABEL[data.category] ?? data.category}
              </div>
              <p
                style={{
                  fontSize: 15,
                  lineHeight: 1.5,
                  whiteSpace: "pre-wrap",
                }}
              >
                {data.full_ru}
              </p>
            </div>

            {data.related.length > 0 && (
              <div className="horoscope-card">
                <div
                  className="horoscope-card__period"
                  style={{ marginBottom: 12 }}
                >
                  См. также
                </div>
                <div className="glossary-list">
                  {data.related.map((r) => (
                    <button
                      key={r.slug}
                      className="glossary-item"
                      onClick={() => openRelated(r.slug)}
                    >
                      <div className="glossary-item__title">{r.title_ru}</div>
                      <div className="glossary-item__short">{r.short_ru}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
