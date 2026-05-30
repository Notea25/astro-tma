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
  type DestinyNodeId,
  type DestinyNodeMeta,
} from "@/components/destiny/DestinyOctagram";
import { DestinyNarrative } from "@/components/destiny/DestinyNarrative";
import { DestinyPurposes } from "@/components/destiny/DestinyPurposes";
import { DestinyChannels } from "@/components/destiny/DestinyChannels";
import { DestinyVarna } from "@/components/destiny/DestinyVarna";

// Human-friendly title shown in the bottom-sheet header for each tap-target.
const NODE_TITLES_RU: Record<DestinyNodeId, string> = {
  day:          "День — портрет личности",
  month:        "Месяц — таланты и вдохновение",
  year:         "Год — опыт рода, повторы",
  bottom:       "Низ — кармический урок",
  center:       "Центр — характер, зона комфорта",
  top_left:     "Род · верх слева — отец, духовное",
  top_right:    "Род · верх справа — мать, духовное",
  bottom_right: "Род · низ справа — мать, материальное",
  bottom_left:  "Род · низ слева — отец, материальное",
};

// Which `arcana_meanings.context` row to pull for the bottom-sheet copy
// when the user taps a given node.
const NODE_CONTEXT: Record<DestinyNodeId, string> = {
  day:          "personality",
  month:        "talents",
  year:         "ancestral",
  bottom:       "karmic_tail",
  center:       "personality",
  top_left:     "ancestral",
  top_right:    "ancestral",
  bottom_right: "ancestral",
  bottom_left:  "ancestral",
};

const MONTHS_RU_GEN = [
  "января", "февраля", "марта", "апреля", "мая", "июня",
  "июля", "августа", "сентября", "октября", "ноября", "декабря",
];

function formatBirthDateRu(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  if (!y || !m || !d) return iso;
  return `${d} ${MONTHS_RU_GEN[m - 1]} ${y}`;
}

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

  const calcMutation = useMutation({
    mutationFn: destinyApi.calculate,
    onSuccess: () => {
      impact("medium");
      window.setTimeout(() => setShowCalcAnim(false), 600);
    },
  });

  useEffect(() => {
    calcMutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const reading = calcMutation.data;

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
    if (ok) calcMutation.mutate();
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
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="destiny-reading__birth"
            >
              <span className="destiny-reading__birth-label">Дата рождения</span>
              <span className="destiny-reading__birth-date">
                {formatBirthDateRu(reading.birth_date)}
              </span>
            </motion.div>

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
              <span>Premium: углы рода и каналы</span>
            </div>

            {!reading.has_full_access && (
              <section className="destiny-reading__upsell">
                <h4>Откройте полный разбор</h4>
                <p>
                  Личный 8-секционный разбор, 4 предназначения, 10 каналов
                  судьбы и варна. Один раз за {price} ⭐, доступ остаётся
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
                <DestinyPurposes purposes={reading.positions.purposes} />
                <DestinyChannels channels={reading.positions.channels} />
                <DestinyVarna varna={reading.positions.varna} />
                <DestinyNarrative enabled={reading.has_full_access} />
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
