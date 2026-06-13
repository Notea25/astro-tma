import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import WebApp from "@twa-dev/sdk";
import { HeaderAvatarButton } from "@/components/ui/HeaderAvatarButton";
import { PaymentSheet } from "@/components/ui/PaymentSheet";
import { paymentsApi } from "@/services/api";
import { useAppStore } from "@/stores/app";
import { useHaptic } from "@/hooks/useTelegram";
import { usePayment } from "@/hooks/usePayment";

/** Create a YuKassa hosted-payment session and open the URL outside the
 *  Mini App. Telegram WebView struggles with 3DS popups, so we always
 *  redirect to the system browser via openLink. The buyer's email is
 *  required so YuKassa can issue the 54-ФЗ fiscal receipt. */
async function payWithCard(productId: string, email: string): Promise<void> {
  try {
    const { confirmation_url } = await paymentsApi.createYukassaInvoice(
      productId,
      email,
    );
    WebApp.openLink(confirmation_url);
  } catch (e: unknown) {
    const message =
      e instanceof Error && e.message
        ? e.message
        : "Не удалось открыть оплату картой. Попробуйте звёзды или повторите позже.";
    if (WebApp.showAlert) {
      WebApp.showAlert(message);
    } else {
      // eslint-disable-next-line no-alert
      alert(message);
    }
  }
}

const BENEFITS = [
  "Все гороскопы: сегодня, завтра, неделя, месяц",
  "Полная натальная карта + PDF-отчёт",
  "Расклады Таро без лимитов",
  "Синастрия и совместимость",
  "Транзиты на неделю и месяц",
  "Матрица судьбы — полный разбор",
];

type SheetTarget = {
  productId: string;
  item: string;
  stars: number;
  rub: number | null;
};

/**
 * Premium / Stars screen — overview of available paid products and the
 * monthly subscription. Reads the catalog from the backend and renders
 * each item with its price and description.
 */
export function Premium() {
  const { user } = useAppStore();
  const { impact } = useHaptic();
  const { purchase, loading } = usePayment();
  const [sheet, setSheet] = useState<SheetTarget | null>(null);

  const { data: products = [], isLoading } = useQuery({
    queryKey: ["payments-products"],
    queryFn: paymentsApi.getProducts,
    staleTime: 1000 * 60 * 5,
  });

  const monthly = products.find((p) => p.id === "subscription_month");
  const yearly = products.find((p) => p.id === "subscription_year");
  const subscriptionIds = new Set(
    [monthly?.id, yearly?.id].filter(Boolean) as string[],
  );
  const oneOffs = products.filter((p) => !subscriptionIds.has(p.id));
  const yearlySavingsPct =
    monthly && yearly
      ? Math.max(0, Math.round((1 - yearly.stars / (monthly.stars * 12)) * 100))
      : 0;

  const openSheet = (t: SheetTarget) => {
    impact("light");
    setSheet(t);
  };
  const closeSheet = () => setSheet(null);

  const handlePayStars = async () => {
    if (!sheet) return;
    const id = sheet.productId;
    setSheet(null);
    await purchase(id);
  };
  const handlePayCard = async (email: string) => {
    if (!sheet) return;
    const id = sheet.productId;
    setSheet(null);
    await payWithCard(id, email);
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
          style={{ textAlign: "center" }}
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
              : "Весь космос в одной подписке — гороскопы, карта, Таро и совместимость без ограничений."}
          </p>
        </motion.div>

        {!user?.is_premium && (monthly || yearly) && (
          <>
            <div className="pf-plans2">
              {monthly && (
                <button
                  type="button"
                  className="pf-card"
                  onClick={() =>
                    openSheet({
                      productId: monthly.id,
                      item: "Премиум · Месяц",
                      stars: monthly.stars,
                      rub: monthly.price_rub ?? null,
                    })
                  }
                  disabled={loading}
                >
                  <div className="pf-card__name">Месяц</div>
                  <div className="pf-card__price">
                    <span className="pf-card__stars">⭐ {monthly.stars}</span>
                    {monthly.price_rub != null && (
                      <>
                        <span className="pf-card__sep">/</span>
                        <span className="pf-card__rub">
                          {monthly.price_rub} ₽
                        </span>
                      </>
                    )}
                  </div>
                  <div className="pf-card__period">30 дней</div>
                </button>
              )}
              {yearly && (
                <button
                  type="button"
                  className="pf-card pf-card--best"
                  onClick={() =>
                    openSheet({
                      productId: yearly.id,
                      item: "Премиум · Год",
                      stars: yearly.stars,
                      rub: yearly.price_rub ?? null,
                    })
                  }
                  disabled={loading}
                >
                  {yearlySavingsPct > 0 && (
                    <span className="pf-card__badge">
                      Выгодно · −{yearlySavingsPct}%
                    </span>
                  )}
                  <div className="pf-card__name">Год</div>
                  <div className="pf-card__price">
                    <span className="pf-card__stars">⭐ {yearly.stars}</span>
                    {yearly.price_rub != null && (
                      <>
                        <span className="pf-card__sep">/</span>
                        <span className="pf-card__rub">
                          {yearly.price_rub} ₽
                        </span>
                      </>
                    )}
                  </div>
                  <div className="pf-card__period">365 дней</div>
                </button>
              )}
            </div>
            <p className="pf-pay-note">
              Оплата звёздами Telegram или картой в рублях
            </p>
          </>
        )}

        {!user?.is_premium && (
          <>
            <h2 className="section-title">Что входит в Premium</h2>
            <ul className="pf-bens">
              {BENEFITS.map((b) => (
                <li key={b} className="pf-ben">
                  <span className="pf-ben__ic" aria-hidden="true">
                    <svg
                      viewBox="0 0 12 12"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M2.5 6.2l2.3 2.3 4.7-5" />
                    </svg>
                  </span>
                  <span>{b}</span>
                </li>
              ))}
            </ul>
          </>
        )}

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
                  whileTap={{ scale: 0.99 }}
                  onClick={() =>
                    openSheet({
                      productId: p.id,
                      item: p.name,
                      stars: p.stars,
                      rub: p.price_rub ?? null,
                    })
                  }
                  disabled={loading || user?.is_premium}
                >
                  <div className="premium-list__main">
                    <div className="premium-list__name">{p.name}</div>
                    <div className="premium-list__desc">{p.description}</div>
                  </div>
                  <span
                    className="premium-list__cart"
                    aria-label="Купить"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M2.5 3.5H5l2.1 10.6a1.5 1.5 0 0 0 1.5 1.2h8.1a1.5 1.5 0 0 0 1.5-1.18L21 7H6" />
                      <circle cx="9.5" cy="19.2" r="1.45" />
                      <circle cx="17" cy="19.2" r="1.45" />
                    </svg>
                  </span>
                </motion.button>
              ))}
            </div>
          </>
        )}
      </div>

      <PaymentSheet
        isOpen={sheet != null}
        item={sheet?.item ?? ""}
        starsPrice={sheet?.stars ?? 0}
        rubPrice={sheet?.rub ?? null}
        onClose={closeSheet}
        onPayStars={handlePayStars}
        onPayCard={handlePayCard}
      />
    </div>
  );
}
