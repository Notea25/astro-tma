import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useAppStore } from "@/stores/app";
import { synastryApi, ApiError } from "@/services/api";
import { useHaptic, useStartParam } from "@/hooks/useTelegram";
import type { SynastryResult } from "@/types";
import { useState } from "react";

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

export function SynastryInvite() {
  const { setScreen, user } = useAppStore();
  const { notification } = useHaptic();
  const startParam = useStartParam();
  const [result, setResult] = useState<SynastryResult | null>(null);

  const token = startParam?.startsWith("syn_") ? startParam.slice(4) : null;

  const acceptMutation = useMutation({
    mutationFn: () => {
      if (!token) throw new Error("no token");
      return synastryApi.accept(token);
    },
    onSuccess: (data) => {
      setResult(data);
      notification("success");
    },
    onError: () => notification("error"),
  });

  const goHome = () => setScreen("home", "back");

  if (!token) {
    return (
      <div className="screen synastry-screen">
        <div className="screen-header screen-header--with-back">
          <button className="back-btn" onClick={goHome} aria-label="Назад">
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
          <p style={{ textAlign: "center", color: "var(--text-dim)" }}>
            Неверная ссылка-приглашение.
          </p>
        </div>
      </div>
    );
  }

  const error =
    acceptMutation.error instanceof ApiError ? acceptMutation.error : null;
  const needsProfile = error?.status === 422;
  const expired = error?.status === 410;
  const notFound = error?.status === 404;
  const ownInvite = error?.status === 400;

  return (
    <div className="screen synastry-screen">
      <div className="screen-header screen-header--with-back">
        <button className="back-btn" onClick={goHome} aria-label="Назад">
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
        <h2 className="screen-title">Приглашение</h2>
      </div>

      <div className="screen-content">
        {result ? (
          <>
            <div className="horoscope-card">
              <div
                className="horoscope-card__period"
                style={{ marginBottom: 8 }}
              >
                {result.initiator_name} × {result.partner_name ?? user?.name}
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
                        transition={{
                          duration: 0.8,
                          ease: "easeOut",
                          delay: 0.1,
                        }}
                      />
                    </div>
                    <span className="energy-val">{result.scores[key]}%</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="horoscope-card">
              <div
                className="horoscope-card__period"
                style={{ marginBottom: 12 }}
              >
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
                      {PLANET_GLYPH[a.p1_name.toLowerCase()] ?? "●"}{" "}
                      {a.p1_name_ru}
                    </span>
                    <span
                      className="transit-row__aspect"
                      style={{
                        color:
                          ASPECT_COLOR[a.aspect] ?? "var(--text-dim)",
                      }}
                    >
                      {ASPECT_SYMBOL[a.aspect] ?? a.aspect_ru}
                    </span>
                    <span className="transit-row__planet">
                      {PLANET_GLYPH[a.p2_name.toLowerCase()] ?? "●"}{" "}
                      {a.p2_name_ru}
                    </span>
                    <span className="transit-row__orb">
                      {a.orb.toFixed(1)}°
                    </span>
                  </motion.div>
                ))}
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ marginTop: 12 }}
              onClick={goHome}
            >
              На главную
            </button>
          </>
        ) : (
          <div
            className="horoscope-card"
            style={{ textAlign: "center", padding: "24px 20px" }}
          >
            <div style={{ fontSize: 48, marginBottom: 12 }}>💞</div>
            <p style={{ marginBottom: 16, fontSize: 15 }}>
              Вас приглашают рассчитать совместимость.
            </p>
            <p
              style={{
                color: "var(--text-dim)",
                fontSize: 13,
                marginBottom: 20,
              }}
            >
              Нужны ваши данные рождения (из профиля). Результат увидите оба.
            </p>
            {notFound && (
              <p style={{ color: "#e88b8b", fontSize: 13, marginBottom: 12 }}>
                Приглашение не найдено.
              </p>
            )}
            {expired && (
              <p style={{ color: "#e88b8b", fontSize: 13, marginBottom: 12 }}>
                Срок действия истёк.
              </p>
            )}
            {ownInvite && (
              <p style={{ color: "#e88b8b", fontSize: 13, marginBottom: 12 }}>
                Нельзя принять собственное приглашение.
              </p>
            )}
            {needsProfile ? (
              <button
                className="btn-primary"
                onClick={() => setScreen("profile")}
              >
                Заполнить профиль
              </button>
            ) : (
              <button
                className="btn-primary"
                onClick={() => acceptMutation.mutate()}
                disabled={
                  acceptMutation.isPending ||
                  !!notFound ||
                  !!expired ||
                  !!ownInvite
                }
              >
                {acceptMutation.isPending
                  ? "Рассчитываем..."
                  : "Принять и рассчитать"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
