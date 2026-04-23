import { useState } from 'react'
import { motion } from 'framer-motion'
import { CelticCrossDiagram } from './CelticCrossDiagram'

type SpreadType = 'three_card' | 'celtic_cross' | 'week' | 'relationship'

interface PositionInfo {
  n: number
  title: string
  description: string
}

interface SpreadContent {
  intro: string
  positions: PositionInfo[]
  secondSection?: { title: string; positions: PositionInfo[] }
  showDiagram?: 'celtic_cross'
  secondSectionFirstTitle?: string  // optional heading for first positions group when a second section exists
}

const SPREAD_CONTENT: Record<SpreadType, SpreadContent> = {
  three_card: {
    intro:
      'Классический базовый расклад: три карты, три времени. Первая рассказывает о корнях ситуации, вторая — о том, где вы стоите сейчас, третья показывает, куда направлено движение. Подходит для быстрого анализа любого вопроса.',
    positions: [
      {
        n: 1,
        title: 'Прошлое',
        description:
          'События и энергии, которые привели вас к текущей ситуации. Корни вопроса, опыт, из которого растёт настоящее.',
      },
      {
        n: 2,
        title: 'Настоящее',
        description:
          'Ваше актуальное состояние. Ключевые силы и обстоятельства, определяющие текущий момент.',
      },
      {
        n: 3,
        title: 'Будущее',
        description:
          'Вероятное развитие, если текущая траектория сохранится. Следующий этап, к которому вы движетесь.',
      },
    ],
  },

  celtic_cross: {
    intro:
      'Понимание каждой позиции — ключ к точной интерпретации. Расклад делится на две части: Крест (позиции 1–6) исследует вашу текущую реальность, а Посох (позиции 7–10) раскрывает путь к разрешению.',
    showDiagram: 'celtic_cross',
    secondSectionFirstTitle: 'Крест — Ваша Текущая Ситуация',
    positions: [
      { n: 1, title: 'Настоящее', description: 'Ваше текущее состояние и центральный вопрос. Эта карта задаёт тон всему раскладу.' },
      { n: 2, title: 'Препятствие', description: 'Кладётся поперёк первой карты. Непосредственное препятствие или противодействующая сила.' },
      { n: 3, title: 'Основа', description: 'Подсознательный фундамент ситуации. Прошлый опыт и скрытые мотивы.' },
      { n: 4, title: 'Недавнее Прошлое', description: 'События, которые уходят, но ещё воздействуют на настоящее.' },
      { n: 5, title: 'Корона', description: 'Ваша осознанная цель или лучший известный вам результат.' },
      { n: 6, title: 'Ближайшее Будущее', description: 'Что приближается в краткосрочной перспективе — следующая фаза развития.' },
    ],
    secondSection: {
      title: 'Посох — Путь Вперёд',
      positions: [
        { n: 7, title: 'Ваш Подход', description: 'Как вы видите себя в этой ситуации. Ваше отношение и самовосприятие.' },
        { n: 8, title: 'Внешние Влияния', description: 'Люди и обстоятельства, влияющие на вашу ситуацию извне.' },
        { n: 9, title: 'Надежды и Страхи', description: 'То, чего вы больше всего желаете или боитесь. Эти две крайности часто связаны.' },
        { n: 10, title: 'Результат', description: 'Вероятное разрешение, если текущие энергии продолжатся без изменений.' },
      ],
    },
  },

  week: {
    intro:
      'Семь карт — по одной на каждый день недели. Расклад показывает энергетический рисунок ближайших семи дней: где будет лёгкость, где сопротивление, на что направить внимание. Используйте как карту маршрута на неделю.',
    positions: [
      { n: 1, title: 'Понедельник', description: 'Энергия старта недели. С чем вы входите в новый цикл, какая главная тема первых дней.' },
      { n: 2, title: 'Вторник', description: 'Момент действия. Что требует инициативы, где важно не откладывать.' },
      { n: 3, title: 'Среда', description: 'Середина недели, точка баланса. Что нужно уравновесить и переосмыслить.' },
      { n: 4, title: 'Четверг', description: 'Развитие и рост. Благоприятная фаза для продвижения планов и новых контактов.' },
      { n: 5, title: 'Пятница', description: 'Завершение рабочей части недели. Итоги усилий, переход к более лёгкому темпу.' },
      { n: 6, title: 'Суббота', description: 'День восстановления. Что питает вашу энергию и возвращает ресурс.' },
      { n: 7, title: 'Воскресенье', description: 'Рефлексия и подготовка. Главный урок уходящей недели и ключ к следующей.' },
    ],
  },

  relationship: {
    intro:
      'Пять карт для глубокого взгляда на отношения — неважно, романтические они, семейные или дружеские. Расклад показывает позиции обоих людей, качество связи, главный вызов и потенциал развития отношений.',
    positions: [
      { n: 1, title: 'Вы', description: 'Ваша роль и состояние в отношениях. Что вы приносите, чем живёте внутри этой связи.' },
      { n: 2, title: 'Партнёр', description: 'Позиция другого человека. Его внутреннее состояние и отношение к ситуации.' },
      { n: 3, title: 'Связь', description: 'Качество и природа того, что происходит между вами. Энергия взаимодействия.' },
      { n: 4, title: 'Вызов', description: 'Главное препятствие или напряжение, с которым нужно работать обоим.' },
      { n: 5, title: 'Потенциал', description: 'Куда могут развиться отношения, если пройти через вызов. Возможное будущее связи.' },
    ],
  },
}

function PositionList({ positions }: { positions: PositionInfo[] }) {
  return (
    <div className="spread-info__positions">
      {positions.map((p) => (
        <div key={p.n} className="spread-info__pos">
          <span className="spread-info__num">{p.n}</span>
          <div>
            <strong>{p.title}</strong>
            <p>{p.description}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

interface Props {
  spread: SpreadType
  onStart: () => void
}

export function SpreadInfoPage({ spread, onStart }: Props) {
  const content = SPREAD_CONTENT[spread]
  const [detailsExpanded, setDetailsExpanded] = useState(false)

  return (
    <motion.div
      className="spread-info"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <div className="spread-info__top">
        <p className="spread-info__intro">{content.intro}</p>

        {content.showDiagram === 'celtic_cross' && <CelticCrossDiagram />}

        {!detailsExpanded && (
          <button
            className="btn-ghost"
            onClick={() => setDetailsExpanded(true)}
            style={{ marginTop: 4 }}
          >
            Читать подробнее ↓
          </button>
        )}

        {detailsExpanded && (
          <>
            {content.secondSection ? (
              <>
                <div className="spread-info__section">
                  {content.secondSectionFirstTitle && (
                    <h4 className="spread-info__section-title">
                      {content.secondSectionFirstTitle}
                    </h4>
                  )}
                  <PositionList positions={content.positions} />
                </div>
                <div className="spread-info__section">
                  <h4 className="spread-info__section-title">
                    {content.secondSection.title}
                  </h4>
                  <PositionList positions={content.secondSection.positions} />
                </div>
              </>
            ) : (
              <div className="spread-info__section">
                <PositionList positions={content.positions} />
              </div>
            )}

            <button
              className="btn-ghost"
              onClick={() => setDetailsExpanded(false)}
              style={{ marginTop: 4 }}
            >
              Скрыть подробности ↑
            </button>
          </>
        )}
      </div>

      <motion.button
        className="btn-primary"
        onClick={onStart}
        whileTap={{ scale: 0.96 }}
        style={{ marginTop: 16 }}
      >
        Перейти к раскладу
      </motion.button>
    </motion.div>
  )
}
