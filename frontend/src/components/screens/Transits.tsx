import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { EnergyBars } from "@/components/ui/EnergyBars";
import { HoroscopeSkeleton } from "@/components/ui/Skeleton";
import { useAppStore } from "@/stores/app";
import { transitsApi } from "@/services/api";
import { ApiError } from "@/services/api";

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

export function Transits() {
  const { setScreen } = useAppStore();

  const { data, isLoading, error } = useQuery({
    queryKey: ["transits-current"],
    queryFn: transitsApi.getCurrent,
    staleTime: 1000 * 60 * 60 * 6,
    retry: false,
  });

  const noBirthData = error instanceof ApiError && error.status === 422;

  return (
    <div className="screen">
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

        {data && (
          <>
            <div className="horoscope-card">
              <div
                className="horoscope-card__period"
                style={{ marginBottom: 8 }}
              >
                Энергии дня по транзитам
              </div>
              <EnergyBars scores={data.energy} />
            </div>

            <div className="horoscope-card">
              <div
                className="horoscope-card__period"
                style={{ marginBottom: 12 }}
              >
                Активные аспекты
              </div>
              {data.aspects.length === 0 ? (
                <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>
                  Значимых аспектов сейчас нет.
                </p>
              ) : (
                <div className="transits-list">
                  {data.aspects.map((a, idx) => (
                    <motion.div
                      key={`${a.transit_planet}-${a.natal_planet}-${a.aspect}-${idx}`}
                      className="transit-row"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.04, duration: 0.3 }}
                    >
                      <span className="transit-row__planet">
                        {PLANET_GLYPH[a.transit_planet.toLowerCase()] ?? "●"}{" "}
                        {a.transit_planet_ru}
                      </span>
                      <span
                        className="transit-row__aspect"
                        style={{
                          color:
                            ASPECT_COLOR[a.aspect] ?? "var(--text-secondary)",
                        }}
                      >
                        {ASPECT_SYMBOL[a.aspect] ?? a.aspect_ru}
                      </span>
                      <span className="transit-row__planet">
                        {PLANET_GLYPH[a.natal_planet.toLowerCase()] ?? "●"}{" "}
                        {a.natal_planet_ru}
                      </span>
                      <span className="transit-row__orb">
                        {a.orb.toFixed(1)}°
                      </span>
                    </motion.div>
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
