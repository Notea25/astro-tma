import { motion, AnimatePresence } from "framer-motion";
import { useHaptic } from "@/hooks/useTelegram";

/**
 * Bottom payment-method sheet — shown when the user taps a Premium plan or
 * a one-off product. Lets them pick Telegram Stars or a Russian bank card.
 *
 * The component is presentation-only — buying logic lives in usePayment
 * (Stars) and a future YuKassa hook (card). Pass two callbacks; `onPayCard`
 * can no-op via an alert until YuKassa is wired in production.
 */
export function PaymentSheet({
  isOpen,
  item,
  starsPrice,
  rubPrice,
  onClose,
  onPayStars,
  onPayCard,
}: {
  isOpen: boolean;
  item: string;
  starsPrice: number;
  rubPrice: number | null;
  onClose: () => void;
  onPayStars: () => void;
  onPayCard: () => void;
}) {
  const { impact } = useHaptic();

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className="payment-sheet__backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="payment-sheet"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 280 }}
            role="dialog"
            aria-label="Способ оплаты"
          >
            <div className="payment-sheet__handle" aria-hidden="true" />
            <h3 className="payment-sheet__title">Способ оплаты</h3>
            <p className="payment-sheet__sub">{item}</p>

            <button
              type="button"
              className="payment-sheet__option payment-sheet__option--primary"
              onClick={() => {
                impact("medium");
                onPayStars();
              }}
            >
              <span className="payment-sheet__option-ic" aria-hidden="true">
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M12 3l2.5 5.6 6.1.6-4.6 4 1.4 6L12 16.9 6.6 19.2l1.4-6-4.6-4 6.1-.6z" />
                </svg>
              </span>
              <span className="payment-sheet__option-main">
                <span className="payment-sheet__option-name">Telegram Stars</span>
                <span className="payment-sheet__option-desc">
                  Оплата звёздами Telegram
                </span>
              </span>
              <span className="payment-sheet__option-price">
                ⭐ {starsPrice}
              </span>
            </button>

            {rubPrice != null && (
              <button
                type="button"
                className="payment-sheet__option"
                onClick={() => {
                  impact("light");
                  onPayCard();
                }}
              >
                <span className="payment-sheet__option-ic" aria-hidden="true">
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <rect x="2" y="5" width="20" height="14" rx="2" />
                    <path d="M2 10h20" />
                    <path d="M6 15h4" />
                  </svg>
                </span>
                <span className="payment-sheet__option-main">
                  <span className="payment-sheet__option-name">
                    Банковской картой
                  </span>
                  <span className="payment-sheet__option-desc">
                    ЮKassa · Visa / MC / МИР / СБП
                  </span>
                </span>
                <span className="payment-sheet__option-price">
                  {rubPrice} ₽
                </span>
              </button>
            )}

            <button
              type="button"
              className="payment-sheet__cancel"
              onClick={() => {
                impact("light");
                onClose();
              }}
            >
              Отмена
            </button>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
