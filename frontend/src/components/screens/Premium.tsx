import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { HeaderAvatarButton } from "@/components/ui/HeaderAvatarButton";
import { paymentsApi } from "@/services/api";
import { useAppStore } from "@/stores/app";
import { useHaptic } from "@/hooks/useTelegram";
import { usePayment } from "@/hooks/usePayment";

/**
 * Premium / Stars screen — overview of available paid products and the
 * monthly subscription. Reads the catalog from the backend and renders
 * each item with its price and description.
 */
export function Premium() {
  const { user } = useAppStore();
  const { impact } = useHaptic();
  const { purchase, loading } = usePayment();

  const { data: products = [], isLoading } = useQuery({
    queryKey: ["payments-products"],
    queryFn: paymentsApi.getProducts,
    staleTime: 1000 * 60 * 5,
  });

  const subscription = products.find(
    (p) => p.type === "subscription" || p.id.includes("subscription"),
  );
  const oneOffs = products.filter((p) => p !== subscription);

  const handleBuy = async (productId: string) => {
    impact("medium");
    await purchase(productId);
  };

  return (
    <div className="screen premium-screen">
      <div className="screen-header">
        <div>
          <h1 className="screen-title">Звёзды</h1>
          <p className="screen-subtitle">Премиум-функции и подписка</p>
        </div>
        <HeaderAvatarButton />
      </div>

      <div className="screen-content">
        {/* Premium status / hero */}
        <motion.div
          className="premium-hero glass-gold"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="premium-hero__icon" aria-hidden="true">
            ✦
          </div>
          <div className="premium-hero__title">
            {user?.is_premium ? "Премиум активен" : "ASTRO Premium"}
          </div>
          <p className="premium-hero__desc">
            {user?.is_premium
              ? "Все разделы и подробные прогнозы открыты для вас."
              : "Доступ ко всем гороскопам, полной натальной карте, раскладам Таро и синастрии."}
          </p>
          {!user?.is_premium && subscription && (
            <button
              className="btn-stars premium-hero__cta"
              onClick={() => handleBuy(subscription.id)}
              disabled={loading}
            >
              {loading ? "⏳ Открываем…" : `⭐ ${subscription.stars} / мес`}
            </button>
          )}
        </motion.div>

        {/* Catalogue */}
        {isLoading ? (
          <div className="premium-list-skeleton">
            <div className="skeleton-card" />
            <div className="skeleton-card" />
            <div className="skeleton-card" />
          </div>
        ) : (
          <>
            <h2 className="section-title">Открыть отдельно</h2>
            <div className="premium-list">
              {oneOffs.map((p) => (
                <motion.button
                  key={p.id}
                  type="button"
                  className="premium-list__item"
                  onClick={() => handleBuy(p.id)}
                  whileTap={{ scale: 0.98 }}
                  disabled={loading || user?.is_premium}
                >
                  <div className="premium-list__main">
                    <div className="premium-list__name">{p.name}</div>
                    <div className="premium-list__desc">{p.description}</div>
                  </div>
                  <div className="premium-list__price">⭐ {p.stars}</div>
                </motion.button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
