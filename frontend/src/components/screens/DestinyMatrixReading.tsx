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
// Wording follows the canonical Russian Destiny Matrix cheat-sheet so users
// see practical, concrete labels instead of geometric ones.
const NODE_TITLES_RU: Record<DestinyNodeId, string> = {
  // Big diamond + center
  day:    "Как видят вас другие — ваш портрет",
  month:  "Стиль мышления и таланты",
  year:   "Камень на пути финансового потока",
  bottom: "Главный кармический урок",
  center: "Ваш настоящий характер",
  // Small ancestral square — practical meanings
  top_left:     "Внутренний потенциал, главный талант",
  top_right:    "Как вы общаетесь, ваша подача себя",
  bottom_right: "Как улучшить поток денег в жизнь",
  bottom_left:  "Желания сердца — от чего вы радуетесь",
  // Axis channels — 3 points per direction (near/mid/close to center)
  month_near:  "Главный талант — что вдохновляет",
  month_mid:   "Канал талантов — работа",
  month_close: "Связь с интуицией",
  year_near:   "Финансовый поток — итог",
  year_mid:    "Финансовый канал — работа",
  year_close:  "Вход в денежный канал",
  bottom_near: "Главный кармический урок",
  bottom_mid:  "Кармический хвост — что прорабатываете",
  bottom_close: "Идеальный партнёр (нижний ключ)",
  day_near:    "Внутренний родитель",
  day_mid:     "Детско-родительский канал",
  day_close:   "Внутренний ребёнок",
  // Diagonal ancestral channels
  aft_in:  "Род отца · таланты — работа канала",
  aft_out: "Духовная карма по роду отца",
  amt_in:  "Род матери · таланты — работа канала",
  amt_out: "Духовная карма по роду матери",
  amk_in:  "Род матери · карма — работа канала",
  amk_out: "Материальная карма по роду матери",
  afk_in:  "Род отца · карма — работа канала",
  afk_out: "Материальная карма по роду отца",
};

// Which `arcana_meanings.context` row to pull for the bottom-sheet copy
// when the user taps a given node.
const NODE_CONTEXT: Record<DestinyNodeId, string> = {
  day:    "personality",
  month:  "talents",
  year:   "ancestral",
  bottom: "karmic_tail",
  center: "personality",
  top_left:     "ancestral",
  top_right:    "ancestral",
  bottom_right: "ancestral",
  bottom_left:  "ancestral",
  // Axis channels — each axis carries a specific life domain
  month_near:  "talents",
  month_mid:   "talents",
  month_close: "talents",
  year_near:   "finance",
  year_mid:    "finance",
  year_close:  "material_karma",
  bottom_near: "karmic_tail",
  bottom_mid:  "karmic_tail",
  bottom_close: "karmic_tail",
  day_near:    "parental",
  day_mid:     "parental",
  day_close:   "relationships",
  // Diagonal ancestral channels
  aft_in:  "ancestral",
  aft_out: "ancestral",
  amt_in:  "ancestral",
  amt_out: "ancestral",
  amk_in:  "ancestral",
  amk_out: "ancestral",
  afk_in:  "ancestral",
  afk_out: "ancestral",
};

interface ActiveTap {
  num: number;
  title: string;
  context: string;
  tier: "free" | "premium";
  /** Only set when the tap came from the octagram itself; lets it
   *  highlight the active node on the SVG. */
  octagramNodeId: DestinyNodeId | null;
}

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

  // Universal tap target — works for octagram nodes AND for cells in the
  // Purposes/Channels tables below.
  const [activeTap, setActiveTap] = useState<ActiveTap | null>(null);
  const [showCalcAnim, setShowCalcAnim] = useState(true);

  const goBack = () => {
    if (activeTap) {
      setActiveTap(null);
      return;
    }
    setScreen("destiny_matrix_info", "back");
  };
  useTelegramBackButton(goBack, true);

  const openTap = (tap: ActiveTap) => {
    impact("light");
    setActiveTap(tap);
  };
  const openOctagramTap = (meta: DestinyNodeMeta) => {
    openTap({
      num: meta.num,
      title: NODE_TITLES_RU[meta.nodeId] ?? meta.nodeId,
      context: NODE_CONTEXT[meta.nodeId] ?? "personality",
      tier: meta.tier,
      octagramNodeId: meta.nodeId,
    });
  };

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
    queryKey: ["destiny-matrix", "arcana", activeTap?.num],
    queryFn: () => destinyApi.getArcana(activeTap!.num),
    enabled: activeTap !== null,
    staleTime: 1000 * 60 * 60,
  });

  const isLocked = activeTap?.tier === "premium" && !reading?.has_full_access;

  const handlePurchase = async () => {
    impact("medium");
    const ok = await purchase("destiny_matrix_full");
    if (ok) calcMutation.mutate();
  };

  const meaning =
    arcanaData && activeTap ? arcanaData.contexts[activeTap.context] : null;

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
                activeNodeId={activeTap?.octagramNodeId ?? null}
                onNodeTap={openOctagramTap}
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
                <DestinyPurposes
                  purposes={reading.positions.purposes}
                  onTap={openTap}
                />
                <DestinyChannels
                  channels={reading.positions.channels}
                  onTap={openTap}
                />
                <DestinyVarna varna={reading.positions.varna} />
                <DestinyNarrative enabled={reading.has_full_access} />
              </>
            )}
          </>
        )}
      </div>

      {/* BottomSheet — tap any node or table cell to see arcana details */}
      <AnimatePresence>
        {activeTap && (
          <>
            <motion.div
              className="destiny-sheet-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setActiveTap(null)}
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
                if (info.offset.y > 80) setActiveTap(null);
              }}
            >
              <div className="destiny-sheet__handle" />
              <div className="destiny-sheet__header">
                <div className="destiny-sheet__node-tag">{activeTap.title}</div>
                <div className="destiny-sheet__arcana">
                  <span className="destiny-sheet__num">{activeTap.num}</span>
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
