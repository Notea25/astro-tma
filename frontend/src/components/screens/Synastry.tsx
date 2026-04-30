import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { PremiumGate } from "@/components/ui/PremiumGate";
import {
  CityAutocomplete,
  type CityOption,
} from "@/components/ui/CityAutocomplete";
import { useAppStore } from "@/stores/app";
import { compatibilityApi, synastryApi, ApiError } from "@/services/api";
import { useHaptic } from "@/hooks/useTelegram";
import type {
  CompatibilityResponse,
  SynastryResult,
  SynastryManualInput,
  ZodiacSign,
} from "@/types";

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

const ASPECT_SYMBOL: Record<string, string> = {
  conjunction: "☌",
  trine: "△",
  sextile: "⚹",
  square: "□",
  opposition: "☍",
};

const ASPECT_COLOR: Record<string, string> = {
  conjunction: "#e8c97e",
  trine: "#8bc89b",
  sextile: "#7ec8e3",
  square: "#e88b8b",
  opposition: "#c58be8",
};

const SPHERE_LABELS: { key: keyof SynastryResult["scores"]; label: string }[] =
  [
    { key: "overall", label: "Общая" },
    { key: "love", label: "Любовь" },
    { key: "communication", label: "Общение" },
    { key: "trust", label: "Доверие" },
    { key: "passion", label: "Страсть" },
  ];

type Mode = "pick" | "invite" | "manual";
type SynastryDisplayResult = SynastryResult & {
  fallbackCompatibility?: CompatibilityResponse;
};

const MIN_SYNASTRY_AGE = 14;

const TELEGRAM_BOT_USERNAME =
  ((import.meta.env.VITE_TELEGRAM_BOT_USERNAME as string | undefined) ??
    "astrologiyatut_bot")
    .trim()
    .replace(/^@/, "");

const INVALID_INVITE_BOT_USERNAMES = new Set([
  "astro_bot",
  "bot_username",
  "your_bot_username",
  "telegram_bot_username",
]);

function normalizeSynastryInviteUrl(url: string): string {
  if (!TELEGRAM_BOT_USERNAME) return url;

  try {
    const parsed = new URL(url);
    const isTelegramHost =
      parsed.hostname === "t.me" || parsed.hostname === "telegram.me";
    const parts = parsed.pathname.split("/").filter(Boolean);
    const botUsername = parts[0]?.toLowerCase();

    if (
      isTelegramHost &&
      botUsername &&
      INVALID_INVITE_BOT_USERNAMES.has(botUsername)
    ) {
      parts[0] = TELEGRAM_BOT_USERNAME;
      parsed.pathname = `/${parts.join("/")}`;
      return parsed.toString();
    }
  } catch {
    return url;
  }

  return url;
}

function normalizeBirthDateInput(value: string): string | null {
  const trimmed = value.trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return trimmed;

  const match = trimmed.match(/^(\d{1,2})[./](\d{1,2})[./](\d{4})$/);
  if (!match) return null;

  const [, day, month, year] = match;
  const dd = day.padStart(2, "0");
  const mm = month.padStart(2, "0");
  const normalized = `${year}-${mm}-${dd}`;
  const parsed = new Date(Date.UTC(Number(year), Number(mm) - 1, Number(dd)));

  if (
    Number.isNaN(parsed.getTime()) ||
    parsed.getUTCFullYear() !== Number(year) ||
    parsed.getUTCMonth() + 1 !== Number(mm) ||
    parsed.getUTCDate() !== Number(dd)
  ) {
    return null;
  }

  return normalized;
}

function formatBirthDateInput(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}.${digits.slice(2)}`;
  return `${digits.slice(0, 2)}.${digits.slice(2, 4)}.${digits.slice(4)}`;
}

function isBirthDateAtLeastAge(isoDate: string, minAge: number): boolean {
  const [year, month, day] = isoDate.split("-").map(Number);
  const birthDate = new Date(year, month - 1, day);
  const cutoff = new Date();
  cutoff.setFullYear(cutoff.getFullYear() - minAge);
  cutoff.setHours(0, 0, 0, 0);
  return birthDate <= cutoff;
}

function validatePartnerBirthDate(value: string): {
  normalizedDate: string | null;
  message: string | null;
} {
  const normalizedDate = normalizeBirthDateInput(value);
  if (!normalizedDate) {
    return {
      normalizedDate: null,
      message: "Введите дату рождения в формате ДД.ММ.ГГГГ.",
    };
  }

  if (!isBirthDateAtLeastAge(normalizedDate, MIN_SYNASTRY_AGE)) {
    return {
      normalizedDate: null,
      message: `Партнёру должно быть не меньше ${MIN_SYNASTRY_AGE} лет.`,
    };
  }

  return { normalizedDate, message: null };
}

function getZodiacSignFromDate(isoDate: string): ZodiacSign {
  const [, monthRaw, dayRaw] = isoDate.split("-").map(Number);
  const mmdd = monthRaw * 100 + dayRaw;

  if (mmdd >= 321 && mmdd <= 419) return "aries";
  if (mmdd >= 420 && mmdd <= 520) return "taurus";
  if (mmdd >= 521 && mmdd <= 620) return "gemini";
  if (mmdd >= 621 && mmdd <= 722) return "cancer";
  if (mmdd >= 723 && mmdd <= 822) return "leo";
  if (mmdd >= 823 && mmdd <= 922) return "virgo";
  if (mmdd >= 923 && mmdd <= 1022) return "libra";
  if (mmdd >= 1023 && mmdd <= 1121) return "scorpio";
  if (mmdd >= 1122 && mmdd <= 1221) return "sagittarius";
  if (mmdd >= 1222 || mmdd <= 119) return "capricorn";
  if (mmdd >= 120 && mmdd <= 218) return "aquarius";
  return "pisces";
}

function compatibilityToSynastryResult(
  result: CompatibilityResponse,
  initiatorName: string | null,
  partnerName: string,
): SynastryDisplayResult {
  return {
    aspects: [],
    scores: {
      love: result.love,
      communication: result.communication,
      trust: result.trust,
      passion: result.passion,
      overall: result.overall,
    },
    total_aspects: 0,
    initiator_name: initiatorName,
    partner_name: partnerName,
    fallbackCompatibility: result,
  };
}

function getManualSynastryErrorMessage(error: unknown): string | null {
  if (!error) return null;

  if (!(error instanceof ApiError)) {
    return "Не удалось отправить запрос. Проверьте соединение и попробуйте ещё раз.";
  }

  if (error.status === 401) {
    return "Сессия Telegram устарела. Закройте и снова откройте приложение.";
  }

  if (error.status === 402) return "Сначала купите Синастрию.";

  if (error.status === 422) {
    return error.message || "Проверьте дату, время и город рождения.";
  }

  if (error.message && error.message !== "Internal server error") {
    return error.message;
  }

  return "Не удалось рассчитать совместимость. Проверьте данные и попробуйте ещё раз.";
}

export function Synastry() {
  const { setScreen, user } = useAppStore();
  const { impact, notification } = useHaptic();
  const [localResult, setLocalResult] = useState<SynastryDisplayResult | null>(
    null,
  );
  const [mode, setMode] = useState<Mode>("pick");

  const requestMutation = useMutation({
    mutationFn: synastryApi.createRequest,
    onSuccess: () => notification("success"),
    onError: () => notification("error"),
  });

  const { data: pending } = useQuery({
    queryKey: ["synastry-pending"],
    queryFn: synastryApi.pending,
    staleTime: 60_000,
  });

  const acceptMutation = useMutation({
    mutationFn: (token: string) => synastryApi.accept(token),
    onSuccess: (data) => {
      setLocalResult(data);
      notification("success");
    },
    onError: () => notification("error"),
  });

  const invite = requestMutation.data;
  const inviteUrl = invite ? normalizeSynastryInviteUrl(invite.invite_url) : "";
  const result = localResult;

  const copy = (text: string) => {
    navigator.clipboard?.writeText(text).then(() => {
      impact("light");
    });
  };

  return (
    <div className="screen synastry-screen">
      <div className="screen-header screen-header--with-back">
        <button
          className="back-btn"
          onClick={() => {
            if (mode !== "pick" && !result) {
              setMode("pick");
              return;
            }
            setScreen("discover", "back");
          }}
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
        <h2 className="screen-title">Синастрия</h2>
      </div>

      <div className="screen-content">
        {result ? (
          <SynastryResultView
            result={result}
            onReset={() => {
              setLocalResult(null);
              setMode("pick");
            }}
          />
        ) : (
          <PremiumGate
            productId="synastry"
            productName="Синастрия"
            stars={100}
            locked={!user?.is_premium}
          >
            {pending && pending.length > 0 && (
              <div className="horoscope-card" style={{ marginBottom: 12 }}>
                <div
                  className="horoscope-card__period"
                  style={{ marginBottom: 8 }}
                >
                  Входящие приглашения
                </div>
                {pending.map((p) => (
                  <div
                    key={p.id}
                    className="transit-row"
                    style={{ gridTemplateColumns: "1fr auto" }}
                  >
                    <span>{p.initiator_name} приглашает вас на Синастрию</span>
                    <button
                      className="btn-primary"
                      onClick={() => acceptMutation.mutate(p.token)}
                      disabled={acceptMutation.isPending}
                    >
                      {acceptMutation.isPending ? "..." : "Принять"}
                    </button>
                  </div>
                ))}
              </div>
            )}

            {mode === "pick" && (
              <div className="synastry-modes">
                <p className="synastry-modes__intro">
                  Синастрия — карта встречи двух натальных гороскопов. Выберите,
                  как добавить партнёра.
                </p>

                <motion.button
                  type="button"
                  className="synastry-mode-card"
                  onClick={() => {
                    impact("light");
                    setMode("invite");
                  }}
                  whileTap={{ scale: 0.97 }}
                >
                  <div className="synastry-mode-card__icon">🔗</div>
                  <div className="synastry-mode-card__body">
                    <div className="synastry-mode-card__title">
                      Пригласить по ссылке
                    </div>
                    <div className="synastry-mode-card__desc">
                      Партнёр получит ссылку, откроет и увидит ваш общий расчёт.
                    </div>
                  </div>
                </motion.button>

                <motion.button
                  type="button"
                  className="synastry-mode-card"
                  onClick={() => {
                    impact("light");
                    setMode("manual");
                  }}
                  whileTap={{ scale: 0.97 }}
                >
                  <div className="synastry-mode-card__icon">✍</div>
                  <div className="synastry-mode-card__body">
                    <div className="synastry-mode-card__title">
                      Ввести данные партнёра
                    </div>
                    <div className="synastry-mode-card__desc">
                      Если партнёр не в Telegram — укажите дату, время и город
                      его рождения.
                    </div>
                  </div>
                </motion.button>
              </div>
            )}

            {mode === "invite" && (
              <div className="horoscope-card">
                <div
                  className="horoscope-card__period"
                  style={{ marginBottom: 8 }}
                >
                  Приглашение партнёра
                </div>
                <p
                  style={{
                    color: "var(--text-dim)",
                    fontSize: 13,
                    marginBottom: 16,
                  }}
                >
                  Создайте ссылку-приглашение и отправьте партнёру. После того
                  как он её откроет, оба увидите карту отношений: топ аспектов и
                  пять сфер совместимости.
                </p>
                {!invite ? (
                  <button
                    className="btn-primary"
                    onClick={() => requestMutation.mutate()}
                    disabled={requestMutation.isPending}
                  >
                    {requestMutation.isPending
                      ? "Создаём..."
                      : "Создать приглашение"}
                  </button>
                ) : (
                  <>
                    <p
                      style={{
                        fontSize: 12,
                        color: "var(--text-dim)",
                        marginBottom: 6,
                      }}
                    >
                      Ссылка-приглашение (действительна 7 дней):
                    </p>
                    <div
                      onClick={() => copy(inviteUrl)}
                      style={{
                        padding: "10px 12px",
                        background: "rgba(255,255,255,0.04)",
                        borderRadius: 10,
                        fontSize: 12,
                        fontFamily: "monospace",
                        wordBreak: "break-all",
                        cursor: "pointer",
                        marginBottom: 12,
                      }}
                    >
                      {inviteUrl}
                    </div>
                    <button
                      className="btn-primary"
                      onClick={() => {
                        const tg = (window as any).Telegram?.WebApp;
                        tg?.openTelegramLink?.(
                          `https://t.me/share/url?url=${encodeURIComponent(inviteUrl)}&text=${encodeURIComponent("Давай узнаем нашу совместимость!")}`,
                        );
                      }}
                    >
                      Поделиться в Telegram
                    </button>
                  </>
                )}
                {requestMutation.error instanceof ApiError && (
                  <p style={{ color: "#e88b8b", fontSize: 12, marginTop: 8 }}>
                    {requestMutation.error.status === 422
                      ? "Заполните данные рождения в профиле."
                      : requestMutation.error.status === 402
                        ? "Сначала купите Синастрию."
                        : requestMutation.error.status === 500
                          ? requestMutation.error.message
                        : "Не удалось создать приглашение."}
                  </p>
                )}
              </div>
            )}

            {mode === "manual" && (
              <ManualPartnerForm onResult={(r) => setLocalResult(r)} />
            )}
          </PremiumGate>
        )}
      </div>
    </div>
  );
}

function ManualPartnerForm({
  onResult,
}: {
  onResult: (r: SynastryDisplayResult) => void;
}) {
  const { user } = useAppStore();
  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("12:00");
  const [timeKnown, setTimeKnown] = useState(true);
  const [city, setCity] = useState("");
  const [coords, setCoords] = useState<CityOption | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const manualMutation = useMutation({
    mutationFn: async (payload: SynastryManualInput) => {
      try {
        return await synastryApi.manual(payload);
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 404) {
          throw error;
        }

        if (!user?.sun_sign) {
          throw new ApiError(
            422,
            "Заполните свои данные рождения в профиле, чтобы рассчитать совместимость.",
          );
        }

        const partnerSign = getZodiacSignFromDate(payload.birth_date);
        const compatibility = await compatibilityApi.get(
          user.sun_sign,
          partnerSign,
        );

        return compatibilityToSynastryResult(
          compatibility,
          user.name,
          payload.partner_name,
        );
      }
    },
    onSuccess: (result) => onResult(result),
  });

  const canSubmit =
    name.trim().length > 0 &&
    date.trim().length > 0 &&
    city.trim().length > 0 &&
    !manualMutation.isPending;

  const submit = () => {
    if (!canSubmit) return;

    const dateValidation = validatePartnerBirthDate(date);
    if (!dateValidation.normalizedDate) {
      setLocalError(dateValidation.message);
      return;
    }

    setLocalError(null);
    manualMutation.mutate({
      partner_name: name.trim(),
      birth_date: dateValidation.normalizedDate,
      birth_time: time,
      birth_time_known: timeKnown,
      birth_city: coords?.cityName ?? city.trim(),
      birth_lat: coords?.lat,
      birth_lng: coords?.lng,
      birth_tz: "", // backend resolves from lat/lng or city
    });
  };

  const errMsg = localError ?? getManualSynastryErrorMessage(manualMutation.error);

  return (
    <div className="horoscope-card">
      <div className="horoscope-card__period" style={{ marginBottom: 8 }}>
        Данные партнёра
      </div>
      <p
        style={{
          color: "var(--text-dim)",
          fontSize: 13,
          marginBottom: 16,
        }}
      >
        Укажите дату, время и город рождения партнёра. Часовой пояс определим
        автоматически.
      </p>
      <label className="form-label">
        Имя партнёра
        <input
          className="form-input"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Например, Анна"
        />
      </label>
      <label className="form-label">
        Дата рождения
        <input
          className="form-input"
          type="text"
          inputMode="numeric"
          value={date}
          onChange={(e) => {
            setDate(formatBirthDateInput(e.target.value));
            setLocalError(null);
            manualMutation.reset();
          }}
          placeholder="ДД.ММ.ГГГГ"
          autoComplete="bday"
          maxLength={10}
        />
      </label>
      <label className="form-label">
        Время рождения
        <input
          className="form-input"
          type="time"
          value={time}
          onChange={(e) => setTime(e.target.value)}
          disabled={!timeKnown}
        />
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            marginTop: 6,
            fontSize: 12,
            color: "var(--text-muted)",
          }}
        >
          <input
            type="checkbox"
            checked={!timeKnown}
            onChange={(e) => setTimeKnown(!e.target.checked)}
          />
          Время неизвестно (используем 12:00)
        </label>
      </label>
      <label className="form-label">
        Город рождения
        <CityAutocomplete
          value={city}
          onChange={(v) => {
            setCity(v);
            if (coords && v !== coords.displayName) setCoords(null);
          }}
          onSelect={(opt) => {
            setCity(opt.displayName);
            setCoords(opt);
          }}
          placeholder="Москва, Лондон, Нью-Йорк..."
        />
      </label>

      <button
        className="btn-primary"
        style={{ marginTop: 8 }}
        disabled={!canSubmit}
        onClick={submit}
      >
        {manualMutation.isPending ? "Считаем..." : "Рассчитать совместимость"}
      </button>

      {errMsg && (
        <p style={{ color: "#e88b8b", fontSize: 12, marginTop: 8 }}>{errMsg}</p>
      )}
    </div>
  );
}

function SynastryResultView({
  result,
  onReset,
}: {
  result: SynastryDisplayResult;
  onReset: () => void;
}) {
  const fallback = result.fallbackCompatibility;

  return (
    <>
      <div className="horoscope-card">
        <div className="horoscope-card__period" style={{ marginBottom: 8 }}>
          {result.initiator_name}{" "}
          {result.partner_name ? `× ${result.partner_name}` : ""}
        </div>
        <div className="energy-bars">
          {SPHERE_LABELS.map(({ key, label }) => (
            <div key={key} className="energy-row">
              <span className="energy-label">{label}</span>
              <div className="energy-track">
                <motion.div
                  className="energy-fill"
                  initial={{ width: 0 }}
                  animate={{ width: `${result.scores[key]}%` }}
                  transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
                />
              </div>
              <span className="energy-val">{result.scores[key]}%</span>
            </div>
          ))}
        </div>
      </div>

      {fallback ? (
        <div className="horoscope-card">
          <div className="horoscope-card__period" style={{ marginBottom: 12 }}>
            Базовая совместимость
          </div>
          <p className="compat-description" style={{ marginTop: 0 }}>
            {fallback.description_ru}
          </p>
          {fallback.strengths_ru.length > 0 && (
            <div className="compat-list compat-list--strengths">
              <div className="compat-list__title">
                <span className="compat-list__dot compat-list__dot--green" />
                Сильные стороны
              </div>
              {fallback.strengths_ru.map((item, idx) => (
                <div key={idx} className="compat-list__item">
                  • {item}
                </div>
              ))}
            </div>
          )}
          {fallback.challenges_ru.length > 0 && (
            <div className="compat-list compat-list--challenges">
              <div className="compat-list__title">
                <span className="compat-list__dot compat-list__dot--amber" />
                Вызовы
              </div>
              {fallback.challenges_ru.map((item, idx) => (
                <div key={idx} className="compat-list__item">
                  • {item}
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="horoscope-card">
          <div className="horoscope-card__period" style={{ marginBottom: 12 }}>
            Ключевые аспекты ({result.total_aspects} всего)
          </div>
          <div className="transits-list">
            {result.aspects.map((a, idx) => (
              <motion.div
                key={idx}
                className="transit-row"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.04, duration: 0.3 }}
              >
                <span className="transit-row__planet">
                  {PLANET_GLYPH[a.p1_name.toLowerCase()] ?? "●"} {a.p1_name_ru}
                </span>
                <span
                  className="transit-row__aspect"
                  style={{
                    color: ASPECT_COLOR[a.aspect] ?? "var(--text-dim)",
                  }}
                >
                  {ASPECT_SYMBOL[a.aspect] ?? a.aspect_ru}
                </span>
                <span className="transit-row__planet">
                  {PLANET_GLYPH[a.p2_name.toLowerCase()] ?? "●"} {a.p2_name_ru}
                </span>
                <span className="transit-row__orb">{a.orb.toFixed(1)}°</span>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      <button
        className="btn-primary"
        style={{ marginTop: 12 }}
        onClick={onReset}
      >
        Назад к приглашениям
      </button>
    </>
  );
}
