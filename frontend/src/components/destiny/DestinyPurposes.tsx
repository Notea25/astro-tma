import type { DestinyPurposes as DestinyPurposesType } from "@/services/api";

interface TapInfo {
  num: number;
  title: string;
  context: string;
  tier: "free" | "premium";
  octagramNodeId: null;
}

interface Props {
  purposes: DestinyPurposesType;
  onTap?: (info: TapInfo) => void;
}

interface PurposeDef {
  key: keyof DestinyPurposesType;
  label: string;
  age: string;
  hint: string;
  sheetTitle: string;
}

const PURPOSES: PurposeDef[] = [
  { key: "personal",  label: "Личное",     age: "до ~40",   hint: "Вектор роста личности",
    sheetTitle: "Личное предназначение — до ~40 лет" },
  { key: "social",    label: "Социальное", age: "40-60",    hint: "Проявление через дело и социум",
    sheetTitle: "Социальное предназначение — 40-60 лет" },
  { key: "spiritual", label: "Духовное",   age: "после 60", hint: "Внутренний итог, наставничество",
    sheetTitle: "Духовное предназначение — после 60" },
  { key: "planetary", label: "Планетарное", age: "миссия",  hint: "Высшая задача, влияние",
    sheetTitle: "Планетарное предназначение — миссия" },
];

export function DestinyPurposes({ purposes, onTap }: Props) {
  return (
    <section className="destiny-purposes">
      <h3 className="destiny-purposes__title">4 предназначения</h3>
      <p className="destiny-purposes__hint">
        Жизненные векторы по возрастным этапам и высшая миссия. Число — аркан 1-22.
        Нажмите ячейку, чтобы открыть трактовку.
      </p>
      <div className="destiny-purposes__grid">
        {PURPOSES.map((p) => (
          <button
            key={p.key}
            type="button"
            className="destiny-purposes__cell"
            onClick={() =>
              onTap?.({
                num: purposes[p.key],
                title: p.sheetTitle,
                context: "purpose",
                tier: "premium",
                octagramNodeId: null,
              })
            }
          >
            <div className="destiny-purposes__num">{purposes[p.key]}</div>
            <div className="destiny-purposes__label">{p.label}</div>
            <div className="destiny-purposes__age">{p.age}</div>
            <div className="destiny-purposes__cell-hint">{p.hint}</div>
          </button>
        ))}
      </div>
    </section>
  );
}
