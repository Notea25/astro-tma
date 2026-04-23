import { useState, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { PremiumGate } from "@/components/ui/PremiumGate";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { HeaderAvatarButton } from "@/components/ui/HeaderAvatarButton";
import { ThreeCardFlow } from "./ThreeCardFlow";
import { SpreadLayout } from "./SpreadLayout";
import { CelticCrossFlow } from "@/components/tarot/CelticCrossFlow";
import { CelticCrossDiagram } from "@/components/tarot/CelticCrossDiagram";
import { tarotApi } from "@/services/api";
import { useAppStore } from "@/stores/app";
import { useHaptic } from "@/hooks/useTelegram";
import { useTelegramBackButton } from "@/hooks/useTelegram";
import type { TarotSpreadResponse } from "@/types";

type SpreadType = "three_card" | "celtic_cross" | "week" | "relationship";

interface SpreadOption {
  id: SpreadType;
  name: string;
  cardCount: number;
  premium: boolean;
  productId: string;
  stars: number;
}

const SPREADS: SpreadOption[] = [
  {
    id: "three_card",
    name: "Прошлое · Настоящее · Будущее",
    cardCount: 3,
    premium: false,
    productId: "",
    stars: 0,
  },
  {
    id: "celtic_cross",
    name: "Кельтский Крест",
    cardCount: 10,
    premium: true,
    productId: "tarot_celtic",
    stars: 30,
  },
  {
    id: "week",
    name: "Карта на каждый день",
    cardCount: 7,
    premium: true,
    productId: "tarot_week",
    stars: 40,
  },
  {
    id: "relationship",
    name: "Расклад на отношения",
    cardCount: 5,
    premium: true,
    productId: "tarot_celtic",
    stars: 30,
  },
];

export function Tarot() {
  const { user, setScreen } = useAppStore();
  const { impact } = useHaptic();
  const [selectedSpread, setSelectedSpread] = useState<SpreadType | null>(null);
  const [reading, setReading] = useState<TarotSpreadResponse | null>(null);
  const [showInfo, setShowInfo] = useState(true);
  const [detailsExpanded, setDetailsExpanded] = useState(false);

  const handleBack = useCallback(() => {
    if (reading) {
      setReading(null);
    } else if (!showInfo && selectedSpread) {
      setShowInfo(true);
    } else if (selectedSpread) {
      setSelectedSpread(null);
      setShowInfo(true);
    } else setScreen("discover", "back");
  }, [reading, selectedSpread, showInfo, setScreen]);

  useTelegramBackButton(handleBack, true);

  const drawMutation = useMutation({
    mutationFn: tarotApi.draw,
    onSuccess: (data) => {
      impact("success" as any);
      setReading(data);
    },
  });

  const handleSelectSpread = (spread: SpreadOption) => {
    impact("light");
    setSelectedSpread(spread.id);
  };

  const handleDraw = () => {
    if (!selectedSpread) return;
    impact("medium");
    drawMutation.mutate(selectedSpread);
  };

  const handleGoToSpread = () => {
    setShowInfo(false);
    if (selectedSpread === "celtic_cross") {
      // Fire draw immediately so CelticCrossFlow has cards when user taps the deck
      impact("medium");
      drawMutation.mutate(selectedSpread);
    }
  };

  const handleNewCelticReading = () => {
    // Restart: re-fire draw so a fresh set of cards is ready for the new idle phase
    if (selectedSpread !== "celtic_cross") return;
    drawMutation.mutate(selectedSpread);
  };

  // Spread selection view
  if (!selectedSpread) {
    return (
      <div className="screen tarot-screen">
        <div className="screen-header screen-header--with-back screen-header--with-back-avatar">
          <button
            className="back-btn"
            onClick={() => setScreen("discover", "back")}
            aria-label="Назад"
          >
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
          <h2 className="screen-title">Таро</h2>
          <HeaderAvatarButton />
        </div>
        <div className="screen-content">
          {SPREADS.map((spread) => (
            <PremiumGate
              key={spread.id}
              locked={spread.premium && !user?.is_premium}
              productId={spread.productId}
              productName={spread.name}
              stars={spread.stars}
            >
              <motion.div
                className="spread-option"
                onClick={() => handleSelectSpread(spread)}
                whileTap={{ scale: 0.97 }}
              >
                <div className="spread-option__info">
                  <div className="spread-option__name">{spread.name}</div>
                  <div className="spread-option__count">
                    {spread.cardCount} карт
                  </div>
                </div>
                {spread.premium && <span className="premium-badge">✦ Pro</span>}
              </motion.div>
            </PremiumGate>
          ))}
        </div>
      </div>
    );
  }

  // Reading view — three_card uses dedicated animated flow
  const spreadInfo = SPREADS.find((s) => s.id === selectedSpread)!;

  if (selectedSpread === "three_card") {
    return (
      <div className="screen tarot-screen">
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
          <h2 className="screen-title">{spreadInfo.name}</h2>
        </div>
        <div className="screen-content">
          <ThreeCardFlow onReset={() => setSelectedSpread(null)} />
        </div>
      </div>
    );
  }

  return (
    <div className="screen tarot-screen">
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
        <h2 className="screen-title">{spreadInfo.name}</h2>
      </div>

      <div className="screen-content">
        {/* ── Spread info page (before drawing) ── */}
        {showInfo &&
          !reading &&
          !drawMutation.isPending &&
          selectedSpread === "celtic_cross" && (
            <motion.div
              className="spread-info"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className="spread-info__top">
              <p className="spread-info__intro">
                Понимание каждой позиции — ключ к точной интерпретации. Расклад
                делится на две части:
                <strong> Крест</strong> (позиции 1–6) исследует вашу текущую
                реальность, а <strong>Посох</strong> (позиции 7–10) раскрывает
                путь к разрешению.
              </p>

              <CelticCrossDiagram />

              {!detailsExpanded && (
                <button
                  className="btn-ghost"
                  onClick={() => setDetailsExpanded(true)}
                  style={{ marginTop: 4 }}
                >
                  Читать подробнее ↓
                </button>
              )}

              {detailsExpanded && (
                <>
              <div className="spread-info__section">
                <h4 className="spread-info__section-title">
                  Крест — Ваша Текущая Ситуация
                </h4>
                <div className="spread-info__positions">
                  <div className="spread-info__pos">
                    <span className="spread-info__num">1</span>
                    <div>
                      <strong>Настоящее</strong>
                      <p>
                        Ваше текущее состояние и центральный вопрос. Эта карта
                        задаёт тон всему раскладу.
                      </p>
                    </div>
                  </div>
                  <div className="spread-info__pos">
                    <span className="spread-info__num">2</span>
                    <div>
                      <strong>Препятствие</strong>
                      <p>
                        Кладётся поперёк первой карты. Непосредственное
                        препятствие или противодействующая сила.
                      </p>
                    </div>
                  </div>
                  <div className="spread-info__pos">
                    <span className="spread-info__num">3</span>
                    <div>
                      <strong>Основа</strong>
                      <p>
                        Подсознательный фундамент ситуации. Прошлый опыт и
                        скрытые мотивы.
                      </p>
                    </div>
                  </div>
                  <div className="spread-info__pos">
                    <span className="spread-info__num">4</span>
                    <div>
                      <strong>Недавнее Прошлое</strong>
                      <p>
                        События, которые уходят, но ещё воздействуют на
                        настоящее.
                      </p>
                    </div>
                  </div>
                  <div className="spread-info__pos">
                    <span className="spread-info__num">5</span>
                    <div>
                      <strong>Корона</strong>
                      <p>
                        Ваша осознанная цель или лучший известный вам результат.
                      </p>
                    </div>
                  </div>
                  <div className="spread-info__pos">
                    <span className="spread-info__num">6</span>
                    <div>
                      <strong>Ближайшее Будущее</strong>
                      <p>
                        Что приближается в краткосрочной перспективе — следующая
                        фаза развития.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="spread-info__section">
                <h4 className="spread-info__section-title">
                  Посох — Путь Вперёд
                </h4>
                <div className="spread-info__positions">
                  <div className="spread-info__pos">
                    <span className="spread-info__num">7</span>
                    <div>
                      <strong>Ваш Подход</strong>
                      <p>
                        Как вы видите себя в этой ситуации. Ваше отношение и
                        самовосприятие.
                      </p>
                    </div>
                  </div>
                  <div className="spread-info__pos">
                    <span className="spread-info__num">8</span>
                    <div>
                      <strong>Внешние Влияния</strong>
                      <p>
                        Люди и обстоятельства, влияющие на вашу ситуацию извне.
                      </p>
                    </div>
                  </div>
                  <div className="spread-info__pos">
                    <span className="spread-info__num">9</span>
                    <div>
                      <strong>Надежды и Страхи</strong>
                      <p>
                        То, чего вы больше всего желаете или боитесь. Эти две
                        крайности часто связаны.
                      </p>
                    </div>
                  </div>
                  <div className="spread-info__pos">
                    <span className="spread-info__num">10</span>
                    <div>
                      <strong>Результат</strong>
                      <p>
                        Вероятное разрешение, если текущие энергии продолжатся
                        без изменений.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <button
                className="btn-ghost"
                onClick={() => setDetailsExpanded(false)}
                style={{ marginTop: 4 }}
              >
                Скрыть подробности ↑
              </button>
                </>
              )}
              </div>

              <motion.button
                className="btn-primary"
                onClick={handleGoToSpread}
                whileTap={{ scale: 0.96 }}
                style={{ marginTop: 16 }}
              >
                Перейти к раскладу
              </motion.button>
            </motion.div>
          )}

        {drawMutation.isPending && (
          <LoadingSpinner message="Тасуем колоду..." />
        )}

        {drawMutation.isError && (
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
            <p>Не удалось загрузить расклад. Попробуйте ещё раз.</p>
            <button className="btn-ghost" onClick={() => drawMutation.reset()}>
              Повторить
            </button>
          </div>
        )}

        {!reading &&
          !drawMutation.isPending &&
          !drawMutation.isError &&
          !(showInfo && selectedSpread === "celtic_cross") &&
          selectedSpread !== "celtic_cross" && (
            <motion.div
              className="draw-prompt"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className="deck-preview">
                {[2, 1, 0].map((i) => (
                  <div
                    key={i}
                    className="deck-card"
                    style={{
                      transform: `rotate(${(i - 1) * 6}deg) translateY(${i * -4}px)`,
                    }}
                  >
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                      opacity="0.5"
                    >
                      <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 16.8l-6.2 4.5 2.4-7.4L2 9.4h7.6z" />
                    </svg>
                  </div>
                ))}
              </div>
              <motion.button
                className="btn-primary btn-draw"
                onClick={handleDraw}
                whileTap={{ scale: 0.96 }}
                disabled={drawMutation.isPending}
              >
                {drawMutation.isPending ? "Тасуем..." : "Тянуть карты"}
              </motion.button>
            </motion.div>
          )}

        {reading && selectedSpread === "celtic_cross" && (
          <CelticCrossFlow
            cards={reading.cards}
            onNewReading={handleNewCelticReading}
          />
        )}

        {reading && selectedSpread !== "celtic_cross" && (
          <>
            <SpreadLayout spreadType={selectedSpread} cards={reading.cards} />
            <motion.button
              className="btn-secondary btn-with-icon"
              onClick={() => {
                setReading(null);
                drawMutation.reset();
              }}
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
              Новый расклад
            </motion.button>
          </>
        )}
      </div>
    </div>
  );
}
