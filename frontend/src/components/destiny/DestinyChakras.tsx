import type { DestinyMatrixPositions } from "@/services/api";

interface Props {
  positions: DestinyMatrixPositions;
}

interface ChakraDef {
  key: string;
  label: string;
  caption: string;
}

// Top-to-bottom (crown → root) as drawn in canonical matrix diagrams.
const CHAKRAS: ChakraDef[] = [
  { key: "sahasrara",    label: "Сахасрара", caption: "Связь с высшим, духовный план" },
  { key: "ajna",         label: "Аджна",     caption: "Интуиция, видение" },
  { key: "vishuddha",    label: "Вишудха",   caption: "Самовыражение, голос" },
  { key: "anahata",      label: "Анахата",   caption: "Сердце, любовь" },
  { key: "manipura",     label: "Манипура",  caption: "Воля, статус" },
  { key: "svadhisthana", label: "Свадхистана", caption: "Чувственность, удовольствия, деньги" },
  { key: "muladhara",    label: "Муладхара", caption: "Тело, безопасность, корни" },
];

export function DestinyChakras({ positions }: Props) {
  const rows = positions.chakras ?? {};
  const totals = rows.totals;

  return (
    <section className="destiny-chakras">
      <h3 className="destiny-chakras__title">7 чакр × 3 уровня</h3>
      <p className="destiny-chakras__hint">
        Каждая чакра описана через три столбца: тело · энергия · эмоции. Снизу
        вверх — от материи к духу.
      </p>
      <div className="destiny-chakras__table">
        <div className="destiny-chakras__head">
          <span />
          <span>Тело</span>
          <span>Энергия</span>
          <span>Эмоция</span>
        </div>
        {CHAKRAS.map((ch) => {
          const row = rows[ch.key];
          if (!row) return null;
          return (
            <div key={ch.key} className="destiny-chakras__row">
              <div className="destiny-chakras__row-head">
                <div className="destiny-chakras__row-label">{ch.label}</div>
                <div className="destiny-chakras__row-caption">{ch.caption}</div>
              </div>
              <span className="destiny-chakras__cell">{row.physics}</span>
              <span className="destiny-chakras__cell">{row.energy}</span>
              <span className="destiny-chakras__cell destiny-chakras__cell--emo">
                {row.emotion}
              </span>
            </div>
          );
        })}
        {totals && (
          <div className="destiny-chakras__row destiny-chakras__row--totals">
            <div className="destiny-chakras__row-head">
              <div className="destiny-chakras__row-label">Итог</div>
              <div className="destiny-chakras__row-caption">Свод по столбцам</div>
            </div>
            <span className="destiny-chakras__cell">{totals.physics}</span>
            <span className="destiny-chakras__cell">{totals.energy}</span>
            <span className="destiny-chakras__cell destiny-chakras__cell--emo">
              {totals.emotion}
            </span>
          </div>
        )}
      </div>
    </section>
  );
}
