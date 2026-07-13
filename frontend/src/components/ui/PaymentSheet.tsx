import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import WebApp from "@twa-dev/sdk";
import { useHaptic } from "@/hooks/useTelegram";
import type { YukassaPaymentMethod } from "@/utils/yukassaPayment";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isIosDevice(): boolean {
  if (WebApp.platform === "ios") return true;
  return /iPhone|iPad|iPod/i.test(navigator.userAgent);
}

/**
 * Bottom payment-method sheet — Stars, bank card, or SBP (rubles).
 */
export function PaymentSheet({
  isOpen,
  item,
  starsPrice,
  rubPrice,
  defaultEmail,
  defaultExpandCard = false,
  defaultRubMethod = null,
  onClose,
  onPayStars,
  onPayRub,
}: {
  isOpen: boolean;
  item: string;
  starsPrice: number;
  rubPrice: number | null;
  defaultEmail?: string;
  /** @deprecated Use defaultRubMethod */
  defaultExpandCard?: boolean;
  defaultRubMethod?: YukassaPaymentMethod | null;
  onClose: () => void;
  onPayStars: () => void;
  onPayRub: (email: string, method: YukassaPaymentMethod) => void;
}) {
  const initialRubMethod: YukassaPaymentMethod | null =
    defaultRubMethod ?? (defaultExpandCard ? "bank_card" : null);

  const { impact } = useHaptic();
  const [rubMethod, setRubMethod] = useState<YukassaPaymentMethod | null>(
    initialRubMethod,
  );
  const [starsExpanded, setStarsExpanded] = useState(false);
  const [email, setEmail] = useState(defaultEmail ?? "");
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      setRubMethod(initialRubMethod);
      setStarsExpanded(false);
      setEmail(defaultEmail ?? "");
      setTouched(false);
    }
  }, [isOpen, defaultEmail, initialRubMethod]);

  const emailValid = EMAIL_RE.test(email.trim());
  const showIosSbpHint = rubMethod === "sbp" && isIosDevice();

  const handleStarsTap = () => {
    impact("medium");
    setRubMethod(null);
    setStarsExpanded((v) => !v);
  };

  const handleStarsConfirm = () => {
    impact("medium");
    setStarsExpanded(false);
    onPayStars();
  };

  const handleRubTap = (method: YukassaPaymentMethod) => {
    impact("light");
    setStarsExpanded(false);
    setRubMethod(method);
  };

  const handleRubConfirm = () => {
    if (!rubMethod) return;
    impact("medium");
    setTouched(true);
    if (!emailValid) return;
    onPayRub(email.trim(), rubMethod);
  };

  const rubEmailBlock = rubMethod && rubPrice != null && rubPrice > 0 && (
    <motion.div
      className="payment-sheet__email"
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.2 }}
    >
      <label className="payment-sheet__email-label" htmlFor="payment-sheet-email">
        Email для чека
      </label>
      <input
        id="payment-sheet-email"
        className={`payment-sheet__email-input${
          touched && !emailValid ? " payment-sheet__email-input--error" : ""
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
        <p className="payment-sheet__email-error">Введите корректный email</p>
      )}
      {showIosSbpHint && (
        <p className="payment-sheet__confirm-hint">
          На iPhone переход в приложение банка иногда не срабатывает. Если
          увидите ошибку Safari — вернитесь и оплатите{" "}
          <strong>банковской картой</strong>.
        </p>
      )}
      <button
        type="button"
        className="payment-sheet__confirm-cta"
        onClick={handleRubConfirm}
      >
        {rubMethod === "sbp"
          ? `Оплатить ${rubPrice} ₽ через СБП`
          : `Оплатить ${rubPrice} ₽ картой`}
      </button>
    </motion.div>
  );

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
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 3l2.5 5.6 6.1.6-4.6 4 1.4 6L12 16.9 6.6 19.2l1.4-6-4.6-4 6.1-.6z" />
                </svg>
              </span>
              <span className="payment-sheet__option-main">
                <span className="payment-sheet__option-name">Telegram Stars</span>
                <span className="payment-sheet__option-desc">
                  Оплата звёздами Telegram
                </span>
              </span>
              <span className="payment-sheet__option-price">⭐ {starsPrice}</span>
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
                    rubMethod === "bank_card" ? " payment-sheet__option--active" : ""
                  }`}
                  onClick={() => handleRubTap("bank_card")}
                  aria-expanded={rubMethod === "bank_card"}
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
                      Visa / MC / МИР — ввод номера карты
                    </span>
                  </span>
                  <span className="payment-sheet__option-price">{rubPrice} ₽</span>
                </button>

                <button
                  type="button"
                  className={`payment-sheet__option${
                    rubMethod === "sbp" ? " payment-sheet__option--active" : ""
                  }`}
                  onClick={() => handleRubTap("sbp")}
                  aria-expanded={rubMethod === "sbp"}
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
                      <path d="M4 7h6l2 3h8" />
                      <path d="M5 7l2 10h10l2-7" />
                      <circle cx="9" cy="19" r="1.5" />
                      <circle cx="17" cy="19" r="1.5" />
                    </svg>
                  </span>
                  <span className="payment-sheet__option-main">
                    <span className="payment-sheet__option-name">СБП</span>
                    <span className="payment-sheet__option-desc">
                      Система быстрых платежей · приложение банка
                    </span>
                  </span>
                  <span className="payment-sheet__option-price">{rubPrice} ₽</span>
                </button>

                <AnimatePresence initial={false}>{rubEmailBlock}</AnimatePresence>
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
