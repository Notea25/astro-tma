import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

interface LegendItem {
  key: string;
  title: string;
  text: string;
}

const LEGEND_ITEMS: LegendItem[] = [
  {
    key: "sky-earth",
    title: "Небо и земля",
    text: "Вертикаль показывает духовный вектор, смыслы и вдохновение. Горизонталь отвечает за земные задачи: тело, быт, действия и ресурсы.",
  },
  {
    key: "lineage-lines",
    title: "Линии рода",
    text: "Синяя диагональ относится к мужской линии рода, розовая - к женской. Они помогают увидеть поддержку семьи и повторяющиеся родовые сценарии.",
  },
  {
    key: "lineage-talents-karma",
    title: "Родовые таланты и карма",
    text: "Точки на диагоналях показывают, какие родовые таланты можно раскрывать и какие уроки важно завершать осознанно.",
  },
  {
    key: "comfort-zone",
    title: "Зона комфорта",
    text: "Розовые точки рядом с центром показывают привычный способ восстанавливать силы, а также место, где легко застрять без роста.",
  },
  {
    key: "love-money",
    title: "Любовь и финансы",
    text: "Сердце отмечает линию отношений, знак $ - финансовый канал. Оранжевые точки рядом с ними показывают вход и силу потока.",
  },
];

export function DestinyMatrixLegend() {
  const [openKey, setOpenKey] = useState<string | null>(null);

  return (
    <section className="destiny-legend" aria-labelledby="destiny-legend-title">
      <h3 id="destiny-legend-title" className="destiny-legend__title">
        Описание схемы
      </h3>
      <div className="destiny-legend__list">
        {LEGEND_ITEMS.map((item) => {
          const isOpen = openKey === item.key;
          const bodyId = `destiny-legend-${item.key}`;

          return (
            <div
              key={item.key}
              className={`destiny-legend__row${isOpen ? " is-open" : ""}`}
            >
              <button
                type="button"
                className="destiny-legend__head"
                onClick={() => setOpenKey(isOpen ? null : item.key)}
                aria-expanded={isOpen}
                aria-controls={bodyId}
              >
                <span className="destiny-legend__head-title">
                  {item.title}
                </span>
                <span className="destiny-legend__chevron" aria-hidden>
                  {isOpen ? "▾" : "▸"}
                </span>
              </button>

              <AnimatePresence initial={false}>
                {isOpen && (
                  <motion.div
                    key="body"
                    id={bodyId}
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.22 }}
                    className="destiny-legend__body"
                  >
                    <p className="destiny-legend__text">{item.text}</p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </section>
  );
}
