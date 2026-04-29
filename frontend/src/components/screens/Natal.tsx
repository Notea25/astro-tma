import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { PremiumGate } from "@/components/ui/PremiumGate";
import { NatalBasicSkeleton } from "@/components/ui/Skeleton";
import { useAppStore } from "@/stores/app";
import { natalApi } from "@/services/api";
import { ZODIAC_SIGNS } from "@/types";
import { NatalChart } from "@/components/NatalChart";
import { toNatalChartData } from "@/components/NatalChart/adapter";

type NatalTab = "circle" | "elements" | "planets" | "houses" | "aspects";
const NATAL_TABS: { key: NatalTab; label: string }[] = [
  { key: "circle", label: "Круг" },
  { key: "elements", label: "Стихии" },
  { key: "planets", label: "Планеты" },
  { key: "houses", label: "Дома" },
  { key: "aspects", label: "Аспекты" },
];

// Render LLM reading: split by **Section** markers into visual blocks
function ReadingBlocks({ text }: { text: string }) {
  // Remove leading # header line if present
  const cleaned = text.replace(/^#[^\n]*\n?/, "").trim();

  // Split into segments: ["intro text", "SectionTitle", "body", "SectionTitle", "body", ...]
  const parts = cleaned.split(/\*\*([^*]+)\*\*/);

  const blocks: { title?: string; body: string }[] = [];
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

  return (
    <div className="natal-reading-blocks">
      {blocks.map((block, idx) => (
        <div
          key={idx}
          className={
            block.title ? "natal-reading-section" : "natal-reading-intro"
          }
        >
          {block.title && (
            <div className="natal-reading-section__title">{block.title}</div>
          )}
          {block.body && (
            <p className="natal-reading-section__body">{block.body}</p>
          )}
        </div>
      ))}
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
  { key: "sun", label: "☉ Солнце", desc: "Ядро личности, творческая сила" },
  { key: "moon", label: "☽ Луна", desc: "Эмоции, интуиция, подсознание" },
  { key: "mercury", label: "☿ Меркурий", desc: "Мышление, коммуникация" },
  { key: "venus", label: "♀ Венера", desc: "Любовь, ценности, красота" },
  { key: "mars", label: "♂ Марс", desc: "Энергия, действие, желание" },
  { key: "jupiter", label: "♃ Юпитер", desc: "Удача, рост, философия" },
  { key: "saturn", label: "♄ Сатурн", desc: "Дисциплина, уроки, структура" },
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
                {tab === "planets" && (
                  <div className="natal-card__tag">✦ Полная карта</div>
                )}
                {tab === "planets" && fullLoading && (
                  <div className="natal-loading">Вычисление планет...</div>
                )}
                {tab === "planets" && !fullLoading && full && (
                  <div className="planet-table">
                    {PLANET_ROWS.map((row) => {
                      const planet = full.planets?.[row.key];
                      const signText = planet
                        ? `${planet.sign_ru} ${Math.floor(planet.sign_degree)}°${planet.retrograde ? " ℞" : ""} • Дом ${planet.house}`
                        : "—";
                      return (
                        <div key={row.key} className="planet-row">
                          <span className="planet-row__symbol">
                            {row.label}
                          </span>
                          <div>
                            <div className="planet-row__sign">{signText}</div>
                            <div className="planet-row__desc">{row.desc}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
                {tab === "planets" && !fullLoading && !full && (
                  <div className="natal-loading">
                    Нет данных — добавьте дату рождения
                  </div>
                )}

                {/* LLM Reading */}
                {tab === "elements" && full?.reading && (
                  <div className="natal-reading">
                    <div
                      className="natal-card__tag"
                      style={{ marginTop: "1.25rem" }}
                    >
                      ✦ Персональная интерпретация
                    </div>
                    <ReadingBlocks text={full.reading} />
                  </div>
                )}

                {/* Interpretations */}
                {tab === "elements" &&
                  full?.interpretations &&
                  full.interpretations.length > 0 && (
                    <div className="natal-interpretations">
                      <div
                        className="natal-card__tag"
                        style={{ marginTop: "1rem" }}
                      >
                        ✦ Интерпретации
                      </div>
                      {full.interpretations.map((interp, i) => (
                        <div key={i} className="natal-interp-item">
                          <div className="natal-interp-item__title">
                            {PLANET_SYMBOLS[interp.planet] ?? "✦"}{" "}
                            {PLANET_RU[interp.planet] ?? interp.planet} ·{" "}
                            {CATEGORY_RU[interp.category] ?? interp.category}
                          </div>
                          <p className="natal-interp-item__text">
                            {interp.text}
                          </p>
                        </div>
                      ))}
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

                {/* House cusps table */}
                {tab === "houses" && full?.houses && full.houses.length > 0 && (
                  <div className="natal-houses-table">
                    <div
                      className="natal-card__tag"
                      style={{ marginTop: "1.25rem" }}
                    >
                      ✦ Куспиды домов
                    </div>
                    <div className="natal-houses-grid">
                      {full.houses.map((h: any) => {
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
                        const axisLabel: Record<number, string> = {
                          1: "AC",
                          4: "IC",
                          7: "DC",
                          10: "MC",
                        };
                        return (
                          <div
                            key={h.number}
                            className={`natal-house-row${axisLabel[h.number] ? " natal-house-row--axis" : ""}`}
                          >
                            <span className="natal-house-row__num">
                              {h.number}
                            </span>
                            <span className="natal-house-row__sign">
                              {signRu}
                            </span>
                            <span className="natal-house-row__deg">
                              {d}°{m.toString().padStart(2, "0")}'
                            </span>
                            {axisLabel[h.number] && (
                              <span className="natal-house-row__axis">
                                {axisLabel[h.number]}
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
