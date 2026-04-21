/**
 * Telegram WebApp SDK hooks.
 * Centralises all WebApp interactions — components never import SDK directly.
 */

import { useEffect, useCallback } from "react";
import WebApp from "@twa-dev/sdk";

export function useTelegramUser() {
  const user = WebApp.initDataUnsafe?.user;
  return {
    id: user?.id ?? 0,
    firstName: user?.first_name ?? "",
    lastName: user?.last_name,
    username: user?.username,
    isPremium: user?.is_premium ?? false,
    photoUrl: user?.photo_url,
    languageCode: user?.language_code ?? "ru",
  };
}

export function useTelegramTheme() {
  return {
    colorScheme: WebApp.colorScheme, // 'light' | 'dark'
    bgColor: WebApp.backgroundColor,
    themeParams: WebApp.themeParams,
  };
}

export function useTelegramBackButton(onBack: () => void, enabled = true) {
  useEffect(() => {
    if (!enabled) {
      WebApp.BackButton.hide();
      return;
    }
    WebApp.BackButton.show();
    WebApp.BackButton.onClick(onBack);
    return () => {
      WebApp.BackButton.offClick(onBack);
      WebApp.BackButton.hide();
    };
  }, [onBack, enabled]);
}

export function useHaptic() {
  return {
    impact: (
      style: "light" | "medium" | "heavy" | "rigid" | "soft" = "light",
    ) => {
      try {
        WebApp.HapticFeedback.impactOccurred(style);
      } catch (e) {
        /* not available */
      }
    },
    notification: (type: "error" | "success" | "warning") => {
      try {
        WebApp.HapticFeedback.notificationOccurred(type);
      } catch (e) {
        /* not available */
      }
    },
    selection: () => {
      try {
        WebApp.HapticFeedback.selectionChanged();
      } catch (e) {
        /* not available */
      }
    },
  };
}
export function useStarsPayment() {
  const { impact, notification } = useHaptic();

  const pay = useCallback(
    async (invoiceUrl: string): Promise<boolean> => {
      return new Promise((resolve) => {
        impact("medium");
        WebApp.openInvoice(invoiceUrl, (status) => {
          if (status === "paid") {
            notification("success");
            resolve(true);
          } else {
            // 'cancelled' | 'failed' | 'pending'
            notification(status === "cancelled" ? "warning" : "error");
            resolve(false);
          }
        });
      });
    },
    [impact, notification],
  );

  return { pay };
}

export function useStartParam(): string | null {
  const raw = (WebApp.initDataUnsafe as any)?.start_param;
  return typeof raw === "string" && raw.length > 0 ? raw : null;
}

export function useTelegramReady() {
  useEffect(() => {
    WebApp.ready();
    WebApp.expand();

    // Fullscreen mode (Bot API 8.0+)
    try {
      (WebApp as any).requestFullscreen?.();
    } catch {
      /* not supported in older clients */
    }

    // Prevent swipe-down to close
    try {
      (WebApp as any).disableVerticalSwipes?.();
    } catch {
      /* not supported */
    }
  }, []);
}
