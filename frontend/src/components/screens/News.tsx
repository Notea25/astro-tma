import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useAppStore } from "@/stores/app";
import { newsApi } from "@/services/api";

const CATEGORY_EMOJI: Record<string, string> = {
  aspect: "✦",
  ingress: "→",
  moon: "☽",
  event: "☉",
};

const CATEGORY_LABEL: Record<string, string> = {
  aspect: "Аспекты",
  ingress: "Ингрессии",
  moon: "Луна",
  event: "События",
};
const CATEGORY_ORDER = ["aspect", "ingress", "moon", "event"];

function formatDate(iso: string): string {
  const d = new Date(iso);
  const months = [
    "янв",
    "фев",
    "мар",
    "апр",
    "май",
    "июн",
    "июл",
    "авг",
    "сен",
    "окт",
    "ноя",
    "дек",
  ];
  return `${d.getDate()} ${months[d.getMonth()]}`;
}

export function News() {
  const { setScreen, setNewsId } = useAppStore();
  const [filter, setFilter] = useState<string>("all");

  const { data, isLoading } = useQuery({
    queryKey: ["news"],
    queryFn: () => newsApi.list({ limit: 30 }),
    staleTime: 1000 * 60 * 30,
  });

  const filtered = useMemo(() => {
    if (!data) return [];
    if (filter === "all") return data;
    return data.filter((n) => n.category === filter);
  }, [data, filter]);

  const availableCats = useMemo(() => {
    if (!data) return new Set<string>();
    return new Set(data.map((n) => n.category));
  }, [data]);

  const openItem = (id: number) => {
    setNewsId(id);
    setScreen("news_detail");
  };

  return (
    <div className="screen news-screen">
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
        <h2 className="screen-title">Астро-новости</h2>
      </div>

      <div className="screen-content">
        <div className="news-intro">
          Астрособытия — важные транзиты, ингрессии планет, затмения,
          полнолуния. Они влияют на коллективное поле и объясняют, почему в
          определённые недели «весь мир штормит».
        </div>

        {data && data.length > 0 && (
          <div className="category-chips">
            <button
              type="button"
              className={`category-chip${filter === "all" ? " is-active" : ""}`}
              onClick={() => setFilter("all")}
            >
              Все
            </button>
            {CATEGORY_ORDER.filter((c) => availableCats.has(c)).map((cat) => (
              <button
                type="button"
                key={cat}
                className={`category-chip${filter === cat ? " is-active" : ""}`}
                onClick={() => setFilter(cat)}
              >
                <span>{CATEGORY_EMOJI[cat] ?? "✦"}</span>{" "}
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
        {data && data.length === 0 && (
          <p style={{ color: "var(--text-secondary)", textAlign: "center" }}>
            Новостей пока нет. Загляните позже.
          </p>
        )}
        {filtered.length === 0 && data && data.length > 0 && (
          <p style={{ color: "var(--text-secondary)", textAlign: "center" }}>
            В этой категории пока пусто.
          </p>
        )}
        {filtered.map((item, idx) => (
          <motion.button
            key={item.id}
            className="news-card"
            onClick={() => openItem(item.id)}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.03, duration: 0.25 }}
          >
            <div className="news-card__date">
              {CATEGORY_EMOJI[item.category] ?? "✦"} {formatDate(item.date)}
            </div>
            <div className="news-card__title">{item.title_ru}</div>
            <div className="news-card__body">{item.preview}</div>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
