/**
 * Product analytics — dual-write to our API + optional PostHog.
 *
 * Own DB powers /api/admin/analytics.html funnels.
 * PostHog (if VITE_POSTHOG_KEY) adds retention / path analysis.
 */

import WebApp from "@twa-dev/sdk";

type TrackProps = Record<string, string | number | boolean | null | undefined>;

type QueuedEvent = {
  event: string;
  product_id?: string;
  props?: TrackProps;
};

const QUEUE: QueuedEvent[] = [];
const FLUSH_MS = 2000;
let flushTimer: ReturnType<typeof setTimeout> | null = null;
let posthogReady = false;

function apiBase(): string {
  const configured = (
    (import.meta.env.VITE_API_URL as string | undefined) ?? ""
  )
    .trim()
    .replace(/\/+$/, "");
  if (!configured) return "/api";
  return configured.endsWith("/api") ? configured : `${configured}/api`;
}

function initData(): string {
  try {
    return WebApp.initData || "";
  } catch {
    return "";
  }
}

async function ensurePosthog(distinctId: string | number): Promise<void> {
  const key = (import.meta.env.VITE_POSTHOG_KEY as string | undefined)?.trim();
  if (!key || posthogReady) return;
  try {
    const posthog = (await import("posthog-js")).default;
    const host =
      (import.meta.env.VITE_POSTHOG_HOST as string | undefined)?.trim() ||
      "https://eu.i.posthog.com";
    posthog.init(key, {
      api_host: host,
      persistence: "localStorage",
      autocapture: false,
      capture_pageview: false,
      capture_pageleave: false,
    });
    posthog.identify(String(distinctId));
    posthogReady = true;
  } catch {
    /* PostHog optional — never break the app */
  }
}

async function flushQueue(): Promise<void> {
  if (QUEUE.length === 0) return;
  const batch = QUEUE.splice(0, QUEUE.length);
  const init = initData();
  if (!init) return;

  try {
    await fetch(`${apiBase()}/events`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Init-Data": init,
      },
      body: JSON.stringify({
        events: batch.map((e) => ({
          event: e.event,
          product_id: e.product_id ?? null,
          props: e.props ?? null,
        })),
      }),
      keepalive: true,
    });
  } catch {
    /* drop on network error — analytics must not block UX */
  }

  if (posthogReady) {
    try {
      const posthog = (await import("posthog-js")).default;
      for (const e of batch) {
        posthog.capture(e.event, {
          product_id: e.product_id,
          ...e.props,
        });
      }
    } catch {
      /* ignore */
    }
  }
}

function scheduleFlush(): void {
  if (flushTimer) return;
  flushTimer = setTimeout(() => {
    flushTimer = null;
    void flushQueue();
  }, FLUSH_MS);
}

/** Identify user for PostHog (call after /users/me). */
export function identifyAnalyticsUser(userId: number): void {
  void ensurePosthog(userId);
}

export function track(
  event: string,
  opts?: { productId?: string; props?: TrackProps },
): void {
  QUEUE.push({
    event,
    product_id: opts?.productId,
    props: opts?.props,
  });
  scheduleFlush();
}

export function trackScreen(screen: string): void {
  track("screen_view", { props: { screen } });
}

/** Flush immediately (e.g. before opening payment sheet). */
export function flushAnalytics(): void {
  if (flushTimer) {
    clearTimeout(flushTimer);
    flushTimer = null;
  }
  void flushQueue();
}

if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") flushAnalytics();
  });
}
