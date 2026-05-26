import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useMutation, useQuery } from "@tanstack/react-query";
import { destinyApi } from "@/services/api";
import { usePayment } from "@/hooks/usePayment";
import { useProductPrice } from "@/hooks/useProductPrice";
import { useAppStore } from "@/stores/app";
import { useHaptic, useTelegramBackButton } from "@/hooks/useTelegram";
import {
  DestinyOctagram,
  type DestinyNodeMeta,
} from "@/components/destiny/DestinyOctagram";
import { DestinyNarrative } from "@/components/destiny/DestinyNarrative";
import { DestinyLifeLines } from "@/components/destiny/DestinyLifeLines";
import { DestinyChakras } from "@/components/destiny/DestinyChakras";

const NODE_TITLES_RU: Record<string, string> = {
  A: "Энергия дня — что я получил при рождении",
  B: "Энергия месяца — эмоциональный план",
  C: "Энергия года — опыт рода",
  D: "Личность — образ Я в этой жизни",
  E: "Центр — главная задача жизни",
  F: "Род · верх слева — отношения по линии отца",
  G: "Род · верх справа — отношения по линии матери",
  H: "Род · низ справа — линия женщин рода",
  I: "Род · низ слева — линия мужчин рода",
};

const NODE_CONTEXT: Record<string, string> = {
  A: "personality",
  B: "personality",
  C: "karma",
  D: "personality",
  E: "mission",
  F: "love",
  G: "love",
  H: "karma",
  I: "karma",
};

export function DestinyMatrixReading() {
  const { setScreen } = useAppStore();
  const { impact } = useHaptic();
  const price = useProductPrice("destiny_matrix_full") ?? 150;
  const { purchase, phase } = usePayment();
  const paying = phase === "opening" || phase === "activating";

  const [activeNode, setActiveNode] = useState<DestinyNodeMeta | null>(null);
  const [showCalcAnim, setShowCalcAnim] = useState(true);

  const goBack = () => {
    if (activeNode) {
      setActiveNode(null);
      return;
    }
    setScreen("destiny_matrix_info", "back");
  };
  useTelegramBackButton(goBack, true);

  // Calculate once on mount — idempotent, returns existing reading if any.
  const calcMutation = useMutation({
    mutationFn: destinyApi.calculate,
    onSuccess: () => {
      impact("medium");
      // Keep the calculating animation for a tick so it doesn't feel
      // instantaneous on cached responses.
      window.setTimeout(() => setShowCalcAnim(false), 600);
    },
  });

  useEffect(() => {
    calcMutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const reading = calcMutation.data;

  // Fetch the tapped arcana's per-context meanings.
  const { data: arcanaData, isFetching: arcanaFetching } = useQuery({
    queryKey: ["destiny-matrix", "arcana", activeNode?.num],
    queryFn: () => destinyApi.getArcana(activeNode!.num),
    enabled: activeNode !== null,
    staleTime: 1000 * 60 * 60,
  });

  const isLocked = activeNode?.tier === "premium" && !reading?.has_full_access;

  const handlePurchase = async () => {
    impact("medium");
    const ok = await purchase("destiny_matrix_full");
    if (ok) calcMutation.mutate(); // refetch so has_full_access flips
  };

  const contextKey = activeNode ? NODE_CONTEXT[activeNode.nodeId] : null;
  const meaning =
    arcanaData && contextKey ? arcanaData.contexts[contextKey] : null;

  return (
    <div className="screen destiny-reading-screen">
      <div className="screen-header screen-header--with-back">
        <button
          type="button"
          className="back-btn"
          onClick={goBack}
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
        <h2 className="screen-title">Ваша Матрица</h2>
      </div>

      <div className="screen-content destiny-reading__content">
        {(showCalcAnim || calcMutation.isPending) && (
          <div className="destiny-reading__calc">
            <div className="destiny-reading__calc-glow" />
            <p>{calcMutation.isPending ? "Считаем вашу матрицу…" : "Расшифровываем арканы…"}</p>
          </div>
        )}

        {calcMutation.isError && (
          <div className="destiny-reading__error">
            <p>
              Не удалось рассчитать матрицу.
              {calcMutation.error instanceof Error
                ? ` ${calcMutation.error.message}`
                : ""}
            </p>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => calcMutation.mutate()}
            >
              Повторить
            </button>
          </div>
        )}

        {reading && !showCalcAnim && !calcMutation.isPending && (
          <>
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
              className="destiny-reading__chart-wrap"
            >
              <DestinyOctagram
                positions={reading.positions}
                hasFullAccess={reading.has_full_access}
                activeNodeId={activeNode?.nodeId ?? null}
                onNodeTap={(meta) => {
                  impact("light");
                  setActiveNode(meta);
                }}
              />
            </motion.div>

            <div className="destiny-reading__legend">
              <span className="destiny-reading__legend-dot destiny-reading__legend-dot--free" />
              <span>Бесплатно: ядро и центр</span>
              <span className="destiny-reading__legend-dot destiny-reading__legend-dot--prem" />
              <span>Premium: углы рода и линии</span>
            </div>

            {!reading.has_full_access && (
              <section className="destiny-reading__upsell">
                <h4>Откройте полный разбор</h4>
                <p>
                  Личный 7-секционный разбор, 5 линий судьбы, 7 чакр и
                  кармические хвосты. Один раз за {price} ⭐, доступ остаётся
                  навсегда.
                </p>
                <button
                  type="button"
                  className="btn-stars"
                  onClick={handlePurchase}
                  disabled={paying}
                >
                  {paying
                    ? phase === "activating"
                      ? "Активируем доступ…"
                      : "Открываем оплату…"
                    : `Открыть за ${price} ⭐`}
                </button>
              </section>
            )}

            {reading.has_full_access && (
              <>
                <DestinyNarrative enabled={reading.has_full_access} />
                <DestinyLifeLines positions={reading.positions} />
                <DestinyChakras positions={reading.positions} />
              </>
            )}
          </>
        )}
      </div>

      {/* BottomSheet — tap a node to see arcana details */}
      <AnimatePresence>
        {activeNode && (
          <>
            <motion.div
              className="destiny-sheet-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setActiveNode(null)}
            />
            <motion.div
              className="destiny-sheet"
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "tween", duration: 0.28 }}
              drag="y"
              dragConstraints={{ top: 0, bottom: 0 }}
              dragElastic={0.2}
              onDragEnd={(_, info) => {
                if (info.offset.y > 80) setActiveNode(null);
              }}
            >
              <div className="destiny-sheet__handle" />
              <div className="destiny-sheet__header">
                <div className="destiny-sheet__node-tag">
                  {NODE_TITLES_RU[activeNode.nodeId] ?? activeNode.nodeId}
                </div>
                <div className="destiny-sheet__arcana">
                  <span className="destiny-sheet__num">{activeNode.num}</span>
                  <div>
                    <div className="destiny-sheet__name">
                      {arcanaData?.arcana_name ?? "…"}
                    </div>
                    {arcanaData?.keywords?.length ? (
                      <div className="destiny-sheet__kw">
                        {arcanaData.keywords.slice(0, 3).join(" · ")}
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>

              <div className="destiny-sheet__body">
                {arcanaFetching && <p>Открываем значение…</p>}
                {!arcanaFetching && isLocked && (
                  <>
                    <p className="destiny-sheet__blur">
                      В этой позиции аркан раскрывает важную часть вашего
                      рода и сценария отношений. Полное описание доступно
                      после открытия Premium-разбора.
                    </p>
                    <button
                      type="button"
                      className="btn-stars"
                      onClick={handlePurchase}
                      disabled={paying}
                    >
                      Открыть за {price} ⭐
                    </button>
                  </>
                )}
                {!arcanaFetching && !isLocked && meaning && (
                  <p>{meaning}</p>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
