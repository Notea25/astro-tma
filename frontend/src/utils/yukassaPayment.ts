import WebApp from "@twa-dev/sdk";
import { paymentsApi } from "@/services/api";

/** Open YuKassa hosted checkout in the system browser (not the WebView).
 *  Telegram WebView cannot complete 3-D Secure / SBP bank-app handoffs. */
export async function payWithCard(
  productId: string,
  email: string,
): Promise<void> {
  try {
    const { confirmation_url } = await paymentsApi.createYukassaInvoice(
      productId,
      email,
    );
    if (typeof WebApp.openLink === "function") {
      // Never use Instant View for payment pages — bank redirects break.
      WebApp.openLink(confirmation_url, { try_instant_view: false });
    } else {
      window.open(confirmation_url, "_blank", "noopener");
    }
  } catch (e: unknown) {
    const message = formatYukassaError(e);
    if (WebApp.showAlert) {
      WebApp.showAlert(message);
    } else {
      // eslint-disable-next-line no-alert
      alert(message);
    }
  }
}

function formatYukassaError(e: unknown): string {
  if (e && typeof e === "object" && "status" in e && "message" in e) {
    const status = (e as { status: number }).status;
    const message = String((e as { message: string }).message);
    if (status === 503) {
      if (message.toLowerCase().includes("not configured")) {
        return "Оплата картой временно недоступна — на сервере не настроена ЮKassa. Попробуйте звёзды Telegram или напишите в поддержку.";
      }
      if (message.toLowerCase().includes("ruble price")) {
        return "Для этого продукта не задана цена в рублях. Попробуйте оплату звёздами.";
      }
      return message;
    }
    if (message) return message;
  }
  if (e instanceof Error && e.message) return e.message;
  return "Не удалось открыть оплату картой. Попробуйте звёзды или повторите позже.";
}
