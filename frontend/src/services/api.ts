/**
 * API client — thin wrapper over fetch.
 * Automatically injects X-Init-Data header (Telegram auth).
 * All methods throw on non-2xx — React Query catches them.
 */

import WebApp from "@twa-dev/sdk";

const BASE_URL = import.meta.env.VITE_API_URL || "/api";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
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
    const detail = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(response.status, detail.detail ?? response.statusText);
  }

  return response.json() as Promise<T>;
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
  downloadPdf: async () => {
    const res = await fetch(`${BASE_URL}/natal/pdf`, {
      headers: { "X-Init-Data": WebApp.initData },
    });
    if (!res.ok) throw new ApiError(res.status, "PDF generation failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    // Try standard download
    const a = document.createElement("a");
    a.href = url;
    a.download = "natal-chart.pdf";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // Fallback: open in new tab (for Telegram WebView)
    setTimeout(() => {
      window.open(url, "_blank");
    }, 500);
  },
};

// ── Tarot ──────────────────────────────────────────────────────────────────────
export const tarotApi = {
  draw: (spread_type: string) =>
    request<import("@/types").TarotSpreadResponse>("POST", "/tarot/draw", {
      spread_type,
    }),
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
    ),
};

// ── Compatibility ──────────────────────────────────────────────────────────────
export const compatibilityApi = {
  get: (sign_a: string, sign_b: string) =>
    request<import("@/types").CompatibilityResponse>("POST", "/compatibility", {
      sign_a,
      sign_b,
    }),
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
  today: () =>
    request<import("@/types").MacTodayResponse>("GET", "/mac/today"),
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
