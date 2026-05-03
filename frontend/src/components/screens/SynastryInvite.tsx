import { useMutation, useQuery } from "@tanstack/react-query";
import { useAppStore } from "@/stores/app";
import { synastryApi, ApiError } from "@/services/api";
import { useHaptic, useStartParam } from "@/hooks/useTelegram";
import type { SynastryResult } from "@/types";
import { useState } from "react";
import { SynastryReport } from "@/components/synastry/SynastryReport";

export function SynastryInvite() {
  const { setScreen, pendingInviteToken, setPendingInviteToken } =
    useAppStore();
  const { notification } = useHaptic();
  const startParam = useStartParam();
  const [result, setResult] = useState<SynastryResult | null>(null);

  // Prefer the start_param if it's still in scope; otherwise fall back to the
  // persisted token (the case where we're returning here after onboarding).
  const tokenFromStart = startParam?.startsWith("syn_")
    ? startParam.slice(4)
    : null;
  const token = tokenFromStart ?? pendingInviteToken;

  // Pre-fetch the inviter's name so we can show "Вас пригласил <name>" while
  // the user decides whether to accept.
  const inviteInfoQuery = useQuery({
    queryKey: ["synastry", "invite", token],
    queryFn: () => synastryApi.inviteInfo(token!),
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
    retry: 0,
  });
  const inviterName = inviteInfoQuery.data?.initiator_name ?? null;

  const acceptMutation = useMutation({
    mutationFn: () => {
      if (!token) throw new Error("no token");
      return synastryApi.accept(token);
    },
    onSuccess: (data) => {
      setResult(data);
      notification("success");
      setPendingInviteToken(null);
    },
    onError: () => notification("error"),
  });

  const goHome = () => {
    setPendingInviteToken(null);
    setScreen("home", "back");
  };

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
            <SynastryReport result={result} />
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
              {inviterName ? (
                <>
                  Вас пригласил <strong>{inviterName}</strong> рассчитать
                  совместимость.
                </>
              ) : (
                <>Вас приглашают рассчитать совместимость.</>
              )}
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
