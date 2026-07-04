import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import WebApp from "@twa-dev/sdk";
import { referralsApi } from "@/services/api";
import { useAppStore } from "@/stores/app";
import { useHaptic } from "@/hooks/useTelegram";

export function Referral() {
  const { setScreen } = useAppStore();
  const { impact, notification } = useHaptic();

  const { data, isLoading } = useQuery({
    queryKey: ["referral-me"],
    queryFn: referralsApi.getMe,
    staleTime: 1000 * 60 * 2,
  });

  const inviteUrl = data?.invite_url ?? "";

  const handleCopy = async () => {
    if (!inviteUrl) return;
    try {
      await navigator.clipboard.writeText(inviteUrl);
      notification("success");
      impact("light");
    } catch {
      // fall back silently
    }
  };

  const handleShare = () => {
    if (!inviteUrl) return;
    impact("light");
    const message = "Я тут нашёл астро-приложение — посмотри, может зайдёт.";
    WebApp.openTelegramLink(
      `https://t.me/share/url?url=${encodeURIComponent(inviteUrl)}&text=${encodeURIComponent(message)}`,
    );
  };

  return (
    <div className="screen referral-screen">
      <div className="screen-header screen-header--with-back">
        <button
          type="button"
          className="back-btn"
          onClick={() => setScreen("profile", "back")}
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
        <h2 className="screen-title">Пригласить друзей</h2>
      </div>

      <div className="screen-content">
        <motion.div
          className="referral-hero"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className="referral-hero__crown" aria-hidden="true">✦</div>
          <h3 className="referral-hero__title">Поделитесь приложением</h3>
          <p className="referral-hero__lead">
            Отправьте ссылку другу — он сможет открыть приложение в один тап.
            Здесь же будет видно, сколько человек уже зашло по вашей ссылке.
          </p>
        </motion.div>

        <motion.div
          className="referral-link-card"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.4 }}
        >
          <div className="referral-link-card__label">Ваша ссылка</div>
          {isLoading ? (
            <div className="referral-link-card__url referral-link-card__url--loading">
              Готовим…
            </div>
          ) : inviteUrl ? (
            <div className="referral-link-card__url" title={inviteUrl}>
              {inviteUrl.replace(/^https?:\/\//, "")}
            </div>
          ) : (
            <div className="referral-link-card__url">Ссылка не настроена</div>
          )}
          <div className="referral-link-card__buttons">
            <button
              type="button"
              className="btn-ghost"
              onClick={handleCopy}
              disabled={!inviteUrl}
            >
              Скопировать
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={handleShare}
              disabled={!inviteUrl}
            >
              Поделиться
            </button>
          </div>
        </motion.div>

        <motion.div
          className="referral-stats referral-stats--single"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.4 }}
        >
          <div className="referral-stats__cell">
            <div className="referral-stats__value">{data?.stats.invited_total ?? 0}</div>
            <div className="referral-stats__label">приглашённых друзей</div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
