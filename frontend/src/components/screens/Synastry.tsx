import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { PremiumGate } from "@/components/ui/PremiumGate";
import { useAppStore } from "@/stores/app";
import { synastryApi, ApiError } from "@/services/api";
import { useHaptic } from "@/hooks/useTelegram";
import type { SynastryResult } from "@/types";

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

export function Synastry() {
  const { setScreen, user } = useAppStore();
  const { impact, notification } = useHaptic();
  const [localResult, setLocalResult] = useState<SynastryResult | null>(null);

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
        <h2 className="screen-title">Синастрия</h2>
      </div>

      <div className="screen-content">
        {result ? (
          <SynastryResultView
            result={result}
            onReset={() => setLocalResult(null)}
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

            <div className="horoscope-card">
              <div
                className="horoscope-card__period"
                style={{ marginBottom: 8 }}
              >
                Глубокий анализ совместимости
              </div>
              <p
                style={{
                  color: "var(--text-secondary)",
                  fontSize: 13,
                  marginBottom: 16,
                }}
              >
                Создайте приглашение и отправьте партнёру. После принятия вы оба
                увидите карту отношений: топ-12 аспектов и 4 сферы
                совместимости.
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
                      color: "var(--text-secondary)",
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
                      : "Не удалось создать приглашение."}
                </p>
              )}
            </div>
          </PremiumGate>
        )}
      </div>
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
                  color: ASPECT_COLOR[a.aspect] ?? "var(--text-secondary)",
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
