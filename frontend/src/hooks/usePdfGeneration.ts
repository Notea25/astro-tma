/**
 * Natal-PDF generation hook — queue-based, like usePayment._waitForPurchase.
 *
 * The button tap enqueues a job on the backend; the heavy LLM work runs in the
 * arq worker. We poll status until ready, then download the PDF by its one-shot
 * token. On a warm cache the backend returns `ready` immediately and we skip
 * polling. Generation can take minutes on a rate-limited LLM tier — that's fine,
 * the request side never blocks.
 */

import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { natalApi } from "@/services/api";

export type PdfDeliveryMode = "download" | "telegram";
export type PdfPhase = "idle" | "queued" | "processing" | "ready" | "error";

interface UsePdfGenerationResult {
  start: (mode?: PdfDeliveryMode) => Promise<void>;
  phase: PdfPhase;
  /** True while a job is queued or processing (UI shows a loader). */
  busy: boolean;
  error: string | null;
}

const POLL_INTERVAL_MS = 1500;
const POLL_MAX_ATTEMPTS = 160; // ~4 min — a slow free-tier run still completes

export function usePdfGeneration(): UsePdfGenerationResult {
  const queryClient = useQueryClient();
  const [phase, setPhase] = useState<PdfPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const inflight = useRef(false);

  const deliverReadyPdf = useCallback(
    async (
      mode: PdfDeliveryMode,
      token: string,
      filename: string | undefined,
    ) => {
      if (mode === "telegram") {
        await natalApi.sendPdfToTelegram();
        return;
      }
      await natalApi.downloadByToken(token, filename);
    },
    [],
  );

  const refreshReportScreens = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["natal-full"] }),
      queryClient.invalidateQueries({ queryKey: ["my-reports"] }),
    ]);
  }, [queryClient]);

  const start = useCallback(async (mode: PdfDeliveryMode = "download") => {
    if (inflight.current) return;
    inflight.current = true;
    setError(null);
    setPhase("queued");

    try {
      // Embed the live on-screen wheel before generating (one-shot upload).
      await natalApi.ensureWheelSvgUploaded();

      const res = await natalApi.startPdf();

      if (res.status === "ready" && res.download_token) {
        setPhase("ready");
        await refreshReportScreens();
        await deliverReadyPdf(mode, res.download_token, res.filename ?? undefined);
        return;
      }

      const jobId = res.job_id;
      setPhase(res.status === "processing" ? "processing" : "queued");

      for (let i = 0; i < POLL_MAX_ATTEMPTS; i++) {
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
        let st;
        try {
          st = await natalApi.pdfStatus(jobId);
        } catch {
          continue; // transient errors — keep polling
        }
        if (st.status === "processing") {
          setPhase("processing");
        } else if (st.status === "ready" && st.download_token) {
          setPhase("ready");
          await refreshReportScreens();
          await deliverReadyPdf(mode, st.download_token, st.filename ?? undefined);
          return;
        } else if (st.status === "failed") {
          throw new Error(st.error || "Не удалось сгенерировать отчёт");
        }
      }
      throw new Error(
        "Разбор пишется дольше обычного. Попробуйте ещё раз через минуту.",
      );
    } catch (e) {
      setPhase("error");
      setError(
        e instanceof Error ? e.message : "Не удалось подготовить отчёт",
      );
    } finally {
      inflight.current = false;
    }
  }, [deliverReadyPdf, refreshReportScreens]);

  return {
    start,
    phase,
    busy: phase === "queued" || phase === "processing",
    error,
  };
}
