import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, type PanInfo } from "framer-motion";
import { PremiumGate } from "@/components/ui/PremiumGate";
import { NatalBasicSkeleton } from "@/components/ui/Skeleton";
import { useAppStore } from "@/stores/app";
import { natalApi } from "@/services/api";
import { ZODIAC_SIGNS } from "@/types";
import { NatalChart } from "@/components/NatalChart";
import { toNatalChartData } from "@/components/NatalChart/adapter";

type NatalTab = "circle" | "elements" | "planets" | "houses" | "aspects";
type ReadingSection = { title?: string; body: string };
type NatalInterpretationSlide = {
  id: string;
  label: string;
  title: string;
  body: string;
};

const NATAL_TABS: { key: NatalTab; label: string }[] = [
  { key: "circle", label: "Круг" },
  { key: "elements", label: "Стихии" },
  { key: "planets", label: "Планеты" },
  { key: "houses", label: "Дома" },
  { key: "aspects", label: "Аспекты" },
];

const SWIPE_OFFSET_THRESHOLD = 60;
const SWIPE_VELOCITY_THRESHOLD = 500;

type HouseAxisLabel = "Асцендент" | "Основание" | "Десцендент" | "Середина неба";

const HOUSE_AXIS_LABELS: Record<number, HouseAxisLabel> = {
  1: "Асцендент",
  4: "Основание",
  7: "Десцендент",
  10: "Середина неба",
};

const ZODIAC_GLYPHS: Record<string, string> = {
  aries: "♈",
  taurus: "♉",
  gemini: "♊",
  cancer: "♋",
  leo: "♌",
  virgo: "♍",
  libra: "♎",
  scorpio: "♏",
  sagittarius: "♐",
  capricorn: "♑",
  aquarius: "♒",
  pisces: "♓",
};

const ZODIAC_TONES: Record<string, string> = {
  aries: "coral",
  taurus: "green",
  gemini: "violet",
  cancer: "blue",
  leo: "gold",
  virgo: "gold",
  libra: "teal",
  scorpio: "rose",
  sagittarius: "gold",
  capricorn: "violet",
  aquarius: "blue",
  pisces: "aqua",
};

const ZODIAC_WHEEL_GLYPHS = [
  "♓",
  "♈",
  "♉",
  "♊",
  "♋",
  "♌",
  "♍",
  "♎",
  "♏",
  "♐",
  "♑",
  "♒",
];

// Split LLM reading by **Section** markers into reusable slide data.
function parseReadingSections(text: string): ReadingSection[] {
  // Remove leading # header line if present
  const cleaned = text.replace(/^#[^\n]*\n?/, "").trim();
  if (!cleaned) return [];

  // Split into segments: ["intro text", "SectionTitle", "body", "SectionTitle", "body", ...]
  const parts = cleaned.split(/\*\*([^*]+)\*\*/);

  const blocks: ReadingSection[] = [];
  let i = 0;

  // If text starts before first **, treat as intro
  if (parts[0].trim()) {
    blocks.push({ body: parts[0].trim() });
  }
  i = 1;

  while (i < parts.length) {
    const title = parts[i]?.trim();
    const body = parts[i + 1]?.trim() ?? "";
    if (title) blocks.push({ title, body });
    i += 2;
  }

  return blocks.filter((block) => block.title || block.body);
}

function NatalInterpretationSlider({
  slides,
}: {
  slides: NatalInterpretationSlide[];
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const tabsRef = useRef<HTMLDivElement | null>(null);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    if (activeIndex > slides.length - 1) {
      setActiveIndex(Math.max(slides.length - 1, 0));
    }
  }, [activeIndex, slides.length]);

  useEffect(() => {
    const tabs = tabsRef.current;
    const activeTab = tabRefs.current[activeIndex];
    if (!tabs || !activeTab) return;

    const centeredLeft =
      activeTab.offsetLeft - tabs.clientWidth / 2 + activeTab.clientWidth / 2;
    tabs.scrollTo({
      left: Math.max(0, centeredLeft),
      behavior: "smooth",
    });
  }, [activeIndex]);

  if (slides.length === 0) return null;

  const activeSlide =
    slides[Math.min(activeIndex, slides.length - 1)] ?? slides[0];

  const goToSlide = (index: number) => {
    setActiveIndex(Math.max(0, Math.min(slides.length - 1, index)));
  };

  const handleDragEnd = (_: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
    const shouldGoNext =
      info.offset.x < -SWIPE_OFFSET_THRESHOLD ||
      info.velocity.x < -SWIPE_VELOCITY_THRESHOLD;
    const shouldGoPrevious =
      info.offset.x > SWIPE_OFFSET_THRESHOLD ||
      info.velocity.x > SWIPE_VELOCITY_THRESHOLD;

    if (shouldGoNext) {
      goToSlide(activeIndex + 1);
    } else if (shouldGoPrevious) {
      goToSlide(activeIndex - 1);
    }
  };

  return (
    <div className="natal-interpretation-slider">
      <div className="natal-interpretation-tabs" role="tablist" ref={tabsRef}>
        {slides.map((slide, index) => (
          <button
            key={slide.id}
            ref={(node) => {
              tabRefs.current[index] = node;
            }}
            type="button"
            role="tab"
            aria-selected={index === activeIndex}
            className={`natal-interpretation-tab${
              index === activeIndex ? " is-active" : ""
            }`}
            onClick={() => goToSlide(index)}
          >
            {slide.label}
          </button>
        ))}
      </div>

      <div className="natal-interpretation-progress">
        <div className="natal-interpretation-progress__count">
          {activeIndex + 1}/{slides.length}
        </div>
        <div className="natal-interpretation-dots">
          {slides.map((slide, index) => {
            const distance = Math.abs(index - activeIndex);
            const sizeClass =
              distance === 0
                ? " is-active"
                : distance === 1
                  ? " is-near"
                  : distance === 2
                    ? " is-mid"
                    : "";

            return (
              <button
                key={`dot-${slide.id}`}
                type="button"
                className={`natal-interpretation-dot${sizeClass}`}
                onClick={() => goToSlide(index)}
                aria-label={`Открыть слайд ${index + 1}`}
              />
            );
          })}
        </div>
      </div>

      <div className="natal-interpretation-stage">
        <motion.div
          key={activeSlide.id}
          className="natal-interpretation-slide"
          drag={slides.length > 1 ? "x" : false}
          dragConstraints={{ left: 0, right: 0 }}
          dragElastic={0.18}
          onDragEnd={handleDragEnd}
          initial={{ opacity: 0, x: 18 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
        >
          <div className="natal-interpretation-slide__head">
            <h3 className="natal-interpretation-slide__title">
              {activeSlide.title}
            </h3>
          </div>
          <p className="natal-interpretation-slide__text">{activeSlide.body}</p>
        </motion.div>
      </div>
    </div>
  );
}

// Backend returns English sign names — translate to Russian
const SIGN_EN_TO_RU: Record<string, string> = {
  Aries: "Овен",
  Taurus: "Телец",
  Gemini: "Близнецы",
  Cancer: "Рак",
  Leo: "Лев",
  Virgo: "Дева",
  Libra: "Весы",
  Scorpio: "Скорпион",
  Sagittarius: "Стрелец",
  Capricorn: "Козерог",
  Aquarius: "Водолей",
  Pisces: "Рыбы",
};
const toRu = (s: string | null | undefined) =>
  s ? (SIGN_EN_TO_RU[s] ?? s) : "—";

// SVG icons for elements (celestial style)
function IconFire() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 2c0 4-4 6-4 10a4 4 0 0 0 8 0c0-4-4-6-4-10z" />
      <path
        d="M12 18a2 2 0 0 0 2-2c0-2-2-3-2-5-0 2-2 3-2 5a2 2 0 0 0 2 2z"
        opacity="0.5"
      />
    </svg>
  );
}
function IconEarth() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="9" />
      <path
        d="M3 12h18M12 3a15 15 0 0 1 4 9 15 15 0 0 1-4 9 15 15 0 0 1-4-9 15 15 0 0 1 4-9z"
        opacity="0.7"
      />
    </svg>
  );
}
function IconAir() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M9.59 4.59A2 2 0 1 1 11 8H2" />
      <path d="M12.59 19.41A2 2 0 1 0 14 16H2" />
      <path d="M17.73 7.73A2.5 2.5 0 1 1 19.5 12H2" opacity="0.7" />
    </svg>
  );
}
function IconWater() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 2c0 0-6 7-6 11a6 6 0 0 0 12 0c0-4-6-11-6-11z" />
      <path d="M8 16a4 4 0 0 0 4 4" opacity="0.5" />
    </svg>
  );
}

const ELEMENT_ICONS: Record<string, () => JSX.Element> = {
  fire: IconFire,
  earth: IconEarth,
  air: IconAir,
  water: IconWater,
};
const ELEMENT_COLORS: Record<string, string> = {
  fire: "#ff6b6b",
  earth: "#3dd68c",
  air: "#b08ef0",
  water: "#8bb8f0",
};

const ELEMENTS: Record<string, { label: string; signs: string[] }> = {
  fire: { label: "Огонь", signs: ["Aries", "Leo", "Sagittarius"] },
  earth: { label: "Земля", signs: ["Taurus", "Virgo", "Capricorn"] },
  air: { label: "Воздух", signs: ["Gemini", "Libra", "Aquarius"] },
  water: { label: "Вода", signs: ["Cancer", "Scorpio", "Pisces"] },
};

const SIGN_TRAITS: Record<string, string[]> = {
  Aries: [
    "Смелый",
    "Энергичный",
    "Лидер",
    "Импульсивный",
    "Прямолинейный",
    "Нетерпеливый",
  ],
  Taurus: [
    "Стабильный",
    "Чувственный",
    "Практичный",
    "Верный",
    "Упрямый",
    "Надёжный",
  ],
  Gemini: [
    "Общительный",
    "Любознательный",
    "Остроумный",
    "Переменчивый",
    "Адаптивный",
    "Двойственный",
  ],
  Cancer: [
    "Заботливый",
    "Интуитивный",
    "Эмоциональный",
    "Защитник",
    "Домашний",
    "Чувствительный",
  ],
  Leo: [
    "Харизматичный",
    "Творческий",
    "Щедрый",
    "Гордый",
    "Драматичный",
    "Вдохновляющий",
  ],
  Virgo: [
    "Аналитичный",
    "Практичный",
    "Трудолюбивый",
    "Скромный",
    "Перфекционист",
    "Внимательный",
  ],
  Libra: [
    "Гармоничный",
    "Дипломатичный",
    "Справедливый",
    "Эстетичный",
    "Нерешительный",
    "Обаятельный",
  ],
  Scorpio: [
    "Страстный",
    "Глубокий",
    "Проницательный",
    "Сильный",
    "Магнетичный",
    "Трансформатор",
  ],
  Sagittarius: [
    "Свободный",
    "Оптимист",
    "Философ",
    "Искатель",
    "Честный",
    "Авантюрный",
  ],
  Capricorn: [
    "Амбициозный",
    "Дисциплинированный",
    "Терпеливый",
    "Ответственный",
    "Стратег",
    "Серьёзный",
  ],
  Aquarius: [
    "Оригинальный",
    "Независимый",
    "Гуманист",
    "Визионер",
    "Бунтарь",
    "Прогрессивный",
  ],
  Pisces: [
    "Интуитивный",
    "Мечтательный",
    "Сострадательный",
    "Творческий",
    "Эмпатичный",
    "Мистический",
  ],
};

// ── Planet symbols ──────────────────────────────────────────────────────────
const PLANET_SYMBOLS: Record<string, string> = {
  sun: "☉",
  moon: "☽",
  mercury: "☿",
  venus: "♀",
  mars: "♂",
  jupiter: "♃",
  saturn: "♄",
  uranus: "♅",
  neptune: "♆",
  pluto: "♇",
};

const PLANET_ROWS = [
  {
    key: "sun",
    name: "Солнце",
    symbol: "☉",
    desc: "Ядро личности, творческая сила",
    tone: "sun",
  },
  {
    key: "moon",
    name: "Луна",
    symbol: "☽",
    desc: "Эмоции, интуиция, подсознание",
    tone: "moon",
  },
  {
    key: "mercury",
    name: "Меркурий",
    symbol: "☿",
    desc: "Мышление, коммуникация",
    tone: "mercury",
  },
  {
    key: "venus",
    name: "Венера",
    symbol: "♀",
    desc: "Любовь, ценности, красота",
    tone: "venus",
  },
  {
    key: "mars",
    name: "Марс",
    symbol: "♂",
    desc: "Энергия, действие, желание",
    tone: "mars",
  },
  {
    key: "jupiter",
    name: "Юпитер",
    symbol: "♃",
    desc: "Удача, рост, философия",
    tone: "jupiter",
  },
  {
    key: "saturn",
    name: "Сатурн",
    symbol: "♄",
    desc: "Дисциплина, уроки, структура",
    tone: "saturn",
  },
];

const PLANET_RU: Record<string, string> = {
  sun: "Солнце",
  moon: "Луна",
  mercury: "Меркурий",
  venus: "Венера",
  mars: "Марс",
  jupiter: "Юпитер",
  saturn: "Сатурн",
  uranus: "Уран",
  neptune: "Нептун",
  pluto: "Плутон",
};

const CATEGORY_RU: Record<string, string> = {
  personality: "Личность",
  emotion: "Эмоции",
  communication: "Общение",
  love: "Любовь",
  career: "Действие",
};

export function Natal() {
  const { user, setScreen } = useAppStore();
  const hasBirthData = !!user?.birth_city;
  const [tab, setTab] = useState<NatalTab>("circle");

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["natal-summary"],
    queryFn: natalApi.getSummary,
    enabled: hasBirthData,
    staleTime: 1000 * 60 * 10,
  });

  const { data: full, isLoading: fullLoading } = useQuery({
    queryKey: ["natal-full"],
    queryFn: natalApi.getFull,
    enabled: hasBirthData && (summary?.has_chart ?? false),
    staleTime: 1000 * 60 * 60,
  });

  const sunSign = summary?.sun_sign ?? user?.sun_sign;
  const userSign = ZODIAC_SIGNS.find((s) => s.value === sunSign);
  const interpretationSlides = useMemo<NatalInterpretationSlide[]>(() => {
    if (!full) return [];

    const readingSlides =
      full.reading
        ? parseReadingSections(full.reading).map((section, index) => {
            const title = section.title || "Вступление";
            return {
              id: `reading-${index}`,
              label: title,
              title,
              body: section.body,
            };
          })
        : [];

    const planetSlides =
      full.interpretations?.map((interp, index) => {
        const symbol = PLANET_SYMBOLS[interp.planet] ?? "✦";
        const planet = PLANET_RU[interp.planet] ?? interp.planet;
        const category = CATEGORY_RU[interp.category] ?? interp.category;
        const title = `${symbol} ${planet} · ${category}`;

        return {
          id: `interp-${interp.planet}-${interp.category}-${index}`,
          label: title,
          title,
          body: interp.text,
        };
      }) ?? [];

    return [...readingSlides, ...planetSlides].filter((slide) =>
      slide.body.trim(),
    );
  }, [full]);

  return (
    <div className="screen natal-screen">
      <div className="screen-header">
        <h2 className="screen-title">Натальная карта</h2>
      </div>

      <div className="screen-content">
        {!hasBirthData ? (
          <motion.div
            className="empty-state"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <svg
              className="empty-state__illustration"
              width="80"
              height="80"
              viewBox="0 0 80 80"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <circle
                cx="40"
                cy="40"
                r="38"
                stroke="currentColor"
                strokeWidth="1"
                strokeDasharray="4 3"
                opacity="0.2"
              />
              <circle
                cx="40"
                cy="40"
                r="26"
                stroke="currentColor"
                strokeWidth="1"
                opacity="0.3"
              />
              <circle
                cx="40"
                cy="40"
                r="14"
                stroke="currentColor"
                strokeWidth="1.2"
                opacity="0.5"
              />
              <circle cx="40" cy="40" r="3" fill="currentColor" opacity="0.6" />
              <line
                x1="40"
                y1="2"
                x2="40"
                y2="14"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
                opacity="0.5"
              />
              <line
                x1="40"
                y1="66"
                x2="40"
                y2="78"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
                opacity="0.5"
              />
              <line
                x1="2"
                y1="40"
                x2="14"
                y2="40"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
                opacity="0.5"
              />
              <line
                x1="66"
                y1="40"
                x2="78"
                y2="40"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
                opacity="0.5"
              />
              <circle
                cx="60"
                cy="20"
                r="4"
                stroke="currentColor"
                strokeWidth="1"
                opacity="0.4"
              />
              <circle
                cx="20"
                cy="60"
                r="3"
                stroke="currentColor"
                strokeWidth="1"
                opacity="0.3"
              />
              <circle cx="20" cy="20" r="2" fill="currentColor" opacity="0.3" />
            </svg>
            <h3 className="empty-state__title">Добавьте данные рождения</h3>
            <p className="empty-state__desc">
              Для расчёта натальной карты нужны
              <br />
              дата, время и город рождения
            </p>
            <button
              className="btn-primary"
              onClick={() => setScreen("profile")}
            >
              Указать данные
            </button>
          </motion.div>
        ) : (
          <>
            {/* ── Tab bar ── */}
            <div className="natal-tabs" role="tablist">
              {NATAL_TABS.map((t) => (
                <button
                  key={t.key}
                  type="button"
                  role="tab"
                  className={`natal-tab${tab === t.key ? " is-active" : ""}`}
                  onClick={() => setTab(t.key)}
                  aria-selected={tab === t.key}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Basic (free) — sun/moon/ascendant */}
            {summaryLoading ? (
              <NatalBasicSkeleton />
            ) : (
              <>
                {/* ── Natal Chart Wheel ── */}
                {tab === "circle" &&
                  summary &&
                  (() => {
                    const chartData = toNatalChartData(summary);
                    if (!chartData) return null;
                    return (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.5 }}
                        style={{ padding: "0 4px" }}
                      >
                        <NatalChart data={chartData} theme="midnight-gold" />
                      </motion.div>
                    );
                  })()}

                {/* ── Elements distribution ── */}
                {tab === "elements" &&
                  summary?.sun_sign &&
                  (() => {
                    const planets = [
                      summary.sun_sign,
                      summary.moon_sign,
                      summary.ascendant_sign,
                    ].filter(Boolean) as string[];
                    return (
                      <div className="natal-elements">
                        {Object.entries(ELEMENTS).map(([key, el]) => {
                          const count = planets.filter((p) =>
                            el.signs.includes(p),
                          ).length;
                          const Icon = ELEMENT_ICONS[key];
                          const color = ELEMENT_COLORS[key];
                          return (
                            <div
                              key={key}
                              className="natal-element-card"
                              style={{ color }}
                            >
                              <span className="natal-element-card__icon">
                                <Icon />
                              </span>
                              <span className="natal-element-card__label">
                                {el.label}
                              </span>
                              <span className="natal-element-card__count">
                                {count}/{planets.length}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })()}

                {/* ── Personality traits ── */}
                {tab === "elements" &&
                  summary?.sun_sign &&
                  SIGN_TRAITS[summary.sun_sign] && (
                    <div className="natal-traits">
                      {SIGN_TRAITS[summary.sun_sign].map((trait) => (
                        <span key={trait} className="natal-trait-pill">
                          {trait}
                        </span>
                      ))}
                    </div>
                  )}

                {tab === "circle" && (
                  <motion.div
                    className="natal-card natal-card--basic"
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <div className="natal-card__tag">✦ Базовый портрет</div>
                    <div className="natal-sign-row">
                      <span className="natal-sign-badge">
                        {userSign?.emoji ?? "☉"}
                      </span>
                      <div>
                        <div className="natal-sign-name">
                          {userSign?.label ?? toRu(sunSign)}
                        </div>
                        <div className="natal-sign-dates">
                          {userSign?.dates}
                        </div>
                      </div>
                    </div>
                    <div className="natal-chips">
                      {summary?.moon_sign && (
                        <div className="natal-chip">
                          <span className="natal-chip__symbol">☽</span>
                          <div>
                            <div className="natal-chip__label">Луна</div>
                            <div className="natal-chip__value">
                              {toRu(summary.moon_sign)}
                            </div>
                          </div>
                        </div>
                      )}
                      {summary?.ascendant_sign && (
                        <div className="natal-chip">
                          <span className="natal-chip__symbol">AC</span>
                          <div>
                            <div className="natal-chip__label">Асцендент</div>
                            <div className="natal-chip__value">
                              {toRu(summary.ascendant_sign)}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                    {summary?.birth_city && (
                      <div className="natal-location">
                        <span className="natal-location__symbol">◎</span>
                        <div>
                          <div className="natal-location__city">
                            {summary.birth_city}
                          </div>
                          {summary?.birth_lat != null &&
                            summary?.birth_lng != null && (
                              <div className="natal-location__coords">
                                {summary.birth_lat.toFixed(2)}°{" "}
                                {summary.birth_lat >= 0 ? "с.ш." : "ю.ш."}
                                {"  "}
                                {summary.birth_lng.toFixed(2)}°{" "}
                                {summary.birth_lng >= 0 ? "в.д." : "з.д."}
                              </div>
                            )}
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
              </>
            )}

            {/* Full natal — premium */}
            <PremiumGate
              locked={false}
              productId="natal_full"
              productName="Полная натальная карта"
              stars={150}
            >
              <motion.div
                className="natal-card natal-card--full"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                {tab === "planets" && fullLoading && (
                  <div className="natal-loading">Вычисление планет...</div>
                )}
                {tab === "planets" && !fullLoading && full && (
                  <div className="natal-planets">
                    <div className="natal-planets-hero">
                      <div className="natal-planets-hero__copy">
                        <div className="natal-card__tag">✦ Полная карта</div>
                        <p className="natal-planets-hero__count">
                          {PLANET_ROWS.length} планет отображено
                        </p>
                      </div>
                      <div
                        className="natal-planets-hero__wheel"
                        aria-hidden="true"
                      >
                        <span>♓</span>
                        <span>♎</span>
                        <span>♏</span>
                        <span>♌</span>
                        <span>♍</span>
                        <span>♐</span>
                        <div className="natal-planets-hero__sun">☉</div>
                      </div>
                    </div>

                    <div className="natal-planet-list">
                      {PLANET_ROWS.map((row) => {
                        const planet = full.planets?.[row.key];
                        const signText = planet
                          ? `${planet.sign_ru} ${Math.floor(planet.sign_degree)}°${planet.retrograde ? " ℞" : ""} • Дом ${planet.house}`
                          : "—";
                        return (
                          <div
                            key={row.key}
                            className={`natal-planet-card natal-planet-card--${row.tone}`}
                          >
                            <div className="natal-planet-orb" aria-hidden="true">
                              <span className="natal-planet-orb__symbol">
                                {row.symbol}
                              </span>
                            </div>
                            <div className="natal-planet-main">
                              <div className="natal-planet-name">{row.name}</div>
                              <div className="natal-planet-meta">{signText}</div>
                              <div className="natal-planet-desc">{row.desc}</div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                {tab === "planets" && !fullLoading && !full && (
                  <div className="natal-loading">
                    Нет данных — добавьте дату рождения
                  </div>
                )}

                {/* Personal interpretation slider */}
                {tab === "elements" && interpretationSlides.length > 0 && (
                  <div className="natal-reading">
                    <div
                      className="natal-card__tag"
                      style={{ marginTop: "1.25rem" }}
                    >
                      ✦ Персональная интерпретация
                    </div>
                    <NatalInterpretationSlider slides={interpretationSlides} />
                  </div>
                )}

                {/* Aspects table */}
                {tab === "aspects" &&
                  full?.aspects &&
                  full.aspects.length > 0 && (
                    <div className="natal-aspects">
                      <div
                        className="natal-card__tag"
                        style={{ marginTop: "1.25rem" }}
                      >
                        ✦ Аспекты
                      </div>
                      {[
                        "conjunction",
                        "trine",
                        "sextile",
                        "square",
                        "opposition",
                        "quincunx",
                      ].map((type) => {
                        const group = full.aspects.filter(
                          (a: any) => a.aspect === type,
                        );
                        if (group.length === 0) return null;
                        const symbols: Record<string, string> = {
                          conjunction: "☌",
                          trine: "△",
                          sextile: "⚹",
                          square: "□",
                          opposition: "☍",
                          quincunx: "⚻",
                        };
                        const names: Record<string, string> = {
                          conjunction: "Соединение",
                          trine: "Трин",
                          sextile: "Секстиль",
                          square: "Квадрат",
                          opposition: "Оппозиция",
                          quincunx: "Квинконс",
                        };
                        return (
                          <div key={type} className="natal-aspect-group">
                            <div className="natal-aspect-group__title">
                              <span className="natal-aspect-group__symbol">
                                {symbols[type]}
                              </span>
                              {names[type]}
                            </div>
                            {group.map((a: any, i: number) => (
                              <div key={i} className="natal-aspect-row">
                                <span>{PLANET_SYMBOLS[a.p1] ?? a.p1}</span>
                                <span className="natal-aspect-row__sym">
                                  {symbols[type]}
                                </span>
                                <span>{PLANET_SYMBOLS[a.p2] ?? a.p2}</span>
                                <span className="natal-aspect-row__orb">
                                  {a.orb.toFixed(1)}°
                                </span>
                              </div>
                            ))}
                          </div>
                        );
                      })}
                    </div>
                  )}

                {/* House cusps */}
                {tab === "houses" && full?.houses && full.houses.length > 0 && (
                  <div className="natal-houses">
                    <div className="natal-houses-hero">
                      <div className="natal-houses-hero__copy">
                        <div className="natal-card__tag">✦ Куспиды домов</div>
                        <p className="natal-houses-hero__count">
                          {full.houses.length} домов гороскопа
                        </p>
                      </div>
                      <div className="natal-houses-hero__wheel" aria-hidden="true">
                        {ZODIAC_WHEEL_GLYPHS.map((glyph) => (
                          <span key={glyph}>{glyph}</span>
                        ))}
                        <div className="natal-houses-hero__sun">☉</div>
                      </div>
                    </div>

                    <div className="natal-houses-grid">
                      {full.houses.map((h: any) => {
                        const signKey = String(h.sign ?? "").toLowerCase();
                        const signRu =
                          SIGN_EN_TO_RU[
                            h.sign?.charAt(0).toUpperCase() + h.sign?.slice(1)
                          ] ??
                          h.sign_ru ??
                          h.sign;
                        const deg = h.degree ?? 0;
                        const signDeg = deg % 30;
                        const d = Math.floor(signDeg);
                        const m = Math.floor((signDeg - d) * 60);
                        const axisLabel = HOUSE_AXIS_LABELS[h.number];
                        const glyph = ZODIAC_GLYPHS[signKey] ?? "✦";
                        const tone = ZODIAC_TONES[signKey] ?? "gold";
                        return (
                          <div
                            key={h.number}
                            className={`natal-house-card natal-house-card--${tone}${
                              axisLabel ? " natal-house-card--axis" : ""
                            }`}
                          >
                            <span className="natal-house-card__num">
                              {h.number}
                            </span>
                            <span className="natal-house-card__glyph" aria-hidden="true">
                              {glyph}
                            </span>
                            <span className="natal-house-card__sign">
                              {signRu}
                            </span>
                            <span className="natal-house-card__deg">
                              {d}°{m.toString().padStart(2, "0")}'
                            </span>
                            {axisLabel && (
                              <span className="natal-house-card__axis">
                                {axisLabel}
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                {/* Download PDF button */}
                {full && (
                  <motion.button
                    className="btn-secondary btn-with-icon"
                    style={{ marginTop: 20 }}
                    onClick={() => natalApi.downloadPdf()}
                    whileTap={{ scale: 0.96 }}
                  >
                    <svg
                      width="15"
                      height="15"
                      viewBox="0 0 15 15"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M7.5 1.5v9M3.5 7.5l4 4 4-4M2 13h11" />
                    </svg>
                    Скачать полный отчёт (PDF)
                  </motion.button>
                )}
              </motion.div>
            </PremiumGate>
          </>
        )}
      </div>
    </div>
  );
}
