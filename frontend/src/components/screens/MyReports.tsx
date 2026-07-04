/**
 * «Мои разборы» — central hub listing every generated report this user
 * has access to. Powered by /users/me/reports (status-only, no LLM).
 *
 * Three cards: Натальная карта · Матрица Судьбы · Синастрия. Each card
 * shows a one-line status («Готов» / «Куплено, нужна дата рождения» /
 * «Откройте Premium…») and routes to the per-product screen on tap.
 */
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { usersApi } from "@/services/api";
import { useAppStore } from "@/stores/app";
import { useHaptic } from "@/hooks/useTelegram";
import { QueryStateFallback } from "@/components/ui/QueryStateFallback";

type ReportRow = {
  title: string;
  subtitle: string;
  emoji: string;
  onOpen: () => void;
  open_disabled?: boolean;
};

export function MyReports() {
  const { setScreen } = useAppStore();
  const { impact } = useHaptic();

  const reportsQuery = useQuery({
    queryKey: ["my-reports"],
    queryFn: usersApi.getMyReports,
    staleTime: 1000 * 30,
  });

  const goBack = () => {
    impact("light");
    setScreen("profile", "back");
  };

  const buildRows = (data: Awaited<ReturnType<typeof usersApi.getMyReports>>): ReportRow[] => {
    const rows: ReportRow[] = [];

    // ── Натальная карта ─────────────────────────────────────
    const n = data.natal;
    let subtitle: string;
    let disabled = false;
    if (!n.has_chart) {
      subtitle = "Сначала укажите дату и место рождения";
      disabled = true;
    } else if (!n.has_access) {
      subtitle = "Откройте Premium-доступ, чтобы прочитать";
    } else if (!n.has_content) {
      subtitle = "Готовится — зайдите через минуту";
    } else {
      const signs = [n.sun_sign, n.moon_sign].filter(Boolean).join(" · ");
      subtitle = signs ? `Готов · ${signs}` : "Готов";
    }
    rows.push({
      title: "Натальная карта",
      subtitle,
      emoji: "✦",
      open_disabled: disabled,
      onOpen: () => {
        impact("light");
        if (n.has_chart && n.has_access && n.has_content) {
          setScreen("natal_full_reading");
        } else {
          setScreen("natal");
        }
      },
    });

    // ── Матрица Судьбы ────────────────────────────────────
    const m = data.matrix;
    let m_subtitle: string;
    let m_disabled = false;
    if (!m.has_chart) {
      m_subtitle = "Сначала укажите дату рождения";
      m_disabled = true;
    } else if (!m.has_access) {
      m_subtitle = "Откройте полный разбор за 150 ⭐";
    } else if (!m.has_content) {
      m_subtitle = "Откройте — разбор соберётся за минуту";
    } else {
      m_subtitle = "Готов · 15 разделов";
    }
    rows.push({
      title: "Матрица Судьбы",
      subtitle: m_subtitle,
      emoji: "✧",
      open_disabled: m_disabled,
      onOpen: () => {
        impact("light");
        setScreen("destiny_matrix_reading");
      },
    });

    // ── Синастрия ─────────────────────────────────────────
    const s = data.synastry;
    let s_subtitle: string;
    if (s.completed_count === 0) {
      s_subtitle = "Запустите первый разбор пары";
    } else {
      const count = `${s.completed_count} ${
        s.completed_count === 1 ? "разбор" : s.completed_count < 5 ? "разбора" : "разборов"
      }`;
      const last = s.latest_partner_name ? ` · последний: ${s.latest_partner_name}` : "";
      s_subtitle = `${count}${last}`;
    }
    rows.push({
      title: "Синастрия",
      subtitle: s_subtitle,
      emoji: "♡",
      onOpen: () => {
        impact("light");
        setScreen("synastry");
      },
    });

    return rows;
  };

  return (
    <div className="screen">
      <div className="screen-header screen-header--with-back">
        <button
          type="button"
          className="back-btn"
          onClick={goBack}
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
        <h1 className="screen-title">Мои разборы</h1>
      </div>

      <div className="myreports">
        <QueryStateFallback
          query={reportsQuery}
          onRetry={() => reportsQuery.refetch()}
          errorTitle="Не удалось загрузить разборы"
        >
          {(data) => (
            <>
              {buildRows(data).map((r, i) => (
                <motion.button
                  key={r.title}
                  type="button"
                  className={`pr-row2 myreports__row${
                    r.open_disabled ? " myreports__row--disabled" : ""
                  }`}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.04 * i }}
                  onClick={r.onOpen}
                  disabled={r.open_disabled}
                >
                  <span className="pr-row2__ic myreports__ic" aria-hidden="true">
                    {r.emoji}
                  </span>
                  <span className="pr-row2__main">
                    <span className="pr-row2__t">{r.title}</span>
                    <span className="pr-row2__s">{r.subtitle}</span>
                  </span>
                  <span className="pr-row2__chev" aria-hidden="true">›</span>
                </motion.button>
              ))}
            </>
          )}
        </QueryStateFallback>
      </div>
    </div>
  );
}
