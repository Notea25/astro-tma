import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useHaptic } from "@/hooks/useTelegram";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Bottom payment-method sheet — shown when the user taps a Premium plan or
 * a one-off product. Lets them pick Telegram Stars or a Russian bank card.
 *
 * When the user picks "Bank card" the sheet expands an inline form with an
 * email input — the fiscal receipt mandated by 54-ФЗ is sent there. We
 * never submit a card payment without a valid email.
 *
 * The component is presentation-only — buying logic lives in usePayment
 * (Stars) and payWithCard() callers (YuKassa).
 */
export function PaymentSheet({
  isOpen,
  item,
  starsPrice,
  rubPrice,
  defaultEmail,
  defaultExpandCard = false,
  onClose,
  onPayStars,
  onPayCard,
}: {
  isOpen: boolean;
  item: string;
  starsPrice: number;
  rubPrice: number | null;
  /** Pre-fills the receipt-email field (e.g. last email the user gave us). */
  defaultEmail?: string;
  /** When the sheet opens, expand the card-payment subform straight away
   *  (used by gates whose dedicated RUB button opens the sheet — the
   *  user already picked card, no point asking them to tap again). */
  defaultExpandCard?: boolean;
  onClose: () => void;
  onPayStars: () => void;
  onPayCard: (email: string) => void;
}) {
  const { impact } = useHaptic();
  const [cardExpanded, setCardExpanded] = useState(defaultExpandCard);
  const [starsExpanded, setStarsExpanded] = useState(false);
  const [email, setEmail] = useState(defaultEmail ?? "");
  const [touched, setTouched] = useState(false);

  // Reset local state when the sheet closes — next time it opens fresh.
  useEffect(() => {
    if (!isOpen) {
      setCardExpanded(defaultExpandCard);
      setStarsExpanded(false);
      setEmail(defaultEmail ?? "");
      setTouched(false);
    }
  }, [isOpen, defaultEmail, defaultExpandCard]);

  const emailValid = EMAIL_RE.test(email.trim());

  const handleStarsTap = () => {
    impact("medium");
    // Mutex with the card sub-form so only one "selected" block is visible.
    setCardExpanded(false);
    setStarsExpanded((v) => !v);
  };

  const handleStarsConfirm = () => {
    impact("medium");
    setStarsExpanded(false);
    onPayStars();
  };

  const handleCardTap = () => {
    impact("light");
    setStarsExpanded(false);
    setCardExpanded(true);
  };

  const handleCardConfirm = () => {
    impact("medium");
    setTouched(true);
    if (!emailValid) return;
    onPayCard(email.trim());
  };

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
              className={`payment-sheet__option payment-sheet__option--primary${
                starsExpanded ? " payment-sheet__option--active" : ""
              }`}
              onClick={handleStarsTap}
              aria-expanded={starsExpanded}
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

            <AnimatePresence initial={false}>
              {starsExpanded && (
                <motion.div
                  className="payment-sheet__confirm"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <p className="payment-sheet__confirm-hint">
                    Откроется окно Telegram. После подтверждения{" "}
                    <strong>{starsPrice} ⭐</strong> спишутся с баланса Telegram
                    Stars — отменить нельзя.
                  </p>
                  <button
                    type="button"
                    className="payment-sheet__confirm-cta"
                    onClick={handleStarsConfirm}
                  >
                    Подтвердить и оплатить · ⭐ {starsPrice}
                  </button>
                </motion.div>
              )}
            </AnimatePresence>

            {rubPrice != null && rubPrice > 0 && (
              <>
                <button
                  type="button"
                  className={`payment-sheet__option${
                    cardExpanded ? " payment-sheet__option--active" : ""
                  }`}
                  onClick={handleCardTap}
                  aria-expanded={cardExpanded}
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
                      {cardExpanded ? "Оплатить картой" : "Банковской картой"}
                    </span>
                    <span className="payment-sheet__option-desc">
                      ЮKassa · Visa / MC / МИР / СБП
                    </span>
                  </span>
                  <span className="payment-sheet__option-price">
                    {rubPrice} ₽
                  </span>
                </button>

                <AnimatePresence initial={false}>
                  {cardExpanded && (
                    <motion.div
                      className="payment-sheet__email"
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <label
                        className="payment-sheet__email-label"
                        htmlFor="payment-sheet-email"
                      >
                        Email для чека
                      </label>
                      <input
                        id="payment-sheet-email"
                        className={`payment-sheet__email-input${
                          touched && !emailValid
                            ? " payment-sheet__email-input--error"
                            : ""
                        }`}
                        type="email"
                        inputMode="email"
                        autoComplete="email"
                        placeholder="you@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        onBlur={() => setTouched(true)}
                        autoFocus
                      />
                      <p className="payment-sheet__email-hint">
                        Фискальный чек по 54-ФЗ придёт на этот адрес
                      </p>
                      {touched && !emailValid && (
                        <p className="payment-sheet__email-error">
                          Введите корректный email
                        </p>
                      )}
                      <button
                        type="button"
                        className="payment-sheet__confirm-cta"
                        onClick={handleCardConfirm}
                      >
                        Оплатить {rubPrice} ₽ картой
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </>
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
