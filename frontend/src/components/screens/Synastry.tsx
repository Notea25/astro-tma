import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { PremiumGate } from "@/components/ui/PremiumGate";
import {
  CityAutocomplete,
  type CityOption,
} from "@/components/ui/CityAutocomplete";
import { useAppStore } from "@/stores/app";
import { synastryApi, ApiError } from "@/services/api";
import { useHaptic } from "@/hooks/useTelegram";
import type { SynastryResult, SynastryManualInput } from "@/types";

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

export function Synastry() {
  const { setScreen, user } = useAppStore();
  const { impact, notification } = useHaptic();
  const [localResult, setLocalResult] = useState<SynastryResult | null>(null);
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
                      onClick={() => copy(invite.invite_url)}
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
                      {invite.invite_url}
                    </div>
                    <button
                      className="btn-primary"
                      onClick={() => {
                        const tg = (window as any).Telegram?.WebApp;
                        tg?.openTelegramLink?.(
                          `https://t.me/share/url?url=${encodeURIComponent(invite.invite_url)}&text=${encodeURIComponent("Давай узнаем нашу совместимость!")}`,
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
  onResult: (r: SynastryResult) => void;
}) {
  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("12:00");
  const [timeKnown, setTimeKnown] = useState(true);
  const [city, setCity] = useState("");
  const [coords, setCoords] = useState<CityOption | null>(null);

  const manualMutation = useMutation({
    mutationFn: (payload: SynastryManualInput) => synastryApi.manual(payload),
    onSuccess: (result) => onResult(result),
  });

  const canSubmit =
    name.trim().length > 0 &&
    date.length > 0 &&
    city.trim().length > 0 &&
    !manualMutation.isPending;

  const submit = () => {
    if (!canSubmit) return;
    manualMutation.mutate({
      partner_name: name.trim(),
      birth_date: date,
      birth_time: time,
      birth_time_known: timeKnown,
      birth_city: coords?.cityName ?? city.trim(),
      birth_lat: coords?.lat,
      birth_lng: coords?.lng,
      birth_tz: "", // backend resolves from lat/lng or city
    });
  };

  const errMsg = (() => {
    const err = manualMutation.error;
    if (!(err instanceof ApiError)) return null;
    if (err.status === 422) return "Заполните данные рождения в профиле.";
    if (err.status === 402) return "Сначала купите Синастрию.";
    return "Не удалось рассчитать совместимость.";
  })();

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
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
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
  result: SynastryResult;
  onReset: () => void;
}) {
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
