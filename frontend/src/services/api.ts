/**
 * API client — thin wrapper over fetch.
 * Automatically injects X-Init-Data header (Telegram auth).
 * All methods throw on non-2xx — React Query catches them.
 */

import WebApp from "@twa-dev/sdk";

const configuredBaseUrl = (
  (import.meta.env.VITE_API_URL as string | undefined) ?? ""
)
  .trim()
  .replace(/\/+$/, "");
const BASE_URL = configuredBaseUrl
  ? configuredBaseUrl.endsWith("/api")
    ? configuredBaseUrl
    : `${configuredBaseUrl}/api`
  : "/api";

type NatalPdfLinkResponse = {
  download_url: string;
  filename: string;
  expires_in: number;
};

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function formatApiErrorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg?: unknown }).msg ?? "");
        }
        return "";
      })
      .filter(Boolean);
    return messages.join("; ") || fallback;
  }

  if (detail && typeof detail === "object" && "msg" in detail) {
    return String((detail as { msg?: unknown }).msg ?? fallback);
  }

  return fallback;
}

function apiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${BASE_URL}${suffix}`;
}

function absoluteUrl(url: string): string {
  return new URL(url, window.location.origin).toString();
}

function openDownloadWindow(): Window | null {
  try {
    const popup = window.open("about:blank", "_blank");
    if (popup?.document) {
      popup.document.title = "Готовим PDF";
      popup.document.body.style.cssText =
        "margin:0;display:grid;place-items:center;min-height:100vh;background:#07060f;color:#f0d48a;font:16px system-ui,sans-serif;";
      popup.document.body.textContent = "Готовим PDF...";
    }
    return popup;
  } catch {
    return null;
  }
}

function triggerDownload(url: string, filename: string): void {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  triggerDownload(url, filename);
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function canUseTelegramOpenLink(): boolean {
  return Boolean(WebApp.initData) && typeof WebApp.openLink === "function";
}

async function openTemporaryPdfLink(filename: string): Promise<void> {
  const link = await request<NatalPdfLinkResponse>("POST", "/natal/pdf-link");
  const downloadUrl = apiUrl(link.download_url);
  const absoluteDownloadUrl = absoluteUrl(downloadUrl);

  if (canUseTelegramOpenLink()) {
    try {
      WebApp.openLink(absoluteDownloadUrl);
      return;
    } catch {
      // Fall through to a browser-style download if Telegram rejects the link.
    }
  }

  triggerDownload(downloadUrl, link.filename || filename);
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Init-Data": WebApp.initData || "", // Telegram auth token
  };

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const payload = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? (payload as { detail?: unknown }).detail
        : undefined;
    throw new ApiError(
      response.status,
      formatApiErrorDetail(detail, response.statusText),
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

async function requestBlob(path: string): Promise<Blob> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "GET",
    headers: {
      "X-Init-Data": WebApp.initData || "",
    },
  });

  if (!response.ok) {
    const payload = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? (payload as { detail?: unknown }).detail
        : undefined;
    throw new ApiError(
      response.status,
      formatApiErrorDetail(detail, response.statusText),
    );
  }

  return response.blob();
}

// ── Users ──────────────────────────────────────────────────────────────────────
export const usersApi = {
  upsertMe: () => request<import("@/types").UserProfile>("POST", "/users/me"),
  setGender: (gender: string) =>
    request<import("@/types").UserProfile>("POST", "/users/me/gender", {
      gender,
    }),
  setupBirth: (data: {
    birth_date: string;
    birth_time_known: boolean;
    birth_city: string;
    lat?: number;
    lng?: number;
  }) => request("POST", "/users/me/birth", data),
  setPushEnabled: (enabled: boolean) =>
    request<import("@/types").UserProfile>("PATCH", "/users/me/push", {
      enabled,
    }),
};

// ── Horoscope ──────────────────────────────────────────────────────────────────
export const horoscopeApi = {
  getToday: () =>
    request<import("@/types").HoroscopeResponse>("GET", "/horoscope/today"),
  getPeriod: (period: string) =>
    request<import("@/types").HoroscopeResponse>(
      "GET",
      `/horoscope/period?period=${period}`,
    ),
  getMoon: () =>
    request<import("@/types").MoonPhaseResponse>("GET", "/horoscope/moon"),
  getMoonCalendar: (year: number, month: number) =>
    request<{
      year: number;
      month: number;
      days: import("@/types").MoonCalendarDay[];
    }>("GET", `/horoscope/moon/calendar?year=${year}&month=${month}`),
};

// ── Natal ──────────────────────────────────────────────────────────────────────
export const natalApi = {
  getSummary: () =>
    request<import("@/types").NatalSummaryResponse>("GET", "/natal/summary"),
  getFull: () =>
    request<import("@/types").NatalFullResponse>("GET", "/natal/full"),
  getDescriptions: () =>
    request<import("@/types").NatalDescriptionsResponse>(
      "GET",
      "/natal/descriptions",
    ),
  downloadPdf: async () => {
    const filename = "natal-chart.pdf";

    if (canUseTelegramOpenLink()) {
      await openTemporaryPdfLink(filename);
      return;
    }

    try {
      const blob = await requestBlob("/natal/pdf");
      triggerBlobDownload(blob, filename);
      return;
    } catch (directDownloadError) {
      const popup = openDownloadWindow();

      try {
        const link = await request<NatalPdfLinkResponse>(
          "POST",
          "/natal/pdf-link",
        );
        const downloadUrl = apiUrl(link.download_url);

        if (popup && !popup.closed) {
          popup.location.href = downloadUrl;
          return;
        }

        triggerDownload(downloadUrl, link.filename || filename);
      } catch {
        if (popup && !popup.closed) {
          popup.close();
        }
        throw directDownloadError;
      }
    }
  },
};

// ── Tarot ──────────────────────────────────────────────────────────────────────
// Rewrite backend's webp image URL to local /tarot/<folder>/card-NN-<slug>.svg
function localTarotImage(remoteUrl: string | null | undefined): string | null {
  if (!remoteUrl) return null;
  const filename = remoteUrl.split("/").pop() ?? "";
  // Pattern: NN_Some_Card_Name.webp  →  NN, Some_Card_Name
  const m = filename.match(/^(\d{2})_(.+)\.(webp|png|jpe?g|svg)$/i);
  if (!m) return remoteUrl; // fallback to original
  const [, num, namePart] = m;
  const folder = parseInt(num, 10) < 22 ? "majors" : "minors";
  const slug = namePart.toLowerCase().replace(/^the_/, "").replace(/_/g, "-");
  return `/tarot/${folder}/card-${num}-${slug}.svg`;
}

function rewriteCardImage<T extends { image_url?: string | null }>(card: T): T {
  return { ...card, image_url: localTarotImage(card.image_url ?? undefined) };
}

function rewriteSpread<T extends { cards: { image_url?: string | null }[] }>(
  resp: T,
): T {
  return { ...resp, cards: resp.cards.map(rewriteCardImage) } as T;
}

export const tarotApi = {
  draw: (spread_type: string) =>
    request<import("@/types").TarotSpreadResponse>("POST", "/tarot/draw", {
      spread_type,
    }).then(rewriteSpread),
  interpret: (reading_id: number) =>
    request<import("@/types").TarotInterpretationResponse>(
      "POST",
      `/tarot/interpret/${reading_id}`,
    ),
  history: () =>
    request<import("@/types").TarotHistoryItem[]>("GET", "/tarot/history"),
  getReading: (reading_id: number) =>
    request<import("@/types").TarotSpreadResponse>(
      "GET",
      `/tarot/readings/${reading_id}`,
    ).then(rewriteSpread),
};

// ── News ───────────────────────────────────────────────────────────────────────
export const newsApi = {
  list: (params?: { category?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.category) qs.set("category", params.category);
    if (params?.limit) qs.set("limit", String(params.limit));
    const tail = qs.toString() ? `?${qs.toString()}` : "";
    return request<import("@/types").NewsPreview[]>("GET", `/news${tail}`);
  },
  get: (id: number) =>
    request<import("@/types").NewsItem>("GET", `/news/${id}`),
};

// ── Glossary ───────────────────────────────────────────────────────────────────
export const glossaryApi = {
  list: (params?: { category?: string; q?: string }) => {
    const qs = new URLSearchParams();
    if (params?.category) qs.set("category", params.category);
    if (params?.q) qs.set("q", params.q);
    const tail = qs.toString() ? `?${qs.toString()}` : "";
    return request<import("@/types").GlossaryTermShort[]>(
      "GET",
      `/glossary${tail}`,
    );
  },
  get: (slug: string) =>
    request<import("@/types").GlossaryTermFull>("GET", `/glossary/${slug}`),
};

// ── Synastry ───────────────────────────────────────────────────────────────────
export const synastryApi = {
  createRequest: () =>
    request<import("@/types").SynastryRequestOut>("POST", "/synastry/request"),
  pending: () =>
    request<import("@/types").SynastryPending[]>("GET", "/synastry/pending"),
  inviteInfo: (token: string) =>
    request<import("@/types").SynastryInviteInfo>(
      "GET",
      `/synastry/invite/${token}`,
    ),
  accept: (token: string) =>
    request<import("@/types").SynastryResult>(
      "POST",
      `/synastry/accept/${token}`,
    ),
  result: (id: number) =>
    request<import("@/types").SynastryResult>("GET", `/synastry/result/${id}`),
  manual: (payload: import("@/types").SynastryManualInput) =>
    request<import("@/types").SynastryResult>(
      "POST",
      "/synastry/manual",
      payload,
    ),
  history: () =>
    request<import("@/types").SynastryHistoryItem[]>(
      "GET",
      "/synastry/history",
    ),
  hideHistoryItem: (id: number) =>
    request<void>("DELETE", `/synastry/history/${id}`),
};

// ── Transits ───────────────────────────────────────────────────────────────────
export const transitsApi = {
  getCurrent: () =>
    request<import("@/types").TransitsResponse>("GET", "/transits/current"),
  getByDate: (date: string) =>
    request<import("@/types").TransitsResponse>(
      "GET",
      `/transits/date?date=${date}`,
    ),
};

// ── Payments ───────────────────────────────────────────────────────────────────
export const macApi = {
  draw: () =>
    request<import("@/types").MacReadingResponse>("POST", "/mac/draw"),
  today: () => request<import("@/types").MacTodayResponse>("GET", "/mac/today"),
  // 48-card deck flow — log a pick (card content stays client-side)
  pick: (body: { card_number: number; card_name: string; category: string }) =>
    request<import("@/types").MacPickResponse>("POST", "/mac/pick", body),
  picks: () =>
    request<import("@/types").MacPickHistoryItem[]>("GET", "/mac/picks"),
};

export const paymentsApi = {
  getProducts: () =>
    request<import("@/types").ProductInfo[]>("GET", "/payments/products"),
  createInvoice: (product_id: string) =>
    request<{ invoice_url: string; product_id: string; stars_amount: number }>(
      "POST",
      "/payments/invoice",
      { product_id },
    ),
};

export { ApiError };
