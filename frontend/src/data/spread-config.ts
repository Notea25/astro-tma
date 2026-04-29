export type SpreadKey = "three_card" | "celtic_cross" | "week" | "relationship";
export type CardBackVariant = "gold" | "geometry" | "mirror" | "duo";

export interface SpreadPosition {
  num: number;
  label: string;
  description: string;
}

export interface SpreadSection {
  title?: string;
  positions: SpreadPosition[];
}

export interface SpreadLayoutSlot {
  x: number;
  y: number;
  rotate?: number;
}

export interface SpreadLayoutDef {
  w: number;
  h: number;
  slots: SpreadLayoutSlot[];
}

export interface SpreadConfig {
  key: SpreadKey;
  title: string;
  intro: string;
  sections: SpreadSection[];
  layout: SpreadLayoutDef;
  backVariant: CardBackVariant;
  /** Optional glyphs shown inside preview cards (e.g. ["☽", "☉", "✦"] for three_card). */
  previewSymbols?: string[];
}

export const CARD_W = 68;
export const CARD_H = 102;

export const SPREAD_CONFIG: Record<SpreadKey, SpreadConfig> = {
  three_card: {
    key: "three_card",
    title: "Прошлое · Настоящее · Будущее",
    intro:
      "Три карты рассказывают о движении темы во времени. <strong>Прошлое</strong> — корни ситуации и то, что уже отпускаете. <strong>Настоящее</strong> — центральная энергия сейчас. <strong>Будущее</strong> — следующий шаг, который уже формируется.",
    sections: [
      {
        positions: [
          {
            num: 1,
            label: "Прошлое",
            description:
              "События и решения, которые привели к текущему моменту. Что завершается, что становится опытом.",
          },
          {
            num: 2,
            label: "Настоящее",
            description:
              "Главная энергия момента. Что разворачивается в вашей жизни прямо сейчас.",
          },
          {
            num: 3,
            label: "Будущее",
            description:
              "Направление, в котором движется тема. Что становится возможным при сохранении текущей траектории.",
          },
        ],
      },
    ],
    layout: {
      w: 260,
      h: 110,
      slots: [
        { x: 0, y: 4 },
        { x: 96, y: 4 },
        { x: 192, y: 4 },
      ],
    },
    backVariant: "gold",
    previewSymbols: ["☽", "☉", "✦"],
  },

  celtic_cross: {
    key: "celtic_cross",
    title: "Кельтский Крест",
    intro:
      "Понимание каждой позиции — ключ к точной интерпретации. Расклад делится на две части: <strong>Крест</strong> (позиции 1–6) исследует вашу текущую реальность, а <strong>Посох</strong> (позиции 7–10) раскрывает путь к разрешению.",
    sections: [
      {
        title: "Крест — Ваша Текущая Ситуация",
        positions: [
          {
            num: 1,
            label: "Ситуация",
            description:
              "Ваше текущее состояние и центральный вопрос. Эта карта задаёт тон всему раскладу.",
          },
          {
            num: 2,
            label: "Препятствие",
            description:
              "Кладётся поперёк первой карты. Непосредственное препятствие или противодействующая сила.",
          },
          {
            num: 3,
            label: "Сознание",
            description:
              "Мысли, осознанная цель и то, что находится «над» ситуацией.",
          },
          {
            num: 4,
            label: "Подсознание",
            description:
              "Корни ситуации, скрытые мотивы и внутренний фундамент.",
          },
          {
            num: 5,
            label: "Ближайшее прошлое",
            description:
              "События, которые уходят, но ещё воздействуют на настоящее.",
          },
          {
            num: 6,
            label: "Ближайшее Будущее",
            description:
              "Что приближается в краткосрочной перспективе — следующая фаза развития.",
          },
        ],
      },
      {
        title: "Посох — Путь Вперёд",
        positions: [
          {
            num: 7,
            label: "Я сам",
            description:
              "Как вы видите себя в этой ситуации. Ваше отношение и самовосприятие.",
          },
          {
            num: 8,
            label: "Другие",
            description:
              "Люди и обстоятельства, влияющие на вашу ситуацию извне.",
          },
          {
            num: 9,
            label: "Надежды и опасения",
            description:
              "То, чего вы больше всего желаете или боитесь. Эти две крайности часто связаны.",
          },
          {
            num: 10,
            label: "Результат",
            description:
              "Вероятное разрешение, если текущие энергии продолжатся без изменений.",
          },
        ],
      },
    ],
    layout: {
      w: 355,
      h: 430,
      slots: [
        { x: 98, y: 150 },
        { x: 98, y: 150, rotate: 90 },
        { x: 98, y: 28 },
        { x: 98, y: 272 },
        { x: 16, y: 150 },
        { x: 180, y: 150 },
        { x: 280, y: 328 },
        { x: 280, y: 228 },
        { x: 280, y: 128 },
        { x: 280, y: 28 },
      ],
    },
    backVariant: "geometry",
    previewSymbols: ["☉", "✦", "☽", "◐", "◇", "☿", "♄", "♀", "△", "✧"],
  },

  week: {
    key: "week",
    title: "Карта на каждый день",
    intro:
      "Семь карт показывают энергетический рисунок ближайших семи дней через планетные архетипы: эмоции, действие, мысли, рост, отношения, ответственность и итоговый фокус. Используйте как карту маршрута на неделю.",
    sections: [
      {
        positions: [
          {
            num: 1,
            label: "Луна",
            description: "Эмоциональный тон ближайшего периода.",
          },
          {
            num: 2,
            label: "Марс",
            description: "Где потребуется действие, смелость и ясная воля.",
          },
          {
            num: 3,
            label: "Меркурий",
            description: "Мысли, разговоры, решения и обмен информацией.",
          },
          {
            num: 4,
            label: "Юпитер",
            description: "Рост, поддержка, возможности и расширение.",
          },
          {
            num: 5,
            label: "Венера",
            description: "Отношения, удовольствие, красота и ценности.",
          },
          {
            num: 6,
            label: "Сатурн",
            description: "Ответственность, границы, дисциплина и урок недели.",
          },
          {
            num: 7,
            label: "Солнце",
            description: "Итоговая ясность, главный фокус и сила недели.",
          },
        ],
      },
    ],
    layout: {
      w: 314,
      h: 240,
      slots: [
        { x: 0, y: 0 },
        { x: 82, y: 0 },
        { x: 164, y: 0 },
        { x: 246, y: 0 },
        { x: 27, y: 116 },
        { x: 123, y: 116 },
        { x: 219, y: 116 },
      ],
    },
    backVariant: "gold",
    previewSymbols: ["☽", "♂", "☿", "♃", "♀", "♄", "☉"],
  },

  relationship: {
    key: "relationship",
    title: "Расклад на отношения",
    intro:
      "Пять карт — зеркало партнёрства. <strong>Вы</strong> и <strong>Партнёр</strong> показывают каждого в отдельности, <strong>Связь</strong> раскрывает динамику между вами, а <strong>Вызов</strong> и <strong>Потенциал</strong> — то, через что растёт ваша пара.",
    sections: [
      {
        positions: [
          {
            num: 1,
            label: "Вы",
            description:
              "Ваш вклад в отношения. Как вы проявляетесь в этой связи.",
          },
          {
            num: 2,
            label: "Партнёр",
            description:
              "Позиция партнёра. Что он приносит и как воспринимает ваши отношения.",
          },
          {
            num: 3,
            label: "Связь",
            description: "Энергия между вами. Что вас держит вместе сейчас.",
          },
          {
            num: 4,
            label: "Вызов",
            description: "Точка напряжения. Через что вы растёте как пара.",
          },
          {
            num: 5,
            label: "Потенциал",
            description:
              "Куда могут привести ваши отношения, если выдержите вызов.",
          },
        ],
      },
    ],
    layout: {
      w: 280,
      h: 426,
      slots: [
        { x: 58, y: 0 },
        { x: 154, y: 0 },
        { x: 106, y: 116 },
        { x: 106, y: 218 },
        { x: 106, y: 320 },
      ],
    },
    backVariant: "duo",
    previewSymbols: ["☽", "☉", "✦", "◇", "♡"],
  },
};

export interface MacIntroConfig {
  title: string;
  intro: string;
  backVariant: CardBackVariant;
}

export const MAC_INTRO: MacIntroConfig = {
  title: "Зеркало Души",
  intro:
    "Метафорические карты — это не предсказание, а зеркало. <strong>Задайте вопрос</strong> или просто позвольте карте найти вас. Образ, который выпадет, откроет ту грань ситуации, которую вы ещё не видели.",
  backVariant: "mirror",
};
