import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { EnergyBars } from "@/components/ui/EnergyBars";
import { HoroscopeSkeleton } from "@/components/ui/Skeleton";
import { useAppStore } from "@/stores/app";
import { transitsApi } from "@/services/api";
import { ApiError } from "@/services/api";
import type { TransitAspect } from "@/types";

const ASPECT_COLOR: Record<string, string> = {
  conjunction: "#e8c97e",
  trine: "#8bc89b",
  sextile: "#7ec8e3",
  square: "#e88b8b",
  opposition: "#c58be8",
};

const ASPECT_SYMBOL: Record<string, string> = {
  conjunction: "☌",
  trine: "△",
  sextile: "⚹",
  square: "□",
  opposition: "☍",
};

const PLANET_GLYPH: Record<string, string> = {
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

const ZODIAC_SYMBOL: Record<string, string> = {
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

// Fast planets drive daily mood; slow planets drive long-term processes.
const FAST_PLANETS = new Set(["moon", "mercury", "venus", "mars", "sun"]);
// Neutral guidance about an aspect archetype
const ASPECT_HINT: Record<string, string> = {
  conjunction: "Слияние энергий — темы объединяются в одну.",
  trine: "Гармония и поддержка. Естественный поток.",
  sextile: "Возможность. Нужно сделать шаг, чтобы включить.",
  square: "Напряжение и вызов. Точка роста через сопротивление.",
  opposition: "Полярность. Баланс между двумя силами.",
};

function splitAspects(aspects: TransitAspect[]) {
  const fast: TransitAspect[] = [];
  const slow: TransitAspect[] = [];
  for (const a of aspects) {
    if (FAST_PLANETS.has(a.transit_planet.toLowerCase())) fast.push(a);
    else slow.push(a);
  }
  return { fast, slow };
}

function TransitCard({
  aspect,
  idx,
  retrograde,
}: {
  aspect: TransitAspect;
  idx: number;
  retrograde?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const color = ASPECT_COLOR[aspect.aspect] ?? "var(--text-secondary)";
  // Prefer server data; fall back to caller-supplied sky retrograde.
  const isRetro = aspect.transit_retrograde ?? retrograde ?? false;
  const applying = aspect.applying;

  return (
    <motion.button
      type="button"
      className="transit-card"
      onClick={() => setOpen((v) => !v)}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.04, duration: 0.3 }}
      aria-expanded={open}
    >
      <div className="transit-card__head">
        <span className="transit-card__planet">
          {PLANET_GLYPH[aspect.transit_planet.toLowerCase()] ?? "●"}
          {isRetro ? " ℞" : ""} {aspect.transit_planet_ru}
        </span>
        <span className="transit-card__aspect" style={{ color }}>
          {ASPECT_SYMBOL[aspect.aspect] ?? aspect.aspect_ru}
        </span>
        <span className="transit-card__planet">
          {PLANET_GLYPH[aspect.natal_planet.toLowerCase()] ?? "●"}{" "}
          {aspect.natal_planet_ru}
        </span>
        <span className="transit-card__orb">{aspect.orb.toFixed(1)}°</span>
      </div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            className="transit-card__body"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
          >
            <p>
              <strong style={{ color }}>
                {aspect.transit_planet_ru} {aspect.aspect_ru}{" "}
                {aspect.natal_planet_ru}
              </strong>{" "}
              — {ASPECT_HINT[aspect.aspect] ?? "Значимая конфигурация."}
            </p>
            {applying === true && (
              <p style={{ marginTop: 6, fontSize: 12, opacity: 0.85 }}>
                Аспект сходится — энергия нарастает, эффект будет усиливаться.
              </p>
            )}
            {applying === false && (
              <p style={{ marginTop: 6, fontSize: 12, opacity: 0.85 }}>
                Аспект расходится — пик пройден, энергия постепенно ослабевает.
              </p>
            )}
            {isRetro && (
              <p style={{ marginTop: 6, fontSize: 12, opacity: 0.8 }}>
                Планета ретроградна: эффект направлен внутрь — переосмысление,
                возврат к прошлым темам.
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.button>
  );
}

export function Transits() {
  const { setScreen } = useAppStore();
  const [introOpen, setIntroOpen] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["transits-current"],
    queryFn: transitsApi.getCurrent,
    staleTime: 1000 * 60 * 60 * 6,
    retry: false,
  });

  const noBirthData = error instanceof ApiError && error.status === 422;

  const split = data ? splitAspects(data.aspects) : null;
  const retroMap = new Set(
    Object.entries(data?.sky ?? {})
      .filter(([, p]) => p.retrograde)
      .map(([name]) => name.toLowerCase()),
  );

  return (
    <div className="screen transits-screen">
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
        <h2 className="screen-title">Транзиты</h2>
      </div>

      <div className="screen-content">
        {/* ── Explainer — collapsible ── */}
        <motion.button
          type="button"
          className="transit-intro"
          onClick={() => setIntroOpen((v) => !v)}
          aria-expanded={introOpen}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          <span className="transit-intro__chevron">
            {introOpen ? "▾" : "▸"}
          </span>
          <span className="transit-intro__title">Что такое транзиты?</span>
        </motion.button>
        <AnimatePresence initial={false}>
          {introOpen && (
            <motion.div
              className="transit-intro__body"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.25 }}
            >
              <p>
                Транзиты — это движение планет прямо сейчас относительно вашей
                натальной карты. Они показывают, какие темы разворачиваются в
                вашей жизни: где энергия поддерживает, где встречаете
                сопротивление, когда открыто окно возможностей.
              </p>
              <p>
                <strong>Быстрые</strong> транзиты (Луна, Меркурий, Венера, Марс)
                формируют настроение дня. <strong>Медленные</strong> (Юпитер,
                Сатурн и дальше) — долгие жизненные процессы, длящиеся месяцы и
                годы.
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {isLoading && <HoroscopeSkeleton />}

        {noBirthData && (
          <div
            className="horoscope-card"
            style={{ textAlign: "center", padding: "32px 20px" }}
          >
            <p style={{ marginBottom: 16, color: "var(--text-secondary)" }}>
              Заполните данные рождения, чтобы увидеть транзиты.
            </p>
            <button
              className="btn-primary"
              onClick={() => setScreen("profile")}
            >
              Перейти в профиль
            </button>
          </div>
        )}

        {error && !noBirthData && (
          <p
            style={{
              color: "var(--text-secondary)",
              textAlign: "center",
              padding: "20px",
            }}
          >
            Не удалось загрузить транзиты.
          </p>
        )}

        {data && split && (
          <>
            <div className="horoscope-card">
              <div
                className="horoscope-card__period"
                style={{ marginBottom: 8 }}
              >
                Энергии дня
              </div>
              <EnergyBars scores={data.energy} />
            </div>

            <div className="horoscope-card">
              <div
                className="horoscope-card__period"
                style={{ marginBottom: 4 }}
              >
                Сегодня
              </div>
              <p
                style={{
                  fontSize: 12,
                  color: "var(--text-secondary)",
                  marginBottom: 12,
                }}
              >
                Быстрые транзиты — настроение дня
              </p>
              {split.fast.length === 0 ? (
                <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>
                  Значимых быстрых аспектов сейчас нет.
                </p>
              ) : (
                <div className="transits-list">
                  {split.fast.map((a, idx) => (
                    <TransitCard
                      key={`${a.transit_planet}-${a.natal_planet}-${a.aspect}-${idx}`}
                      aspect={a}
                      idx={idx}
                      retrograde={retroMap.has(a.transit_planet.toLowerCase())}
                    />
                  ))}
                </div>
              )}
            </div>

            <div className="horoscope-card">
              <div
                className="horoscope-card__period"
                style={{ marginBottom: 4 }}
              >
                Этот период
              </div>
              <p
                style={{
                  fontSize: 12,
                  color: "var(--text-secondary)",
                  marginBottom: 12,
                }}
              >
                Медленные транзиты — долгие жизненные процессы
              </p>
              {split.slow.length === 0 ? (
                <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>
                  Значимых медленных аспектов сейчас нет.
                </p>
              ) : (
                <div className="transits-list">
                  {split.slow.map((a, idx) => (
                    <TransitCard
                      key={`${a.transit_planet}-${a.natal_planet}-${a.aspect}-${idx}`}
                      aspect={a}
                      idx={idx}
                      retrograde={retroMap.has(a.transit_planet.toLowerCase())}
                    />
                  ))}
                </div>
              )}
            </div>

            <div className="horoscope-card">
              <div
                className="horoscope-card__period"
                style={{ marginBottom: 12 }}
              >
                Небо сейчас
              </div>
              <div className="sky-grid">
                {Object.entries(data.sky).map(([planet, pos]) => (
                  <div key={planet} className="sky-cell">
                    <span className="sky-cell__glyph">
                      {PLANET_GLYPH[planet] ?? "●"}
                    </span>
                    <span className="sky-cell__sign">
                      {ZODIAC_SYMBOL[pos.sign] ?? ""} {pos.sign_ru}
                      {pos.retrograde && (
                        <span className="sky-cell__retro"> ℞</span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
