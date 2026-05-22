import { useQuery } from "@tanstack/react-query";
import { useCallback } from "react";
import { usersApi } from "@/services/api";
import { useAppStore } from "@/stores/app";

/**
 * Returns true if the current user is entitled to `productId` content —
 * either they hold an active Premium subscription OR they bought this
 * specific product once. Keeps the list of completed purchases in
 * React Query cache so the rest of the UI can stay in sync after a
 * successful Stars payment.
 */
export function useEntitlement(productId: string | undefined | null): boolean {
  const isPremium = useAppStore((s) => s.user?.is_premium ?? false);
  const { data } = useQuery({
    queryKey: ["my-purchases"],
    queryFn: usersApi.getPurchases,
    staleTime: 1000 * 60 * 5,
  });

  if (isPremium) return true;
  if (!productId || !data) return false;

  return data.purchases.some(
    (p) => p.product_id === productId && p.status === "completed",
  );
}

/**
 * Same backing data as `useEntitlement`, exposed as a callable predicate
 * so a single component can check several products in one render (e.g.
 * the period-tab lock icons on the Horoscopes / Transits screens).
 */
export function useEntitlementChecker(): (productId: string) => boolean {
  const isPremium = useAppStore((s) => s.user?.is_premium ?? false);
  const { data } = useQuery({
    queryKey: ["my-purchases"],
    queryFn: usersApi.getPurchases,
    staleTime: 1000 * 60 * 5,
  });

  return useCallback(
    (productId: string) => {
      if (isPremium) return true;
      if (!data) return false;
      return data.purchases.some(
        (p) => p.product_id === productId && p.status === "completed",
      );
    },
    [isPremium, data],
  );
}
