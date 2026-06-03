import { useEntitlementStatus } from "@/hooks/useEntitlement";

/**
 * Compact badge: `✦ Premium` while any active subscription exists
 * (paid or admin-granted), nothing for free users.
 */
export function EntitlementBadge() {
  const status = useEntitlementStatus();
  if (!status.isPremium) return null;
  return (
    <span className="entitlement-badge entitlement-badge--paid">
      <span className="entitlement-badge__glyph" aria-hidden="true">✦</span>
      Premium
    </span>
  );
}
