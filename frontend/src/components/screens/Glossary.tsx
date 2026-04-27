import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useAppStore } from "@/stores/app";
import { glossaryApi } from "@/services/api";

const CATEGORY_LABEL: Record<string, string> = {
  planet: "Планеты",
  sign: "Знаки",
  house: "Дома",
  aspect: "Аспекты",
  concept: "Понятия",
};

const CATEGORY_ORDER = ["planet", "sign", "house", "aspect", "concept"];

export function Glossary() {
  const { setScreen, setGlossarySlug } = useAppStore();
  const [query, setQuery] = useState("");
  const [activeCat, setActiveCat] = useState<string>("all");

  const { data: terms, isLoading } = useQuery({
    queryKey: ["glossary", query],
    queryFn: () => glossaryApi.list(query ? { q: query } : undefined),
    staleTime: 1000 * 60 * 10,
  });

  const grouped = useMemo(() => {
    const map: Record<string, typeof terms> = {};
    if (!terms) return map;
    for (const t of terms) {
      if (!map[t.category]) map[t.category] = [];
      map[t.category]!.push(t);
    }
    return map;
  }, [terms]);

  const availableCats = useMemo(() => {
    if (!terms) return new Set<string>();
    return new Set(terms.map((t) => t.category));
  }, [terms]);

  const visibleCats =
    activeCat === "all"
      ? CATEGORY_ORDER
      : CATEGORY_ORDER.filter((c) => c === activeCat);

  const openTerm = (slug: string) => {
    setGlossarySlug(slug);
    setScreen("glossary_term");
  };

  return (
    <div className="screen glossary-screen">
      <div className="screen-header screen-header--with-back">
        <button
          className="back-btn"
          onClick={() => setScreen("discover", "back")}
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
        <h2 className="screen-title">Глоссарий</h2>
      </div>

      <div className="screen-content">
        <input
          type="search"
          className="form-input"
          placeholder="Поиск термина..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ marginBottom: 12 }}
        />

        {terms && terms.length > 0 && (
          <div className="category-chips">
            <button
              type="button"
              className={`category-chip${activeCat === "all" ? " is-active" : ""}`}
              onClick={() => setActiveCat("all")}
            >
              Все
            </button>
            {CATEGORY_ORDER.filter((c) => availableCats.has(c)).map((cat) => (
              <button
                type="button"
                key={cat}
                className={`category-chip${activeCat === cat ? " is-active" : ""}`}
                onClick={() => setActiveCat(cat)}
              >
                {CATEGORY_LABEL[cat] ?? cat}
              </button>
            ))}
          </div>
        )}

        {isLoading && (
          <p style={{ color: "var(--text-secondary)", textAlign: "center" }}>
            Загрузка...
          </p>
        )}

        {terms && terms.length === 0 && (
          <p style={{ color: "var(--text-secondary)", textAlign: "center" }}>
            Ничего не найдено.
          </p>
        )}

        {terms &&
          terms.length > 0 &&
          visibleCats.map((cat) => {
            const items = grouped[cat];
            if (!items || items.length === 0) return null;
            return (
              <div key={cat} className="discover-section">
                <h3 className="discover-section__title">
                  {CATEGORY_LABEL[cat] ?? cat}
                </h3>
                <div className="glossary-list">
                  {items.map((t, idx) => (
                    <motion.button
                      key={t.slug}
                      className="glossary-item"
                      onClick={() => openTerm(t.slug)}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.02, duration: 0.2 }}
                    >
                      <div className="glossary-item__title">{t.title_ru}</div>
                      <div className="glossary-item__short">{t.short_ru}</div>
                    </motion.button>
                  ))}
                </div>
              </div>
            );
          })}
      </div>
    </div>
  );
}
