import { useState } from "react";
import type { ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";

interface LegendItem {
  key: string;
  title: string;
  text: string;
  descriptionKind: "axis" | "lineage" | "diagonal-dots" | "comfort" | "love-money";
}

const LEGEND_ITEMS: LegendItem[] = [
  {
    key: "sky-earth",
    title: "Небо и земля",
    text: "Вертикаль показывает духовный вектор, смыслы и вдохновение. Горизонталь отвечает за земные задачи: тело, быт, действия и ресурсы.",
    descriptionKind: "axis",
  },
  {
    key: "lineage-lines",
    title: "Линии рода",
    text: "Обе линии помогают увидеть поддержку семьи и повторяющиеся родовые сценарии.",
    descriptionKind: "lineage",
  },
  {
    key: "lineage-talents-karma",
    title: "Родовые таланты и карма",
    text: "Точки на диагоналях показывают, какие родовые таланты можно раскрывать и какие уроки важно завершать осознанно.",
    descriptionKind: "diagonal-dots",
  },
  {
    key: "comfort-zone",
    title: "Зона комфорта",
    text: "Розовые точки рядом с центром показывают привычный способ восстанавливать силы, а также место, где легко застрять без роста.",
    descriptionKind: "comfort",
  },
  {
    key: "love-money",
    title: "Любовь и финансы",
    text: "Сердце отмечает линию отношений, знак $ - финансовый канал. Оранжевые точки рядом с ними показывают вход и силу потока.",
    descriptionKind: "love-money",
  },
];

function AxisArrowIcon({ direction }: { direction: "vertical" | "horizontal" }) {
  const isVertical = direction === "vertical";
  const markerId = `dm-legend-${direction}-axis-arrow`;
  const color = "rgba(232, 200, 98, 0.72)";

  return (
    <svg
      className="destiny-legend__axis-arrow"
      viewBox="0 0 34 34"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <marker
          id={markerId}
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="4"
          markerHeight="4"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill={color} />
        </marker>
      </defs>
      <line
        x1={isVertical ? "17" : "5"}
        y1={isVertical ? "5" : "17"}
        x2={isVertical ? "17" : "29"}
        y2={isVertical ? "29" : "17"}
        stroke={color}
        strokeWidth="1.8"
        markerStart={`url(#${markerId})`}
        markerEnd={`url(#${markerId})`}
      />
    </svg>
  );
}

function AxisDescription() {
  return (
    <div className="destiny-legend__axis-description">
      <div className="destiny-legend__axis-row">
        <AxisArrowIcon direction="vertical" />
        <span>
          <strong>Вертикальная стрелка</strong> показывает духовный
          вектор, смыслы и вдохновение.
        </span>
      </div>
      <div className="destiny-legend__axis-row">
        <AxisArrowIcon direction="horizontal" />
        <span>
          <strong>Горизонтальная стрелка</strong> отвечает за земные задачи:
          тело, быт, действия и ресурсы.
        </span>
      </div>
    </div>
  );
}

function LineageArrowIcon({ kind }: { kind: "father" | "mother" }) {
  const isFather = kind === "father";
  const color = isFather
    ? "rgba(120, 145, 220, 0.75)"
    : "rgba(220, 110, 130, 0.75)";
  const markerId = `dm-legend-${kind}-description-arrow`;

  return (
    <svg
      className="destiny-legend__lineage-arrow"
      viewBox="0 0 34 24"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <marker
          id={markerId}
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="4"
          markerHeight="4"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill={color} />
        </marker>
      </defs>
      <line
        x1="5"
        y1="12"
        x2="29"
        y2="12"
        stroke={color}
        strokeWidth="1.8"
        markerStart={`url(#${markerId})`}
        markerEnd={`url(#${markerId})`}
      />
    </svg>
  );
}

function LineageDescription({ text }: { text: string }) {
  return (
    <div className="destiny-legend__lineage-description">
      <div className="destiny-legend__lineage-row">
        <LineageArrowIcon kind="father" />
        <span>
          <strong>Синяя стрелка</strong> — мужская линия рода.
        </span>
      </div>
      <div className="destiny-legend__lineage-row">
        <LineageArrowIcon kind="mother" />
        <span>
          <strong>Розовая стрелка</strong> — женская линия рода.
        </span>
      </div>
      <p className="destiny-legend__text">{text}</p>
    </div>
  );
}

function DiagonalDotsIcon() {
  return (
    <svg className="destiny-legend__visual-icon" viewBox="0 0 34 34" aria-hidden="true">
      <line
        x1="5"
        y1="29"
        x2="29"
        y2="5"
        stroke="rgba(232, 200, 98, 0.45)"
        strokeWidth="1.6"
      />
      <circle cx="11" cy="23" r="4" fill="rgba(232, 200, 98, 0.95)" />
      <circle cx="23" cy="11" r="4" fill="#e07b6a" />
    </svg>
  );
}

function ComfortDotsIcon() {
  return (
    <svg className="destiny-legend__visual-icon" viewBox="0 0 34 34" aria-hidden="true">
      <circle cx="10" cy="17" r="5" fill="#d27b9c" />
      <circle cx="24" cy="17" r="5" fill="#d27b9c" />
    </svg>
  );
}

function HeartIcon() {
  return (
    <svg className="destiny-legend__visual-icon" viewBox="0 0 34 34" aria-hidden="true">
      <path
        d="M17 28S5 21.2 5 12.5C5 8.7 7.8 6 11.3 6c2.5 0 4.6 1.4 5.7 3.4C18.1 7.4 20.2 6 22.7 6 26.2 6 29 8.7 29 12.5 29 21.2 17 28 17 28Z"
        fill="#d27b9c"
      />
    </svg>
  );
}

function MoneyIcon() {
  return (
    <svg className="destiny-legend__visual-icon" viewBox="0 0 34 34" aria-hidden="true">
      <circle cx="17" cy="17" r="13" fill="rgba(232, 165, 83, 0.16)" stroke="#e8a553" />
      <text
        x="17"
        y="23"
        textAnchor="middle"
        fill="#e8a553"
        fontSize="18"
        fontWeight="700"
      >
        $
      </text>
    </svg>
  );
}

function OrangeDotsIcon() {
  return (
    <svg className="destiny-legend__visual-icon" viewBox="0 0 34 34" aria-hidden="true">
      <circle cx="10" cy="17" r="5" fill="#e8a553" />
      <circle cx="24" cy="17" r="5" fill="#e8a553" />
    </svg>
  );
}

function SingleVisualDescription({
  icon,
  text,
}: {
  icon: ReactNode;
  text: string;
}) {
  return (
    <div className="destiny-legend__visual-description">
      <div className="destiny-legend__visual-row">
        {icon}
        <span>{text}</span>
      </div>
    </div>
  );
}

function LoveMoneyDescription() {
  return (
    <div className="destiny-legend__visual-description">
      <div className="destiny-legend__visual-row">
        <HeartIcon />
        <span>
          <strong>Сердце</strong> отмечает линию отношений.
        </span>
      </div>
      <div className="destiny-legend__visual-row">
        <MoneyIcon />
        <span>
          <strong>Знак $</strong> отмечает финансовый канал.
        </span>
      </div>
      <div className="destiny-legend__visual-row">
        <OrangeDotsIcon />
        <span>
          <strong>Оранжевые точки</strong> показывают вход и силу потока.
        </span>
      </div>
    </div>
  );
}

function LegendDescription({ item }: { item: LegendItem }) {
  switch (item.descriptionKind) {
    case "axis":
      return <AxisDescription />;
    case "lineage":
      return <LineageDescription text={item.text} />;
    case "diagonal-dots":
      return <SingleVisualDescription icon={<DiagonalDotsIcon />} text={item.text} />;
    case "comfort":
      return <SingleVisualDescription icon={<ComfortDotsIcon />} text={item.text} />;
    case "love-money":
      return <LoveMoneyDescription />;
  }
}

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
                    <LegendDescription item={item} />
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
