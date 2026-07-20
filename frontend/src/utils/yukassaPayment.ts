import WebApp from "@twa-dev/sdk";
import { paymentsApi } from "@/services/api";
import { track } from "@/services/analytics";

export type YukassaPaymentMethod = "bank_card" | "sbp";

/** Open YuKassa hosted checkout in the system browser (not the WebView). */
export async function payWithYukassa(
  productId: string,
  email: string,
  paymentMethod: YukassaPaymentMethod = "bank_card",
): Promise<void> {
  track("checkout_click", {
    productId,
    props: { method: paymentMethod },
  });
  try {
    const { confirmation_url } = await paymentsApi.createYukassaInvoice(
      productId,
      email,
      paymentMethod,
    );
    if (typeof WebApp.openLink === "function") {
      WebApp.openLink(confirmation_url, { try_instant_view: false });
    } else {
      window.open(confirmation_url, "_blank", "noopener");
    }
  } catch (e: unknown) {
    const message = formatYukassaError(e, paymentMethod);
    if (WebApp.showAlert) {
      WebApp.showAlert(message);
    } else {
      // eslint-disable-next-line no-alert
      alert(message);
    }
  }
}

/** @deprecated Use payWithYukassa(..., "bank_card") */
export async function payWithCard(
  productId: string,
  email: string,
): Promise<void> {
  return payWithYukassa(productId, email, "bank_card");
}

function formatYukassaError(
  e: unknown,
  paymentMethod: YukassaPaymentMethod,
): string {
  if (e && typeof e === "object" && "status" in e && "message" in e) {
    const status = (e as { status: number }).status;
    const message = String((e as { message: string }).message);
    if (status === 503) {
      if (message.toLowerCase().includes("not configured")) {
        return "Оплата в рублях временно недоступна — на сервере не настроена ЮKassa. Попробуйте звёзды Telegram или напишите в поддержку.";
      }
      if (message.toLowerCase().includes("ruble price")) {
        return "Для этого продукта не задана цена в рублях. Попробуйте оплату звёздами.";
      }
      return message;
    }
    if (message) return message;
  }
  if (e instanceof Error && e.message) return e.message;
  return paymentMethod === "sbp"
    ? "Не удалось открыть оплату через СБП. Попробуйте карту или звёзды."
    : "Не удалось открыть оплату картой. Попробуйте СБП или звёзды.";
}
