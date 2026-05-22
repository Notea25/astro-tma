import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { EnergyBars } from "@/components/ui/EnergyBars";
import { PremiumGate } from "@/components/ui/PremiumGate";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { HoroscopeSkeleton, MoonCardSkeleton } from "@/components/ui/Skeleton";
import { MeaningText } from "@/components/ui/MeaningText";
import { HeaderAvatarButton } from "@/components/ui/HeaderAvatarButton";
import { horoscopeApi, tarotApi } from "@/services/api";
import { useAppStore } from "@/stores/app";
import { useHaptic } from "@/hooks/useTelegram";
import { useEntitlementChecker } from "@/hooks/useEntitlement";
import { ZODIAC_SIGNS } from "@/types";

const POWER_EMOJIS: Record<string, string[]> = {
  aries: ["🔥", "⚡", "🗡️", "🏆", "🚀", "💥"],
  taurus: ["🌿", "💎", "🍯", "🏔️", "🌸", "💰"],
  gemini: ["🦋", "💬", "📚", "🎭", "✨", "🌀"],
  cancer: ["🌙", "🏠", "💧", "🐚", "🌊", "💫"],
  leo: ["☀️", "👑", "🦁", "🔥", "💛", "⭐"],
  virgo: ["🌾", "💚", "📋", "🌿", "🔬", "✅"],
  libra: ["⚖️", "🌹", "💎", "🎨", "💕", "🕊️"],
  scorpio: ["🦂", "🔮", "🌑", "💀", "🖤", "🌌"],
  sagittarius: ["🏹", "🌍", "🔥", "🗺️", "🐎", "🎯"],
  capricorn: ["🏔️", "⛰️", "🧱", "💼", "🪨", "🏗️"],
  aquarius: ["💡", "🌐", "⚡", "🔭", "🛸", "🌈"],
  pisces: ["🐟", "🌊", "💜", "🔮", "🎵", "🌙"],
};

function getPowerEmoji(sign?: string): string {
  if (!sign) return "✨";
  const emojis = POWER_EMOJIS[sign.toLowerCase()] ?? ["✨"];
  const dayOfYear = Math.floor(
    (Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) /
      86400000,
  );
  return emojis[dayOfYear % emojis.length];
}

type Period = "today" | "tomorrow" | "week" | "month";

const PERIOD_LABELS: Record<Period, string> = {
  today: "Сегодня",
  tomorrow: "Завтра",
  week: "Неделя",
  month: "Месяц",
};
const PERIOD_PRODUCTS: Record<
  Exclude<Period, "today">,
  { id: string; stars: number }
> = {
  tomorrow: { id: "horoscope_tomorrow", stars: 25 },
  week: { id: "horoscope_week", stars: 50 },
  month: { id: "horoscope_month", stars: 75 },
};

export function Home() {
  const { user, setScreen } = useAppStore();
  const { impact } = useHaptic();
  const [period, setPeriod] = useState<Period>("today");
  const [cardRevealed, setCardRevealed] = useState(false);

  const signInfo = ZODIAC_SIGNS.find((s) => s.value === user?.sun_sign);
  const isEntitled = useEntitlementChecker();

  const { data: horoscope, isLoading } = useQuery({
    queryKey: ["horoscope", period, user?.id],
    queryFn: () =>
      period === "today"
        ? horoscopeApi.getToday()
        : horoscopeApi.getPeriod(period),
    staleTime: 1000 * 60 * 30,
  });

  const { data: moon, isLoading: moonLoading } = useQuery({
    queryKey: ["moon"],
    queryFn: horoscopeApi.getMoon,
    staleTime: 1000 * 60 * 60,
  });

  const {
    data: dailyCard,
    isLoading: cardLoading,
    isFetching: cardFetching,
    isError: cardError,
    refetch: refetchDailyCard,
  } = useQuery({
    queryKey: ["tarot-daily"],
    queryFn: () => tarotApi.draw("single"),
    enabled: cardRevealed,
    staleTime: 1000 * 60 * 60 * 12,
  });

  // Re-tick the clock every minute so the greeting flips at 5/12/17/23
  // even if the user keeps the home screen open across boundaries.
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);
  const greeting = (() => {
    const h = now.getHours();
    if (h < 5) return "Доброй ночи";
    if (h < 12) return "Доброе утро";
    if (h < 17) return "Добрый день";
    if (h < 23) return "Добрый вечер";
    return "Доброй ночи";
  })();

  const today = new Date().toLocaleDateString("ru-RU", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
  const openedDailyCard = dailyCard?.cards?.[0];

  return (
    <div className="screen home-screen">
      {/* Header */}
      <div className="screen-header home-header">
        <div>
          <h1 className="screen-greeting">
            {greeting}
            {user?.name ? `, ${user.name}` : ""}
          </h1>
          <p className="screen-date">{today}</p>
        </div>
        <HeaderAvatarButton />
      </div>

      {/* Period tabs */}
      <div className="period-tabs">
        {(["today", "tomorrow", "week", "month"] as Period[]).map((p) => (
          <button
            key={p}
            className={`period-tab ${period === p ? "active" : ""}`}
            onClick={() => {
              impact("light");
              setPeriod(p);
            }}
          >
            {PERIOD_LABELS[p]}
            {p !== "today" &&
              !isEntitled(
                PERIOD_PRODUCTS[p as Exclude<Period, "today">].id,
              ) && (
              <svg
                className="period-tab__lock"
                width="10"
                height="10"
                viewBox="0 0 10 10"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="1.5" y="4.5" width="7" height="5" rx="1" />
                <path d="M3 4.5V3a2 2 0 0 1 4 0v1.5" />
              </svg>
            )}
          </button>
        ))}
      </div>

      <div className="screen-content">
        {/* Horoscope card */}
        {isLoading ? (
          <HoroscopeSkeleton />
        ) : period === "today" ? (
          <motion.div
            key="today"
            className="horoscope-card glass-gold"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="card-tag">✦ Гороскоп на сегодня</div>
            <div className="card-sign-row">
              <div className="sign-badge">{signInfo?.emoji ?? "✦"}</div>
              <div>
                <div className="sign-name">{signInfo?.label ?? "Ваш знак"}</div>
                <div className="sign-dates">{signInfo?.dates}</div>
              </div>
            </div>
            <p className="horoscope-text">{horoscope?.text_ru}</p>
            {horoscope?.energy && <EnergyBars scores={horoscope.energy} />}
            <div className="power-emoji-row">
              <span className="power-emoji-row__icon">
                {getPowerEmoji(user?.sun_sign ?? undefined)}
              </span>
              <span className="power-emoji-row__text">Ваша энергия дня</span>
            </div>
          </motion.div>
        ) : (
          <PremiumGate
            productId={PERIOD_PRODUCTS[period as Exclude<Period, "today">].id}
            productName={`Гороскоп — ${PERIOD_LABELS[period]}`}
            stars={PERIOD_PRODUCTS[period as Exclude<Period, "today">].stars}
          >
            <motion.div
              key={period}
              className="horoscope-card glass-gold"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="card-tag">✦ {PERIOD_LABELS[period]}</div>
              <p className="horoscope-text">{horoscope?.text_ru}</p>
            </motion.div>
          </PremiumGate>
        )}

        {/* Moon card + Tarot daily — only on "today" tab. For tomorrow/week/month
            these blocks would show stale data (the backend has no period-aware
            moon/daily-card endpoints), so we hide them there. */}
        {period === "today" && moonLoading && <MoonCardSkeleton />}
        {period === "today" && moon && (
          <motion.div
            className="moon-card glass-purp"
            onClick={() => {
              impact("light");
              setScreen("moon");
            }}
            whileTap={{ scale: 0.98 }}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 }}
          >
            <span className="moon-card__emoji">{moon.emoji}</span>
            <div>
              <div className="moon-card__title">{moon.phase_name_ru}</div>
              <div className="moon-card__illum">
                Освещённость {Math.round(moon.illumination * 100)}%
              </div>
            </div>
            <svg
              className="moon-card__arrow"
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M6 3l5 5-5 5" />
            </svg>
          </motion.div>
        )}

        {/* Zodiac signs — horizontal scroll */}
        {period === "today" && (
          <section className="home-zodiac-section">
            <div className="home-zodiac-section__head">
              <h2 className="section-title">Знаки зодиака</h2>
              <button
                className="home-zodiac-section__more"
                onClick={() => {
                  impact("light");
                  setScreen("horoscopes");
                }}
              >
                Смотреть все
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 2l4 4-4 4" />
                </svg>
              </button>
            </div>
            <div className="zodiac-scroll">
              {ZODIAC_SIGNS.map((s) => (
                <button
                  key={s.value}
                  className={`zodiac-scroll__card ${user?.sun_sign === s.value ? "active" : ""}`}
                  onClick={() => {
                    impact("light");
                    setScreen("horoscopes");
                  }}
                >
                  <span className="zodiac-scroll__symbol">{s.emoji}</span>
                  <span className="zodiac-scroll__constellation" aria-hidden="true">
                    ✦ &nbsp;✦&nbsp; ✧ &nbsp;✦
                  </span>
                  <span className="zodiac-scroll__name">{s.label}</span>
                  <span className="zodiac-scroll__dates">{s.dates}</span>
                </button>
              ))}
            </div>
          </section>
        )}

        {/* Quick tiles — links to main practice screens */}
        {period === "today" && (
          <section className="home-tiles">
            <button
              className="home-tile"
              onClick={() => {
                impact("light");
                setScreen("moon");
              }}
            >
              <span className="home-tile__emoji" aria-hidden="true">🌙</span>
              <span className="home-tile__title">Лунный календарь</span>
              <span className="home-tile__desc">Фазы Луны и влияние дней</span>
              <span className="home-tile__arrow" aria-hidden="true">›</span>
            </button>
            <button
              className="home-tile"
              onClick={() => {
                impact("light");
                setScreen("natal");
              }}
            >
              <span className="home-tile__emoji" aria-hidden="true">✦</span>
              <span className="home-tile__title">Натальная карта</span>
              <span className="home-tile__desc">Расшифровка вашей карты рождения</span>
              <span className="home-tile__arrow" aria-hidden="true">›</span>
            </button>
            <button
              className="home-tile"
              onClick={() => {
                impact("light");
                setScreen("synastry_invite");
              }}
            >
              <span className="home-tile__emoji" aria-hidden="true">♥</span>
              <span className="home-tile__title">Совместимость</span>
              <span className="home-tile__desc">Сравните два знака</span>
              <span className="home-tile__arrow" aria-hidden="true">›</span>
            </button>
            <button
              className="home-tile"
              onClick={() => {
                impact("light");
                setScreen("tarot");
              }}
            >
              <span className="home-tile__emoji" aria-hidden="true">🎴</span>
              <span className="home-tile__title">Таро</span>
              <span className="home-tile__desc">Расклады и совет дня</span>
              <span className="home-tile__arrow" aria-hidden="true">›</span>
            </button>
          </section>
        )}

        {/* Tarot card of the day */}
        {period === "today" && (
        <motion.div
          className="tarot-day-card"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.14 }}
        >
          <div className="card-tag">✦ Карта таро на сегодня</div>
          <div className="tarot-flip">
            <motion.div
              key={cardRevealed ? "front" : "back"}
              className={`tarot-flip__inner ${
                cardRevealed ? "tarot-flip__inner--revealed" : ""
              }`}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.28, ease: "easeOut" }}
            >
              {!cardRevealed ? (
                <button
                  type="button"
                  className="tarot-flip__face tarot-flip__face--back"
                  onClick={() => {
                    impact("medium");
                    setCardRevealed(true);
                  }}
                >
                  <div className="tarot-flip__back-ornament" aria-hidden="true">
                    ✦
                  </div>
                  <span className="tarot-flip__hint">Нажмите, чтобы открыть</span>
                  <span className="tarot-flip__free">Бесплатно</span>
                </button>
              ) : (
                <div className="tarot-flip__face tarot-flip__face--front">
                  {cardLoading || cardFetching ? (
                    <div className="tarot-flip__loading">
                      <LoadingSpinner message="Карты открываются..." />
                    </div>
                  ) : cardError ? (
                    <div className="tarot-flip__empty">
                      <p className="tarot-flip__empty-title">Не удалось открыть карту</p>
                      <button
                        type="button"
                        className="tarot-flip__retry"
                        onClick={() => {
                          impact("light");
                          void refetchDailyCard();
                        }}
                      >
                        Повторить
                      </button>
                    </div>
                  ) : openedDailyCard ? (
                    <>
                      <div className="tarot-flip__img-wrap">
                        {openedDailyCard.image_url ? (
                          <img
                            src={openedDailyCard.image_url}
                            alt={openedDailyCard.name_ru}
                            className="tarot-flip__img"
                            loading="lazy"
                          />
                        ) : (
                          <div className="tarot-flip__img-fallback">
                            {openedDailyCard.emoji}
                          </div>
                        )}
                        <span
                          className={`tarot-flip__orientation ${
                            openedDailyCard.reversed
                              ? "tarot-flip__orientation--rev"
                              : ""
                          }`}
                        >
                          {openedDailyCard.reversed ? "↓ Перевёрнутое" : "↑ Прямое"}
                        </span>
                      </div>
                      <div className="tarot-flip__info">
                        <div className="tarot-flip__arcana">
                          {openedDailyCard.arcana === "major"
                            ? "Старший аркан"
                            : "Младший аркан"}
                        </div>
                        <div className="tarot-flip__name">
                          {openedDailyCard.name_ru}
                        </div>
                        <p className="tarot-flip__keywords">
                          {openedDailyCard.keywords_ru?.slice(0, 3).join(" · ")}
                        </p>
                        <MeaningText text={openedDailyCard.meaning_ru} compact />
                      </div>
                    </>
                  ) : (
                    <div className="tarot-flip__empty">
                      <p className="tarot-flip__empty-title">Карта пока не пришла</p>
                      <button
                        type="button"
                        className="tarot-flip__retry"
                        onClick={() => {
                          impact("light");
                          void refetchDailyCard();
                        }}
                      >
                        Открыть снова
                      </button>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          </div>
        </motion.div>
        )}
      </div>
    </div>
  );
}
