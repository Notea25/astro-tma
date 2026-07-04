/**
 * NatalFullReading — sub-screen that surfaces the pre-generated natal
 * reading text inline, without forcing the user to download the PDF or
 * wait for a 90+ second worker pipeline. Pulls /natal/full (uses cache)
 * and /natal/descriptions (already persisted on the chart row).
 *
 * Routing: opened from «Мой разбор» buttons inside the Natal screen
 * AND from the «Мои разборы» Profile hub.
 */
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { natalApi } from "@/services/api";
import { useAppStore } from "@/stores/app";
import { useHaptic } from "@/hooks/useTelegram";
import { usePdfGeneration } from "@/hooks/usePdfGeneration";
import { cleanMarkdownText } from "@/utils/text";

// LLM output uses **bold** for section headers; turn them into proper h3s.
function renderReading(raw: string): JSX.Element[] {
  const blocks: JSX.Element[] = [];
  const lines = raw.split("\n");
  let para: string[] = [];
  let key = 0;

  const flushPara = () => {
    if (!para.length) return;
    const text = para.join(" ").trim();
    if (text) {
      blocks.push(
        <p key={`p-${key++}`} className="natal-fr__p">
          {cleanMarkdownText(text)}
        </p>,
      );
    }
    para = [];
  };

  for (const line of lines) {
    const t = line.trim();
    if (!t) {
      flushPara();
      continue;
    }
    const headingMatch = t.match(/^\*\*(.+?)\*\*$/);
    if (headingMatch) {
      flushPara();
      blocks.push(
        <h3 key={`h-${key++}`} className="natal-fr__h">
          {cleanMarkdownText(headingMatch[1])}
        </h3>,
      );
      continue;
    }
    para.push(t);
  }
  flushPara();
  return blocks;
}

export function NatalFullReading() {
  const { setScreen } = useAppStore();
  const { impact } = useHaptic();
  const { start: startPdf, phase: pdfPhase, error: pdfError } = usePdfGeneration();

  const { data, isLoading } = useQuery({
    queryKey: ["natal-full"],
    queryFn: natalApi.getFull,
    staleTime: 1000 * 60 * 5,
  });

  const goBack = () => {
    impact("light");
    setScreen("natal", "back");
  };

  const reading = (data?.reading || "").trim();
  const downloading = pdfPhase === "queued" || pdfPhase === "processing";

  return (
    <div className="screen natal-fr-screen">
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
        <h1 className="screen-title">Мой разбор</h1>
      </div>

      <motion.div
        className="natal-fr"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
      >
        {isLoading && <p className="natal-fr__loading">Открываем…</p>}

        {!isLoading && reading ? (
          <article className="natal-fr__article">{renderReading(reading)}</article>
        ) : null}

        {!isLoading && !reading && (
          <p className="natal-fr__empty">
            Разбор ещё не готов. Откройте «Скачать PDF» — он соберётся
            за минуту и сохранится здесь же.
          </p>
        )}

        <div className="natal-fr__cta-row">
          <button
            type="button"
            className="btn-stars natal-fr__pdf-btn"
            onClick={() => {
              impact("medium");
              void startPdf();
            }}
            disabled={downloading}
          >
            {pdfPhase === "queued" && "В очереди…"}
            {pdfPhase === "processing" && "Пишем PDF…"}
            {pdfPhase !== "queued" &&
              pdfPhase !== "processing" &&
              "Скачать PDF"}
          </button>
          {pdfError && <p className="natal-fr__pdf-error">{pdfError}</p>}
        </div>
      </motion.div>
    </div>
  );
}
