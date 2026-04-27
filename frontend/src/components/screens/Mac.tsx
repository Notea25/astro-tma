import { useState, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { macApi } from "@/services/api";
import { useAppStore } from "@/stores/app";
import { useHaptic } from "@/hooks/useTelegram";
import { useTelegramBackButton } from "@/hooks/useTelegram";
import { MAC_INTRO } from "@/data/spread-config";
import type { MacReadingResponse } from "@/types";

type Step = "intro" | "deck" | "revealed";

export function Mac() {
  const { setScreen } = useAppStore();
  const { impact } = useHaptic();
  const [reading, setReading] = useState<MacReadingResponse | null>(null);
  const [step, setStep] = useState<Step>("intro");

  const handleBack = useCallback(() => {
    if (step === "revealed") {
      setReading(null);
      setStep("deck");
    } else if (step === "deck") {
      setStep("intro");
    } else {
      setScreen("discover", "back");
    }
  }, [step, setScreen]);

  useTelegramBackButton(handleBack, true);

  const drawMutation = useMutation({
    mutationFn: macApi.draw,
    onSuccess: (data) => {
      impact("success" as any);
      setReading(data);
      setStep("revealed");
    },
  });

  const handleDraw = () => {
    impact("medium");
    drawMutation.mutate();
  };

  const reset = () => {
    setReading(null);
    setStep("deck");
    drawMutation.reset();
  };

  return (
    <div className="screen mac-screen">
      <div className="screen-header screen-header--with-back">
        <button className="back-btn" onClick={handleBack} aria-label="Назад">
          <svg
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M13 4l-6 6 6 6" />
          </svg>
        </button>
        <h2 className="screen-title">
          {step === "revealed" ? "Ваша карта" : "Зеркало Души"}
        </h2>
      </div>

      <div className="screen-content">
        {step === "intro" && (
          <motion.div
            className="spread-intro-v2"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="spread-intro-v2__preview">
              <div
                className="spread-intro-v2__preview-stage"
                style={{ width: 56, height: 84 }}
              >
                <div
                  className="spread-intro-v2__mini-card card-back-pattern--mirror"
                  style={{ left: 0, top: 0, width: 56, height: 84 }}
                />
              </div>
            </div>

            <div className="spread-intro-v2__frame">
              <p
                className="spread-intro-v2__intro-text"
                dangerouslySetInnerHTML={{ __html: MAC_INTRO.intro }}
              />
            </div>

            <motion.button
              className="btn-primary spread-intro-v2__start-btn"
              onClick={() => setStep("deck")}
              whileTap={{ scale: 0.96 }}
            >
              Перейти к раскладу
            </motion.button>
          </motion.div>
        )}

        {step === "deck" && drawMutation.isPending && (
          <LoadingSpinner message="Выбираем вашу карту..." />
        )}

        {step === "deck" && drawMutation.isError && (
          <div className="error-state">
            <svg
              width="32"
              height="32"
              viewBox="0 0 32 32"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity="0.5"
            >
              <circle cx="16" cy="16" r="13" />
              <line x1="16" y1="10" x2="16" y2="17" />
              <circle cx="16" cy="21" r="1" fill="currentColor" stroke="none" />
            </svg>
            <p>Не удалось выбрать карту. Попробуйте ещё раз.</p>
            <button className="btn-ghost" onClick={() => drawMutation.reset()}>
              Повторить
            </button>
          </div>
        )}

        {step === "deck" &&
          !drawMutation.isPending &&
          !drawMutation.isError && (
            <motion.div
              className="mac-draw-prompt"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className="mac-intro">
                <p>Закройте глаза. Сделайте глубокий вдох.</p>
                <p>
                  Задайте себе вопрос — или просто позвольте карте найти вас.
                </p>
              </div>

              <div className="mac-deck">
                {[3, 2, 1, 0].map((i) => (
                  <motion.div
                    key={i}
                    className="mac-deck-card"
                    style={{
                      transform: `rotate(${(i - 1.5) * 4}deg)`,
                      zIndex: i,
                    }}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{
                      duration: 0.35,
                      delay: i * 0.06,
                      ease: "easeOut",
                    }}
                    onClick={i === 0 ? handleDraw : undefined}
                  >
                    <span className="mac-deck-symbol">☽</span>
                  </motion.div>
                ))}
              </div>

              <motion.button
                className="btn-primary btn-draw"
                onClick={handleDraw}
                whileTap={{ scale: 0.96 }}
              >
                Вытянуть карту
              </motion.button>
            </motion.div>
          )}

        {step === "revealed" && reading && (
          <div className="mac-revealed">
            {/* Remaining deck behind (stays visible) */}
            <div className="mac-deck mac-deck--faded" aria-hidden="true">
              {[3, 2, 1].map((i) => (
                <div
                  key={i}
                  className="mac-deck-card"
                  style={{
                    transform: `rotate(${(i - 1.5) * 4}deg)`,
                    zIndex: i,
                  }}
                >
                  <span className="mac-deck-symbol">☽</span>
                </div>
              ))}
            </div>

            {/* Card — expanded immediately with full content, no tap required */}
            <motion.div
              className="mac-card mac-card--revealed"
              initial={{ scale: 0.7, opacity: 0, rotateY: 180 }}
              animate={{ scale: 1, opacity: 1, rotateY: 0 }}
              transition={{ duration: 0.7, type: "spring" }}
            >
              <div className="mac-card__emoji">{reading.card.emoji}</div>
              <h3 className="mac-card__name">{reading.card.name_ru}</h3>

              <motion.div
                className="mac-card__content"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25, duration: 0.4 }}
              >
                <p className="mac-card__description">
                  {reading.card.description_ru}
                </p>

                <div className="mac-card__question">
                  <span className="mac-card__label">
                    Вопрос для размышления
                  </span>
                  <p>{reading.card.question_ru}</p>
                </div>

                <div className="mac-card__affirmation">
                  <span className="mac-card__label">Аффирмация</span>
                  <p>{reading.card.affirmation_ru}</p>
                </div>
              </motion.div>
            </motion.div>

            <motion.button
              className="btn-secondary btn-with-icon"
              onClick={reset}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 15 15"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M1.5 7.5A6 6 0 0 1 13 4.5M13.5 7.5A6 6 0 0 1 2 10.5" />
                <polyline points="11,2 13,4.5 10.5,6.5" />
                <polyline points="4,12.5 2,10.5 4.5,8.5" />
              </svg>
              Новая карта
            </motion.button>
          </div>
        )}
      </div>
    </div>
  );
}
