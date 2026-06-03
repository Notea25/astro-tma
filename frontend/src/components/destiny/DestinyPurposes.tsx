import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { destinyV3Api } from "@/services/api";
import type {
  DestinyPurposes as DestinyPurposesType,
  DestinyPurposesFull,
  V3ReadingResponse,
} from "@/services/api";

interface Props {
  purposes: DestinyPurposesType;
  purposesFull?: DestinyPurposesFull;
}

interface PurposeRow {
  /** Section key in destiny_interpretations_v3 (e.g. `purpose_celestial_personal`). */
  sectionKey: string;
  /** Label for the cell. */
  label: string;
  /** One-line role hint, shown in the collapsed cell. */
  hint: string;
  /** Composition string, e.g. "5 + 13 = 18". */
  formula: string;
  /** Total-arcana number — what users see as the big number. */
  num: number;
}

const PURPOSE_DEFS: Array<{
  key: keyof V3ReadingResponse["purposes"];
  sectionKey: string;
  label: string;
  hint: string;
}> = [
  { key: "celestial_personal", sectionKey: "purpose_celestial_personal",
    label: "Небесное личное",
    hint: "Духовная жизнь, уроки души" },
  { key: "earthly_personal", sectionKey: "purpose_earthly_personal",
    label: "Земное личное",
    hint: "Тело, дом, ресурсы" },
  { key: "wholeness_personal", sectionKey: "purpose_wholeness_personal",
    label: "Целостное личное",
    hint: "Баланс духа и материи" },
  { key: "father_lineage", sectionKey: "purpose_father_lineage",
    label: "Род Отца",
    hint: "Мужская линия" },
  { key: "mother_lineage", sectionKey: "purpose_mother_lineage",
    label: "Род Матери",
    hint: "Женская линия" },
  { key: "wholeness_lineage", sectionKey: "purpose_wholeness_lineage",
    label: "Социальная реализация",
    hint: "Примирение родов, 40–60 лет" },
  { key: "personal_divine", sectionKey: "purpose_personal_divine",
    label: "Личное Божественное",
    hint: "Путь самопознания" },
  { key: "divine_mission", sectionKey: "purpose_divine_mission",
    label: "Божественная миссия",
    hint: "Большая роль для мира" },
];

/** Fallback layout for the legacy 4-purpose model (older readings). */
function build4(p: DestinyPurposesType): PurposeRow[] {
  return [
    { sectionKey: "", num: p.personal, label: "Личное",
      hint: "Вектор до ~40 лет", formula: "Небо + Земля" },
    { sectionKey: "", num: p.social, label: "Социальное",
      hint: "Проявление 40–60", formula: "Отец + Мать" },
    { sectionKey: "", num: p.spiritual, label: "Духовное",
      hint: "После 60", formula: "Личное + Социальное" },
    { sectionKey: "", num: p.planetary, label: "Планетарное",
      hint: "Высшая миссия", formula: "Социальное + Духовное" },
  ];
}

function plainText(raw: string): string {
  return raw
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "$1")
    .trim();
}

export function DestinyPurposes({ purposes, purposesFull }: Props) {
  const [openKey, setOpenKey] = useState<string | null>(null);

  // V3 reading carries the 8 per-purpose section texts plus the
  // canonical (left, right, total) triples. Shared cache with
  // DestinyV3Narrative — no extra round-trip.
  const { data: v3 } = useQuery<V3ReadingResponse>({
    queryKey: ["destiny-matrix-v3", "reading"],
    queryFn: destinyV3Api.getReading,
    enabled: !!purposesFull,
    staleTime: 1000 * 60 * 60 * 24 * 7,
  });

  // Fall back to the legacy 4-cell layout for pre-V3 readings.
  if (!purposesFull) {
    const rows = build4(purposes);
    return (
      <section className="destiny-purposes">
        <h3 className="destiny-purposes__title">4 предназначения</h3>
        <p className="destiny-purposes__hint">
          Векторы жизни по методике Ладини.
        </p>
        <div className="destiny-purposes__grid">
          {rows.map((row, i) => (
            <div key={i} className="destiny-purposes__cell">
              <div className="destiny-purposes__num">{row.num}</div>
              <div className="destiny-purposes__label">{row.label}</div>
              <div className="destiny-purposes__cell-hint">{row.hint}</div>
              <div className="destiny-purposes__formula">{row.formula}</div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  const sectionsByKey = new Map(
    (v3?.sections ?? []).map((s) => [s.key, s] as const),
  );

  const rows: PurposeRow[] = PURPOSE_DEFS.map((def) => {
    const triple = v3?.purposes[def.key];
    const num = triple?.key[2] ?? 0;
    const formula = triple
      ? `${triple.key[0]} + ${triple.key[1]} = ${triple.key[2]}`
      : "";
    return {
      sectionKey: def.sectionKey,
      label: def.label,
      hint: def.hint,
      formula,
      num,
    };
  });

  return (
    <section className="destiny-purposes">
      <h3 className="destiny-purposes__title">8 предназначений</h3>
      <p className="destiny-purposes__hint">
        Тапни любое — раскроется персональный разбор именно по этой линии.
      </p>
      <div className="destiny-purposes__list">
        {rows.map((row) => {
          const isOpen = openKey === row.sectionKey;
          const section = sectionsByKey.get(row.sectionKey);
          const body = section?.content;
          const loading = !v3 || (!section && !v3?.sections.length);
          return (
            <div
              key={row.sectionKey}
              className={`destiny-purposes__row${isOpen ? " is-open" : ""}`}
            >
              <button
                type="button"
                className="destiny-purposes__head"
                onClick={() =>
                  setOpenKey(isOpen ? null : row.sectionKey)
                }
                aria-expanded={isOpen}
              >
                <span className="destiny-purposes__head-num">{row.num}</span>
                <span className="destiny-purposes__head-main">
                  <span className="destiny-purposes__head-label">{row.label}</span>
                  <span className="destiny-purposes__head-formula">
                    {row.formula} · {row.hint}
                  </span>
                </span>
                <span className="destiny-purposes__head-chev" aria-hidden>
                  {isOpen ? "▾" : "▸"}
                </span>
              </button>
              <AnimatePresence initial={false}>
                {isOpen && (
                  <motion.div
                    key="body"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.22 }}
                    className="destiny-purposes__body"
                  >
                    {body ? (
                      <div className="destiny-purposes__text">
                        {plainText(body)}
                      </div>
                    ) : loading ? (
                      <div className="destiny-purposes__text destiny-purposes__text--muted">
                        Готовим текст для этого предназначения…
                      </div>
                    ) : (
                      <div className="destiny-purposes__text destiny-purposes__text--muted">
                        Этот раздел появится через минуту — обнови страницу.
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </section>
  );
}
