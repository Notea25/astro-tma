import type { DestinyPurposes as DestinyPurposesType } from "@/services/api";

interface Props {
  purposes: DestinyPurposesType;
}

interface PurposeDef {
  key: keyof DestinyPurposesType;
  label: string;
  age: string;
  hint: string;
}

const PURPOSES: PurposeDef[] = [
  { key: "personal",  label: "Личное",     age: "до ~40",   hint: "Вектор роста личности" },
  { key: "social",    label: "Социальное", age: "40-60",    hint: "Проявление через дело и социум" },
  { key: "spiritual", label: "Духовное",   age: "после 60", hint: "Внутренний итог, наставничество" },
  { key: "planetary", label: "Планетарное", age: "миссия",  hint: "Высшая задача, влияние" },
];

export function DestinyPurposes({ purposes }: Props) {
  return (
    <section className="destiny-purposes">
      <h3 className="destiny-purposes__title">4 предназначения</h3>
      <p className="destiny-purposes__hint">
        Жизненные векторы по возрастным этапам и высшая миссия. Число — аркан 1-22.
      </p>
      <div className="destiny-purposes__grid">
        {PURPOSES.map((p) => (
          <div key={p.key} className="destiny-purposes__cell">
            <div className="destiny-purposes__num">{purposes[p.key]}</div>
            <div className="destiny-purposes__label">{p.label}</div>
            <div className="destiny-purposes__age">{p.age}</div>
            <div className="destiny-purposes__cell-hint">{p.hint}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
