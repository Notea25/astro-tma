import type { DestinyChannels as DestinyChannelsType } from "@/services/api";

interface Props {
  channels: DestinyChannelsType;
}

interface ChannelDef {
  key: keyof DestinyChannelsType;
  label: string;
  caption: string;
  hint: string; // 3-stage label series
}

const STAGES = ["вход", "работа", "итог"];

// Group ordering matches §6.3 of the spec: relationships+finance share a
// "wellbeing" group on the right side, ancestral channels are paired
// (talents above / karma below) per parent.
const CHANNELS: ChannelDef[] = [
  { key: "karmic_tail",  label: "Кармический хвост", caption: "Главный кармический урок", hint: "" },
  { key: "talents",      label: "Зона талантов",     caption: "Что вдохновляет, где рост", hint: "" },
  { key: "relationships", label: "Отношения",        caption: "Какого партнёра притягиваешь", hint: "" },
  { key: "finance",      label: "Финансы",           caption: "Откуда деньги, профессии", hint: "" },
  { key: "material_karma", label: "Материальная карма", caption: "Прошлый опыт как ресурс", hint: "" },
  { key: "parental",     label: "Детско-родительский", caption: "Что пришёл от родителей", hint: "" },
  { key: "ancestral_father_talents", label: "Род отца · таланты", caption: "Сильные стороны линии отца", hint: "" },
  { key: "ancestral_father_karma",   label: "Род отца · карма",   caption: "Что прорабатывает линия отца", hint: "" },
  { key: "ancestral_mother_talents", label: "Род матери · таланты", caption: "Сильные стороны линии матери", hint: "" },
  { key: "ancestral_mother_karma",   label: "Род матери · карма",   caption: "Что прорабатывает линия матери", hint: "" },
];

export function DestinyChannels({ channels }: Props) {
  return (
    <section className="destiny-channels">
      <h3 className="destiny-channels__title">10 каналов</h3>
      <p className="destiny-channels__hint">
        Каждый канал — три точки: вход в энергию, работа с ней и итог.
        Числа — номера арканов 1-22.
      </p>
      <div className="destiny-channels__list">
        {CHANNELS.map((ch) => {
          const arr = channels[ch.key];
          if (!Array.isArray(arr) || arr.length < 3) return null;
          return (
            <div key={ch.key} className="destiny-channels__row">
              <div className="destiny-channels__row-head">
                <div className="destiny-channels__row-label">{ch.label}</div>
                <div className="destiny-channels__row-caption">{ch.caption}</div>
              </div>
              <div className="destiny-channels__nodes">
                {arr.slice(0, 3).map((num, i) => (
                  <div key={i} className="destiny-channels__node">
                    <span className="destiny-channels__node-num">{num}</span>
                    <span className="destiny-channels__node-stage">
                      {STAGES[i] ?? ""}
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
