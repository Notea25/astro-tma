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

/** Per-user YuKassa eligibility — ruble buttons may show only when true. */
export function useCardPaymentsAvailable(): boolean {
  const { data } = useQuery(PRODUCTS_QUERY);
  return data?.card_payments_available ?? false;
}

/**
 * Ruble price counterpart. Returns undefined when YuKassa payments are
 * unavailable for this user or no positive ruble price is configured.
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
