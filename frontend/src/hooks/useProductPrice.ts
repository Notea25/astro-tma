import { useQuery } from "@tanstack/react-query";
import { paymentsApi } from "@/services/api";

const PRODUCTS_QUERY = {
  queryKey: ["payments-products"] as const,
  queryFn: paymentsApi.getProducts,
  staleTime: 1000 * 60 * 5,
};

/**
 * Single source of truth for product prices on the frontend. Fetches
 * the catalogue once (with admin overrides applied) and exposes a
 * lookup. Components stop hard-coding `stars: 25` — the price they
 * render always matches what Telegram will actually charge.
 */
export function useProductPrice(
  productId: string | undefined | null,
): number | undefined {
  const { data } = useQuery(PRODUCTS_QUERY);

  if (!productId || !data) return undefined;
  return data.products.find((p) => p.id === productId)?.stars;
}

/** True when the backend has YuKassa credentials — ruble buttons may show. */
export function useCardPaymentsAvailable(): boolean {
  const { data } = useQuery(PRODUCTS_QUERY);
  return data?.card_payments_available ?? false;
}

/**
 * Ruble price counterpart. Returns undefined when card payments are
 * disabled on the backend or no positive ruble price is configured.
 */
export function useProductPriceRub(
  productId: string | undefined | null,
): number | undefined {
  const { data } = useQuery(PRODUCTS_QUERY);

  if (!productId || !data?.card_payments_available) return undefined;
  const found = data.products.find((p) => p.id === productId);
  if (!found) return undefined;
  return found.price_rub && found.price_rub > 0 ? found.price_rub : undefined;
}
