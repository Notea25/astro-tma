import type { DestinyMatrixPositions } from "@/services/api";

interface Props {
  positions: DestinyMatrixPositions;
}

interface LineDef {
  key: keyof DestinyMatrixPositions;
  label: string;
  caption: string;
}

const LINES: LineDef[] = [
  { key: "line_karma",   label: "Линия кармы",      caption: "Что вы принесли · что прорабатываете · итог рода" },
  { key: "line_mission", label: "Линия миссии",     caption: "Старт · переход · цель" },
  { key: "line_money",   label: "Линия денег",      caption: "Вход в канал · поток · реализация" },
  { key: "line_love",    label: "Линия любви",      caption: "Притяжение · работа в отношениях · итог" },
  { key: "line_health",  label: "Линия здоровья",   caption: "Природа тела · нагрузка · долгосрочный фон" },
];

const NODE_LABELS = ["начало", "середина", "итог"];

export function DestinyLifeLines({ positions }: Props) {
  return (
    <section className="destiny-lines">
      <h3 className="destiny-lines__title">5 линий судьбы</h3>
      <p className="destiny-lines__hint">
        Каждая линия — три точки: вход в энергию, работа с ней и итог. Числа —
        номера арканов 1–22.
      </p>
      <div className="destiny-lines__list">
        {LINES.map((line) => {
          const arr = positions[line.key] as number[];
          if (!Array.isArray(arr)) return null;
          return (
            <div key={line.key} className="destiny-lines__row">
              <div className="destiny-lines__row-head">
                <div className="destiny-lines__row-label">{line.label}</div>
                <div className="destiny-lines__row-caption">{line.caption}</div>
              </div>
              <div className="destiny-lines__nodes">
                {arr.map((num, i) => (
                  <div key={i} className="destiny-lines__node">
                    <span className="destiny-lines__node-num">{num}</span>
                    <span className="destiny-lines__node-stage">
                      {NODE_LABELS[i] ?? ""}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
