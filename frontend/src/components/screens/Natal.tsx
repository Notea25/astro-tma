import { type CSSProperties, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, type PanInfo } from "framer-motion";
import { PremiumGate } from "@/components/ui/PremiumGate";
import { NatalBasicSkeleton } from "@/components/ui/Skeleton";
import { useAppStore } from "@/stores/app";
import { ApiError, natalApi } from "@/services/api";
import {
  ZODIAC_SIGNS,
  type NatalFullResponse,
  type NatalSummaryResponse,
} from "@/types";
import { NatalChart, type NatalChartData } from "@/components/NatalChart";
import { toNatalChartData } from "@/components/NatalChart/adapter";
import styles from "./Natal.module.css";

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
  scorpio: "♏︎",
  sagittarius: "♐︎",
  capricorn: "♑︎",
  aquarius: "♒︎",
  pisces: "♓︎",
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
  s
    ? (SIGN_EN_TO_RU[s.charAt(0).toUpperCase() + s.slice(1).toLowerCase()] ??
      ZODIAC_SIGNS.find((sign) => sign.value === s.toLowerCase())?.label ??
      s)
    : "—";

function getPdfDownloadError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 402) {
      return "PDF доступен после покупки полной натальной карты.";
    }
    if (error.status === 422) {
      return "Для PDF нужны дата, время и город рождения.";
    }
    return error.message || "Не удалось подготовить PDF.";
  }

  return "Не удалось скачать PDF. Попробуйте ещё раз.";
}

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
      <path d="M12 21V8" />
      <path d="M12 8c-4.2.7-6.8 3.4-7.2 7.4 3.8.1 6.5-2.1 7.2-7.4Z" />
      <path d="M12 8c4.2.7 6.8 3.4 7.2 7.4-3.8.1-6.5-2.1-7.2-7.4Z" />
      <path d="M12 8c-.2-3 1.2-5.1 4.3-6.2.4 3.1-.9 5.2-4.3 6.2Z" opacity="0.72" />
      <path d="M8 18h8" opacity="0.56" />
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

const ELEMENT_ORDER = ["fire", "earth", "air", "water"];

const ELEMENT_META: Record<
  string,
  { subtitle: string; toneClass: string; accent: string }
> = {
  fire: {
    subtitle: "Энергия · Действие",
    toneClass: "fire",
    accent: "#ff8b66",
  },
  earth: {
    subtitle: "Стабильность · Тело",
    toneClass: "earth",
    accent: "#93ee82",
  },
  air: {
    subtitle: "Мысли · Общение",
    toneClass: "air",
    accent: "#bb7cff",
  },
  water: {
    subtitle: "Эмоции · Интуиция",
    toneClass: "water",
    accent: "#67c9ff",
  },
};

const TRAIT_ICONS = ["♧", "♒︎", "◉", "✧", "↺", "☄"];

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

const PLANET_ACCENTS: Record<string, string> = {
  sun: "#ffd36e",
  moon: "#b991ff",
  mercury: "#7ec5ff",
  venus: "#f37bd9",
  mars: "#ff8467",
  jupiter: "#b77cff",
  saturn: "#c58cff",
};

const PLANET_HERO_SYMBOLS = ["♄", "♆", "♃", "♇", "♀", "☉", "☿", "☽"];

const HOUSE_HERO_SYMBOLS = ["♑︎", "♓︎", "♈", "♏︎", "♎", "♐︎", "♉", "♊", "♋", "♌", "♍", "♎"];

const CATEGORY_RU: Record<string, string> = {
  personality: "Личность",
  emotion: "Эмоции",
  communication: "Общение",
  love: "Любовь",
  career: "Действие",
};

const ASPECT_ORDER = [
  "conjunction",
  "trine",
  "sextile",
  "square",
  "opposition",
  "quincunx",
];

const ASPECT_META: Record<
  string,
  { name: string; symbol: string; accent: string }
> = {
  conjunction: { name: "Соединение", symbol: "☌", accent: "#ff9b63" },
  trine: { name: "Трин", symbol: "△", accent: "#d47cff" },
  sextile: { name: "Секстиль", symbol: "✶", accent: "#c36cff" },
  square: { name: "Квадрат", symbol: "□", accent: "#8d96ff" },
  opposition: { name: "Оппозиция", symbol: "☍", accent: "#ff8467" },
  quincunx: { name: "Квинконс", symbol: "⚻", accent: "#8ec7ff" },
};

const POINT_SYMBOLS: Record<string, string> = {
  ascendant: "AC",
  descendant: "DC",
  medium_coeli: "MC",
  imum_coeli: "IC",
  true_north_lunar_node: "☊",
  true_south_lunar_node: "☋",
  mean_lilith: "⚸",
  chiron: "⚷",
};

const DATE_FORMATTER = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  timeZone: "UTC",
  year: "numeric",
});

const ELEMENT_TONE: Record<
  string,
  { adjective: string; description: string; color: string }
> = {
  fire: {
    adjective: "огненная",
    description: "Инициатива, импульс и смелость в действиях",
    color: "#ffb36a",
  },
  earth: {
    adjective: "земная",
    description: "Практичность, устойчивость и чувство формы",
    color: "#7de2a8",
  },
  air: {
    adjective: "воздушная",
    description: "Идеи, связи и лёгкость мышления",
    color: "#c7b2ff",
  },
  water: {
    adjective: "водная",
    description: "Интуиция, глубина и эмоциональная память",
    color: "#8ec7ff",
  },
};

const FOCUS_PHRASES: Record<string, string> = {
  Aries: "Фокус на смелом старте",
  Taurus: "Фокус на устойчивости",
  Gemini: "Фокус на ясном слове",
  Cancer: "Фокус на внутренней опоре",
  Leo: "Фокус на самовыражении",
  Virgo: "Фокус на точности",
  Libra: "Фокус на гармонии",
  Scorpio: "Фокус на трансформации",
  Sagittarius: "Фокус на расширении",
  Capricorn: "Фокус на стратегии",
  Aquarius: "Фокус на свободе мышления",
  Pisces: "Фокус на интуиции",
};

function normalizeSign(value: string | null | undefined): string {
  if (!value) return "";
  const lower = value.toLowerCase();
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

function signKey(value: string | null | undefined): string {
  return value?.toLowerCase() ?? "";
}

function formatBirthDate(value: string | null | undefined): string {
  if (!value) return "Дата рождения не указана";

  const [datePart] = value.split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  if (!year || !month || !day) return value;

  return DATE_FORMATTER.format(new Date(Date.UTC(year, month - 1, day)));
}

function formatBirthTime(
  value: string | null | undefined,
  known: boolean | null | undefined,
): string {
  if (!known) return "Время не указано";
  return value ? value.slice(0, 5) : "Время не указано";
}

function formatCoordinate(
  value: number,
  positiveLabel: "N" | "E",
  negativeLabel: "S" | "W",
): string {
  return `${Math.abs(value).toFixed(4)}° ${value >= 0 ? positiveLabel : negativeLabel}`;
}

function formatCoordinates(
  lat: number | null | undefined,
  lng: number | null | undefined,
): string {
  if (lat == null || lng == null) return "Координаты не указаны";
  return `${formatCoordinate(lat, "N", "S")} · ${formatCoordinate(lng, "E", "W")}`;
}

function formatDegreeFromParts(
  degree: number | null | undefined,
  minute: number | null | undefined,
): string {
  if (degree == null) return "—";
  return `${Math.floor(degree)}°${Math.floor(minute ?? 0)
    .toString()
    .padStart(2, "0")}'`;
}

function formatDegree(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  const normalized = ((value % 30) + 30) % 30;
  let degree = Math.floor(normalized);
  let minute = Math.round((normalized - degree) * 60);
  if (minute === 60) {
    degree = (degree + 1) % 30;
    minute = 0;
  }
  return `${degree}°${minute.toString().padStart(2, "0")}'`;
}

function formatDegreeShort(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${Math.round(((value % 30) + 30) % 30)}°`;
}

function titleFromPoint(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function pointSymbol(value: string): string {
  const key = value.toLowerCase();
  return PLANET_SYMBOLS[key] ?? POINT_SYMBOLS[key] ?? "✦";
}

function aspectDisplayName(value: string): string {
  const key = value.toLowerCase();
  return PLANET_RU[key] ?? titleFromPoint(value);
}

function getPlanetData(
  summary: NatalSummaryResponse | undefined,
  full: NatalFullResponse | undefined,
  planet: string,
): { sign?: string | null; sign_ru?: string; sign_degree?: number } | undefined {
  return full?.planets?.[planet] ?? summary?.planets?.[planet];
}

function getElementSummary(summary: NatalSummaryResponse | undefined): {
  key: string;
  label: string;
  text: string;
  description: string;
  color: string;
} {
  const signs = [
    summary?.sun_sign,
    summary?.moon_sign,
    summary?.ascendant_sign,
  ]
    .map(normalizeSign)
    .filter(Boolean);

  const fallback = ELEMENT_TONE.water;
  if (signs.length === 0) {
    return {
      key: "water",
      label: "Вода",
      text: `Сильная ${fallback.adjective} энергия`,
      description: fallback.description,
      color: fallback.color,
    };
  }

  const ranked = Object.entries(ELEMENTS)
    .map(([key, element]) => ({
      key,
      label: element.label,
      count: signs.filter((sign) => element.signs.includes(sign)).length,
    }))
    .sort((a, b) => b.count - a.count);

  const dominant = ranked[0] ?? { key: "water", label: "Вода" };
  const tone = ELEMENT_TONE[dominant.key] ?? fallback;

  return {
    key: dominant.key,
    label: dominant.label,
    text: `Сильная ${tone.adjective} энергия`,
    description: tone.description,
    color: tone.color,
  };
}

function IconDownload() {
  return (
    <svg width="25" height="25" viewBox="0 0 25 25" fill="none">
      <path
        d="M12.5 4.5v10M8.5 10.5l4 4 4-4M5.5 19.5h14"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function IconCalendarSmall() {
  return (
    <svg width="21" height="21" viewBox="0 0 24 24" fill="none">
      <rect x="4" y="5" width="16" height="15" rx="2" stroke="currentColor" strokeWidth="1.7" />
      <path d="M8 3v4M16 3v4M4 10h16" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function IconClockSmall() {
  return (
    <svg width="21" height="21" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.7" />
      <path d="M12 7v5l3 2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconPinSmall() {
  return (
    <svg width="21" height="21" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 21s7-6.1 7-12a7 7 0 1 0-14 0c0 5.9 7 12 7 12Z"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <circle cx="12" cy="9" r="2.4" stroke="currentColor" strokeWidth="1.7" />
    </svg>
  );
}

function IconGlobeSmall() {
  return (
    <svg width="21" height="21" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.7" />
      <path
        d="M3.5 12h17M12 3.5c2.1 2.1 3.2 5 3.2 8.5S14.1 18.4 12 20.5c-2.1-2.1-3.2-5-3.2-8.5S9.9 5.6 12 3.5Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

function IconDropSmall() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 3s6 6.8 6 11a6 6 0 0 1-12 0c0-4.2 6-11 6-11Z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function IconStarSmall() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path
        d="m12 3 2.7 5.7 6.3.8-4.6 4.4 1.2 6.1-5.6-3-5.6 3 1.2-6.1L3 9.5l6.3-.8L12 3Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function NatalTopBar() {
  return (
    <header className={styles.topBar}>
      <div className={styles.titleBlock}>
        <h1 className={styles.title}>Натальная карта</h1>
        <div className={styles.titleDivider} aria-hidden="true">
          <span />
          <b>✦</b>
          <span />
        </div>
      </div>

    </header>
  );
}

function NatalTabBar({
  tab,
  onChange,
}: {
  tab: NatalTab;
  onChange: (next: NatalTab) => void;
}) {
  return (
    <div className={styles.tabBar} role="tablist" aria-label="Разделы натальной карты">
      {NATAL_TABS.map((item) => (
        <button
          key={item.key}
          type="button"
          role="tab"
          className={`${styles.tabButton}${tab === item.key ? ` ${styles.tabButtonActive}` : ""}`}
          onClick={() => onChange(item.key)}
          aria-selected={tab === item.key}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

function NatalConstellation() {
  const stars = [
    { x: 21, y: 78, r: 3.4, glow: 8 },
    { x: 51, y: 35, r: 2.6, glow: 6 },
    { x: 86, y: 55, r: 2.9, glow: 7 },
    { x: 121, y: 21, r: 4.2, glow: 10 },
    { x: 160, y: 78, r: 3.2, glow: 8 },
    { x: 91, y: 86, r: 2.5, glow: 6 },
    { x: 56, y: 105, r: 2.4, glow: 5 },
    { x: 130, y: 108, r: 3.5, glow: 8 },
    { x: 146, y: 43, r: 1.9, glow: 5 },
  ];
  const dust = [
    [12, 44, 0.8],
    [33, 22, 0.9],
    [41, 94, 0.7],
    [69, 16, 0.7],
    [74, 70, 0.6],
    [104, 38, 0.8],
    [112, 91, 0.7],
    [139, 19, 0.8],
    [171, 53, 0.9],
    [176, 96, 0.7],
  ];

  return (
    <svg
      className={styles.constellation}
      viewBox="0 0 190 128"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <radialGradient id="natalConstellationMist" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.24" />
          <stop offset="58%" stopColor="currentColor" stopOpacity="0.08" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </radialGradient>
        <filter id="natalConstellationGlow" x="-40%" y="-45%" width="180%" height="190%">
          <feGaussianBlur stdDeviation="2.2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <ellipse
        cx="96"
        cy="65"
        rx="84"
        ry="46"
        fill="url(#natalConstellationMist)"
      />
      <path
        d="M21 78 51 35l35 20 35-34 25 22 14 35-30 30-39-22-35 19-35-27Z"
        stroke="currentColor"
        strokeWidth="1.18"
        opacity="0.72"
        strokeLinecap="round"
        strokeLinejoin="round"
        filter="url(#natalConstellationGlow)"
      />
      <path
        d="m51 35 40 51 30-65M86 55l5 31 69-8M56 105 86 55m0 0 60-12m-55 43 55-43m-16 65 16-65"
        stroke="currentColor"
        strokeWidth="0.78"
        opacity="0.38"
        strokeLinecap="round"
      />
      {dust.map(([x, y, r]) => (
        <circle
          key={`${x}-${y}`}
          cx={x}
          cy={y}
          r={r}
          fill="currentColor"
          opacity="0.5"
        />
      ))}
      {stars.map((star) => (
        <g key={`${star.x}-${star.y}`} filter="url(#natalConstellationGlow)">
          <circle
            cx={star.x}
            cy={star.y}
            r={star.glow}
            fill="currentColor"
            opacity="0.08"
          />
          <path
            d={`M${star.x - star.r * 2.3} ${star.y}H${star.x + star.r * 2.3}M${star.x} ${star.y - star.r * 2.3}V${star.y + star.r * 2.3}`}
            stroke="currentColor"
            strokeWidth="0.55"
            opacity="0.56"
            strokeLinecap="round"
          />
          <circle cx={star.x} cy={star.y} r={star.r} fill="currentColor" />
          <circle cx={star.x - star.r * 0.42} cy={star.y - star.r * 0.42} r={star.r * 0.28} fill="#fff6cf" opacity="0.72" />
        </g>
      ))}
    </svg>
  );
}

function DecorativeOrbit({
  symbols,
  variant,
}: {
  symbols: string[];
  variant: "planets" | "houses";
}) {
  return (
    <div
      className={`${styles.orbitArt} ${
        variant === "planets" ? styles.orbitArtPlanets : styles.orbitArtHouses
      }`}
      aria-hidden="true"
    >
      <div className={styles.orbitCore}>✦</div>
      {symbols.map((symbol, index) => (
        <span
          key={`${symbol}-${index}`}
          className={styles.orbitGlyph}
          style={{ "--orbit-angle": `${index * (360 / symbols.length)}deg` } as CSSProperties}
        >
          {symbol}
        </span>
      ))}
    </div>
  );
}

function NatalKeyChips({
  summary,
  full,
  chartData,
}: {
  summary: NatalSummaryResponse | undefined;
  full: NatalFullResponse | undefined;
  chartData: NatalChartData;
}) {
  const sun = getPlanetData(summary, full, "sun");
  const moon = getPlanetData(summary, full, "moon");
  const ascendantDegree =
    chartData.ascendant.degree != null
      ? formatDegreeFromParts(chartData.ascendant.degree, chartData.ascendant.minute)
      : "—";

  const chips = [
    {
      key: "asc",
      glyph: ZODIAC_GLYPHS[signKey(summary?.ascendant_sign)] ?? "AC",
      title: "ASC",
      sign: toRu(summary?.ascendant_sign),
      degree: ascendantDegree,
    },
    {
      key: "sun",
      glyph: "☉",
      title: "Sun",
      sign: sun?.sign_ru ?? toRu(sun?.sign ?? summary?.sun_sign),
      degree: formatDegree(sun?.sign_degree),
    },
    {
      key: "moon",
      glyph: "☽",
      title: "Moon",
      sign: moon?.sign_ru ?? toRu(moon?.sign ?? summary?.moon_sign),
      degree: formatDegree(moon?.sign_degree),
    },
  ];

  return (
    <div className={styles.keyChips}>
      {chips.map((chip) => (
        <div key={chip.key} className={styles.keyChip}>
          <span className={styles.keyChipGlyph} aria-hidden="true">
            {chip.glyph}
          </span>
          <span className={styles.keyChipText}>
            <b>{chip.title}</b>
            <span>{chip.sign}</span>
            <small>{chip.degree}</small>
          </span>
        </div>
      ))}
    </div>
  );
}

function NatalHeroCard({
  chartData,
  summary,
  full,
  userName,
}: {
  chartData: NatalChartData;
  summary: NatalSummaryResponse | undefined;
  full: NatalFullResponse | undefined;
  userName?: string | null;
}) {
  const displayName = userName?.trim() || "Моя карта";
  const ascendantSign = summary?.ascendant_sign;
  const sunSign = summary?.sun_sign;
  const subtitleSign = ascendantSign || sunSign;
  const subtitle = ascendantSign
    ? `${toRu(ascendantSign)} восходящий`
    : `${toRu(sunSign)} солнечный знак`;

  return (
    <section className={styles.heroCard} aria-label="Основная натальная карта">
      <div className={styles.heroAura} aria-hidden="true" />
      <NatalConstellation />

      <div className={styles.heroCopy}>
        <div className={styles.heroKicker}>
          <span aria-hidden="true">✦</span>
          <span>МОЯ КАРТА</span>
          <span aria-hidden="true">✦</span>
        </div>
        <h2 className={styles.personName}>{displayName}</h2>
        <div className={styles.ascLine}>
          <span aria-hidden="true">{ZODIAC_GLYPHS[signKey(subtitleSign)] ?? "☉"}</span>
          <span>{subtitle}</span>
        </div>
        <p className={styles.quote}>«Рождённый звёздами»</p>
      </div>

      <div className={styles.wheelStage}>
        <NatalChart
          data={{ ...chartData, name: displayName }}
          theme="onyx-gold"
          variant="reference-wheel"
          size={650}
          className={styles.wheel}
        />
      </div>

      <NatalKeyChips summary={summary} full={full} chartData={chartData} />
    </section>
  );
}

function NatalBirthDetails({
  summary,
}: {
  summary: NatalSummaryResponse | undefined;
}) {
  const element = getElementSummary(summary);
  const ascendant = summary?.ascendant_sign
    ? `Восходящий ${toRu(summary.ascendant_sign)}`
    : "Асцендент уточняется";
  const focus = FOCUS_PHRASES[normalizeSign(summary?.sun_sign)] ?? "Фокус на личной силе";

  return (
    <section className={styles.detailsCard} aria-label="Данные рождения и ключевые акценты">
      <div className={styles.birthRows}>
        <div className={styles.birthRow}>
          <IconCalendarSmall />
          <span>{formatBirthDate(summary?.birth_date)}</span>
        </div>
        <div className={styles.birthRow}>
          <IconClockSmall />
          <span>{formatBirthTime(summary?.birth_time, summary?.birth_time_known)}</span>
        </div>
        <div className={styles.birthRow}>
          <IconPinSmall />
          <span>{summary?.birth_city || "Город не указан"}</span>
        </div>
        <div className={styles.birthRow}>
          <IconGlobeSmall />
          <span>{formatCoordinates(summary?.birth_lat, summary?.birth_lng)}</span>
        </div>
        <div className={styles.timezone}>
          Часовой пояс: {summary?.birth_tz || "не указан"}
        </div>
      </div>

      <div className={styles.detailsDivider} aria-hidden="true" />

      <div className={styles.highlights}>
        <h3>Ключевые акценты</h3>
        <div className={styles.highlightRow}>
          <span aria-hidden="true">{ZODIAC_GLYPHS[signKey(summary?.ascendant_sign)] ?? "AC"}</span>
          <p>{ascendant}</p>
        </div>
        <div className={styles.highlightRow} style={{ color: element.color }}>
          <IconDropSmall />
          <p>{element.text}</p>
        </div>
        <div className={styles.highlightRow}>
          <IconStarSmall />
          <p>{focus}</p>
        </div>
      </div>
    </section>
  );
}

function NatalPdfCard({
  full,
  isDownloading,
  error,
  onDownload,
}: {
  full: NatalFullResponse | undefined;
  isDownloading: boolean;
  error: string | null;
  onDownload: () => void;
}) {
  if (!full) return null;

  return (
    <section className={styles.pdfCard}>
      <motion.button
        type="button"
        className={styles.pdfButton}
        onClick={onDownload}
        disabled={isDownloading}
        aria-busy={isDownloading}
        whileTap={{ scale: isDownloading ? 1 : 0.98 }}
      >
        <IconDownload />
        <span>{isDownloading ? "Готовим PDF..." : "Скачать полный отчёт (PDF)"}</span>
      </motion.button>
      {error && <p className={styles.downloadError}>{error}</p>}
    </section>
  );
}

function NatalNoChartCard({
  userSign,
  sunSign,
  summary,
}: {
  userSign: (typeof ZODIAC_SIGNS)[number] | undefined;
  sunSign: string | null | undefined;
  summary: NatalSummaryResponse | undefined;
}) {
  return (
    <motion.div
      className={styles.referencePanel}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className={styles.sectionKicker}>✦ Базовый портрет</div>
      <div className={styles.basicSignRow}>
        <span>{userSign?.emoji ?? "☉"}</span>
        <div>
          <h2>{userSign?.label ?? toRu(sunSign)}</h2>
          <p>{userSign?.dates}</p>
        </div>
      </div>
      <p className={styles.panelText}>
        Для полного круга нужны точные дома и положения планет. Проверьте дату,
        время и город рождения в профиле.
      </p>
      {summary?.birth_city && (
        <div className={styles.compactLocation}>
          <IconPinSmall />
          <span>{summary.birth_city}</span>
        </div>
      )}
    </motion.div>
  );
}

function NatalElementsPanel({
  summary,
  slides,
}: {
  summary: NatalSummaryResponse | undefined;
  slides: NatalInterpretationSlide[];
}) {
  const planets = [
    summary?.sun_sign,
    summary?.moon_sign,
    summary?.ascendant_sign,
  ]
    .map(normalizeSign)
    .filter(Boolean);
  const total = Math.max(planets.length, 1);

  return (
    <motion.div
      className={styles.elementsPage}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className={styles.sectionKicker}>✦ Баланс стихий</div>
      <div className={styles.elementGrid}>
        {ELEMENT_ORDER.map((key) => {
          const element = ELEMENTS[key];
          const count = planets.filter((planet) =>
            element.signs.includes(planet),
          ).length;
          const Icon = ELEMENT_ICONS[key];
          const tone = ELEMENT_TONE[key];
          const meta = ELEMENT_META[key];

          return (
            <article
              key={key}
              className={`${styles.elementCard} ${styles[`elementCard${meta.toneClass.charAt(0).toUpperCase()}${meta.toneClass.slice(1)}`]}`}
              style={{ color: meta?.accent ?? tone?.color ?? ELEMENT_COLORS[key] }}
            >
              <span className={styles.elementIcon} aria-hidden="true">
                <Icon />
              </span>
              <span className={styles.elementText}>
                <b>{element.label}</b>
                <small>{meta?.subtitle}</small>
                <strong>
                  {count} <span>/ {total}</span>
                </strong>
              </span>
            </article>
          );
        })}
      </div>

      {summary?.sun_sign && SIGN_TRAITS[normalizeSign(summary.sun_sign)] && (
        <div className={styles.traitCloud}>
          {SIGN_TRAITS[normalizeSign(summary.sun_sign)].map((trait, index) => (
            <span key={trait}>
              <b aria-hidden="true">{TRAIT_ICONS[index % TRAIT_ICONS.length]}</b>
              {trait}
            </span>
          ))}
        </div>
      )}

      <NatalInterpretationPanel slides={slides} />
    </motion.div>
  );
}

function NatalInterpretationPanel({
  slides,
}: {
  slides: NatalInterpretationSlide[];
}) {
  if (slides.length === 0) return null;

  return (
    <section className={styles.interpretationPanel}>
      <div className={styles.interpretationHeader}>
        <span aria-hidden="true">✦</span>
        <h2>Персональная интерпретация</h2>
        <span aria-hidden="true">✦</span>
      </div>
      <NatalInterpretationSlider slides={slides} />
    </section>
  );
}

function NatalPlanetsPanel({ full }: { full: NatalFullResponse }) {
  const visibleRows = PLANET_ROWS.filter((row) => full.planets?.[row.key]);

  return (
    <motion.div
      className={styles.planetsPage}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: "easeOut" }}
    >
      <section className={styles.planetsHero}>
        <div className={styles.panelHeroCopy}>
          <div className={styles.panelEyebrow}>Полная карта</div>
          <h2>{visibleRows.length} планет отображено</h2>
          <p>
            Ваш космический отпечаток — раскройте влияние планет на вашу
            личность и судьбу.
          </p>
        </div>
        <DecorativeOrbit symbols={PLANET_HERO_SYMBOLS} variant="planets" />
      </section>

      <div className={styles.planetList}>
        {visibleRows.map((row) => {
          const planet = full.planets[row.key];
          const accent = PLANET_ACCENTS[row.key] ?? "#ffd476";
          const signText = `${planet.sign_ru} ${formatDegreeShort(
            planet.sign_degree,
          )}${planet.retrograde ? " ℞" : ""} · Дом ${planet.house}`;

          return (
            <article
              key={row.key}
              className={styles.planetCard}
              style={{ color: accent }}
            >
              <span className={styles.planetOrb} aria-hidden="true">
                <span>{row.symbol}</span>
              </span>
              <span className={styles.planetCopy}>
                <h3>{row.name}</h3>
                <b>{signText}</b>
                <p>{row.desc}</p>
              </span>
              <span className={styles.cardArrow} aria-hidden="true">
                ›
              </span>
            </article>
          );
        })}
      </div>
    </motion.div>
  );
}

function NatalHousesPanel({ full }: { full: NatalFullResponse }) {
  return (
    <motion.div
      className={styles.housesPage}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: "easeOut" }}
    >
      <section className={styles.housesHero}>
        <div className={styles.panelHeroCopy}>
          <div className={styles.panelEyebrow}>Куспиды домов</div>
          <h2>12 домов гороскопа</h2>
        </div>
        <DecorativeOrbit symbols={HOUSE_HERO_SYMBOLS} variant="houses" />
      </section>

      <div className={styles.housesGrid}>
        {full.houses.map((house) => {
          const houseSignKey = signKey(house.sign);
          const signRu =
            SIGN_EN_TO_RU[normalizeSign(house.sign)] ??
            house.sign_ru ??
            house.sign;
          const axisLabel = HOUSE_AXIS_LABELS[house.number];
          const glyph = ZODIAC_GLYPHS[houseSignKey] ?? "✦";
          const tone = ZODIAC_TONES[houseSignKey] ?? "gold";

          return (
            <article
              key={house.number}
              className={`${styles.houseCard} ${axisLabel ? styles.houseCardAxis : ""}`}
              data-tone={tone}
            >
              <span className={styles.houseNumber}>{house.number}</span>
              <span className={styles.houseGlyph} aria-hidden="true">
                {glyph}
              </span>
              <span className={styles.houseCopy}>
                <b>{signRu}</b>
                <small>{formatDegree(house.degree)}</small>
                {axisLabel && <em>{axisLabel}</em>}
              </span>
            </article>
          );
        })}
      </div>
    </motion.div>
  );
}

function NatalAspectsPanel({ full }: { full: NatalFullResponse }) {
  return (
    <motion.section
      className={styles.aspectsPage}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: "easeOut" }}
    >
      <div className={styles.aspectsHeader}>
        <h2>
          <span aria-hidden="true">✷</span>
          Аспекты
          <span aria-hidden="true">✧</span>
        </h2>
        <p>Гармония и напряжение между планетами</p>
      </div>

      {full.aspects.length === 0 && (
        <div className={styles.loadingState}>Значимые аспекты не найдены.</div>
      )}

      <div className={styles.aspectGroups}>
        {ASPECT_ORDER.map((type) => {
          const group = full.aspects.filter((aspect) => aspect.aspect === type);
          const meta = ASPECT_META[type];
          if (!meta || group.length === 0) return null;

          return (
            <article
              key={type}
              className={styles.aspectGroup}
              style={{ color: meta.accent }}
            >
              <span className={styles.aspectIcon} aria-hidden="true">
                {meta.symbol}
              </span>
              <span className={styles.aspectContent}>
                <h3>{meta.name}</h3>
                <span className={styles.aspectRows}>
                  {group.map((aspect, index) => (
                    <span
                      key={`${aspect.p1}-${aspect.p2}-${index}`}
                      className={styles.aspectRow}
                    >
                      <span className={styles.aspectPair}>
                        <span>
                          <i aria-hidden="true">{pointSymbol(aspect.p1)}</i>
                          {aspectDisplayName(aspect.p1)}
                        </span>
                        <b>{meta.symbol}</b>
                        <span>
                          <i aria-hidden="true">{pointSymbol(aspect.p2)}</i>
                          {aspectDisplayName(aspect.p2)}
                        </span>
                      </span>
                      <span className={styles.aspectOrbValue}>
                        {aspect.orb.toFixed(1)}°
                      </span>
                    </span>
                  ))}
                </span>
              </span>
            </article>
          );
        })}
      </div>
    </motion.section>
  );
}

export function Natal() {
  const { user, setScreen } = useAppStore();
  const hasBirthData = !!user?.birth_city;
  const [tab, setTab] = useState<NatalTab>("circle");
  const [isPdfDownloading, setIsPdfDownloading] = useState(false);
  const [pdfDownloadError, setPdfDownloadError] = useState<string | null>(null);

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
  const chartData = useMemo(
    () => (summary ? toNatalChartData(summary) : null),
    [summary],
  );
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

  const handlePdfDownload = async () => {
    if (isPdfDownloading) return;

    setIsPdfDownloading(true);
    setPdfDownloadError(null);
    try {
      await natalApi.downloadPdf();
    } catch (error) {
      setPdfDownloadError(getPdfDownloadError(error));
    } finally {
      setIsPdfDownloading(false);
    }
  };

  const renderFullPanel = () => {
    if (fullLoading) {
      return (
        <motion.div
          className={styles.referencePanel}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className={styles.loadingState}>Вычисление полной карты...</div>
        </motion.div>
      );
    }

    if (!full) {
      return (
        <motion.div
          className={styles.referencePanel}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className={styles.loadingState}>
            Нет данных — проверьте дату, время и город рождения.
          </div>
        </motion.div>
      );
    }

    return (
      <PremiumGate
        locked={false}
        productId="natal_full"
        productName="Полная натальная карта"
        stars={150}
      >
        <>
          {tab === "planets" && <NatalPlanetsPanel full={full} />}
          {tab === "houses" && <NatalHousesPanel full={full} />}
          {tab === "aspects" && <NatalAspectsPanel full={full} />}
        </>
      </PremiumGate>
    );
  };

  const renderTabContent = () => {
    if (summaryLoading) {
      return (
        <div className={styles.skeletonPanel}>
          <NatalBasicSkeleton />
        </div>
      );
    }

    if (tab === "circle") {
      return (
        <>
          {chartData ? (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.42, ease: "easeOut" }}
            >
              <NatalHeroCard
                chartData={chartData}
                summary={summary}
                full={full}
                userName={user?.name}
              />
            </motion.div>
          ) : (
            <NatalNoChartCard
              userSign={userSign}
              sunSign={sunSign}
              summary={summary}
            />
          )}

          <NatalBirthDetails summary={summary} />
          <NatalPdfCard
            full={full}
            isDownloading={isPdfDownloading}
            error={pdfDownloadError}
            onDownload={handlePdfDownload}
          />
        </>
      );
    }

    if (tab === "elements") {
      return (
        <NatalElementsPanel summary={summary} slides={interpretationSlides} />
      );
    }

    return (
      <>
        {renderFullPanel()}
        <NatalPdfCard
          full={full}
          isDownloading={isPdfDownloading}
          error={pdfDownloadError}
          onDownload={handlePdfDownload}
        />
      </>
    );
  };

  return (
    <div className={`screen natal-screen ${styles.screen}`}>
      <div className={styles.sky} aria-hidden="true" />

      <div className={styles.content}>
        <NatalTopBar />

        {!hasBirthData ? (
          <motion.div
            className={styles.emptyState}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className={styles.emptyGlyph} aria-hidden="true">
              <NatalConstellation />
              <span>☉</span>
            </div>
            <h2>Добавьте данные рождения</h2>
            <p>
              Для расчёта натальной карты нужны дата, время и город рождения.
            </p>
            <button
              type="button"
              className={styles.primaryButton}
              onClick={() => setScreen("profile")}
            >
              Указать данные
            </button>
          </motion.div>
        ) : (
          <>
            <NatalTabBar tab={tab} onChange={setTab} />
            <div className={styles.tabContent}>
              {renderTabContent()}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
