import { useState } from "react";
import { motion } from "framer-motion";
import { useAppStore } from "@/stores/app";
import { useHaptic, useTelegramBackButton } from "@/hooks/useTelegram";

interface SphereDef {
  icon: string;
  title: string;
  text: string;
}

const SPHERES: SphereDef[] = [
  {
    icon: "✦",
    title: "Визитка личности",
    text: "Портрет по пяти центральным арканам — характер, таланты, зона комфорта, главный мотив.",
  },
  {
    icon: "⚡",
    title: "Кармическая программа",
    text: "Канон школы Ладини: что было в прошлом воплощении, как проявляется сейчас и что прорабатывать.",
  },
  {
    icon: "★",
    title: "8 предназначений",
    text: "Личные, родовые и божественные задачи в формате композиции: левый + правый = итоговый аркан.",
  },
  {
    icon: "♥",
    title: "Отношения и деньги",
    text: "Какого партнёра вы притягиваете, откуда приходят финансы, через что возникают блоки.",
  },
  {
    icon: "✿",
    title: "Дерево Рода",
    text: "Линии Отца и Матери — что унаследовано как талант, что как программа, и как примирить.",
  },
  {
    icon: "☉",
    title: "Энергия года",
    text: "Какой аркан задаёт тон текущему году от ДР до ДР и что приходит после следующего Дня рождения.",
  },
];

interface StepDef {
  num: string;
  title: string;
  text: string;
}

const STEPS: StepDef[] = [
  {
    num: "1",
    title: "Считаем числа из даты рождения",
    text:
      "День, месяц и сумма цифр года — это первые три точки. Из них по простой формуле получаются ещё 19 чисел в диапазоне 1–22. Расчёт мгновенный, чистая математика.",
  },
  {
    num: "2",
    title: "Раскладываем 22 числа на октаграмму",
    text:
      "Восьмиугольная звезда из ромба и квадрата. Каждый кружок на ней — это одно из 22 чисел. У каждой позиции свой смысл: личность, миссия, отношения, родовые линии и так далее.",
  },
  {
    num: "3",
    title: "Каждое число — это аркан Таро",
    text:
      "От 1 (Маг) до 22 (Шут / Уровневая свобода) в традиции Марсельского Таро. Аркан описывает энергию позиции. Один и тот же аркан в разных точках читается по-разному.",
  },
  {
    num: "4",
    title: "Нажимаете любой кружок — открывается трактовка",
    text:
      "В нижней шторке появится название аркана, ключевые слова и тёплое объяснение что именно эта энергия значит конкретно в этой позиции вашей матрицы.",
  },
];

const FREE_ITEMS = [
  "Расчёт всей матрицы — все 22 числа видны сразу",
  "Визитка личности — портрет по 5 центральным арканам",
  "Кармический хвост — главный урок и каноническое название программы",
];

const PREM_ITEMS = [
  "Полная октаграмма — родовой квадрат, 10 каналов судьбы, чакры",
  "Кармическая программа — каноническое описание (до 26 вариантов) + как прорабатывать",
  "8 предназначений в формате композиции арканов: личные, родовые, Божественные, миссия",
  "7 чакр на Небесной и Земной линиях — карта энергетики и зон внимания",
  "Энергия текущего и следующего года — что задаёт тон до следующего ДР",
  "Личный разбор от астролога-AI — 15 разделов, ~5000 слов, адаптация под пол",
  "PDF-отчёт на ~22 A4 страницы — можно перечитать позже",
];

export function DestinyMatrixInfo() {
  const { setScreen, user } = useAppStore();
  const { impact } = useHaptic();
  const [stepsOpen, setStepsOpen] = useState(false);

  const goBack = () => setScreen("discover", "back");
  useTelegramBackButton(goBack, true);

  const hasBirthData = Boolean(user?.sun_sign);

  const handleStart = () => {
    impact("medium");
    setScreen("destiny_matrix_reading");
  };

  return (
    <div className="screen destiny-info-screen">
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
        <h2 className="screen-title">Матрица Судьбы</h2>
      </div>

      <div className="screen-content">
        <motion.div
          className="destiny-info__hero glass-gold"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <svg
            className="destiny-info__preview"
            viewBox="0 0 200 200"
            aria-hidden="true"
          >
            <g fill="none" stroke="rgba(232,200,98,0.55)" strokeWidth="0.9">
              <path d="M100 18 L182 100 L100 182 L18 100 Z" />
              <path d="M42 42 L158 42 L158 158 L42 158 Z" />
              <circle cx="100" cy="100" r="3" fill="rgba(232,200,98,0.7)" stroke="none" />
              {[
                [100, 18], [182, 100], [100, 182], [18, 100],
                [42, 42], [158, 42], [158, 158], [42, 158],
              ].map(([x, y], i) => (
                <circle key={i} cx={x} cy={y} r="3.5" fill="rgba(232,200,98,0.85)" stroke="none" />
              ))}
            </g>
          </svg>

          <h3 className="destiny-info__title">
            Карта вашей жизни через 22 аркана Таро
          </h3>
          <p className="destiny-info__lead">
            Из вашей даты рождения построим персональную октаграмму из 22 чисел
            и развёрнутый разбор на 15 разделов: визитка, кармическая программа
            из канонической базы, 8 предназначений, чакры и энергия года.
            Тепло, по делу и без эзотерических штампов.
          </p>
        </motion.div>

        {/* What you'll learn — concrete spheres */}
        <section className="destiny-info__section">
          <h4 className="destiny-info__section-title">Что вы узнаете</h4>
          <ul className="destiny-info__spheres">
            {SPHERES.map((s) => (
              <li key={s.title} className="destiny-info__sphere">
                <span className="destiny-info__sphere-icon" aria-hidden="true">
                  {s.icon}
                </span>
                <div>
                  <div className="destiny-info__sphere-title">{s.title}</div>
                  <p className="destiny-info__sphere-text">{s.text}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>

        {/* What happens after you tap "Перейти" — 4 visual steps */}
        <section className="destiny-info__section">
          <button
            type="button"
            className="destiny-info__how-toggle"
            onClick={() => setStepsOpen((v) => !v)}
          >
            <span>Как это работает — 4 шага</span>
            <span className="destiny-info__how-chev" aria-hidden="true">
              {stepsOpen ? "−" : "+"}
            </span>
          </button>
          {stepsOpen && (
            <ol className="destiny-info__steps">
              {STEPS.map((s) => (
                <li key={s.num} className="destiny-info__step">
                  <span className="destiny-info__step-num">{s.num}</span>
                  <div>
                    <div className="destiny-info__step-title">{s.title}</div>
                    <p className="destiny-info__step-text">{s.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>

        {/* Free vs Premium — upfront so user knows what they're paying for */}
        <section className="destiny-info__section destiny-info__tiers">
          <h4 className="destiny-info__section-title">
            Что доступно бесплатно
          </h4>
          <ul className="destiny-info__tier destiny-info__tier--free">
            {FREE_ITEMS.map((it) => (
              <li key={it}>
                <span className="destiny-info__tier-mark" aria-hidden="true">✓</span>
                {it}
              </li>
            ))}
          </ul>

          <h4 className="destiny-info__section-title destiny-info__tier-prem-title">
            <span className="destiny-info__prem-badge">Premium</span>
            <span>Полный разбор за 150 ⭐, доступ навсегда</span>
          </h4>
          <ul className="destiny-info__tier destiny-info__tier--prem">
            {PREM_ITEMS.map((it) => (
              <li key={it}>
                <span className="destiny-info__tier-mark" aria-hidden="true">★</span>
                {it}
              </li>
            ))}
          </ul>
        </section>

        {/* Disclaimer */}
        <p className="destiny-info__disclaimer">
          Матрица Судьбы — эзотерическая система для саморефлексии и
          разговора с собой. Это не прогноз и не медицинская/финансовая
          рекомендация.
        </p>

        {!hasBirthData ? (
          <section className="destiny-info__cta-block">
            <p className="destiny-info__hint">
              Для расчёта нужна только ваша дата рождения. Сейчас она не
              заполнена в профиле — это занимает 10 секунд.
            </p>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                impact("light");
                setScreen("profile");
              }}
            >
              Указать дату рождения
            </button>
          </section>
        ) : (
          <section className="destiny-info__cta-block">
            <p className="destiny-info__cta-hint">
              Расчёт занимает 1–2 секунды. Результат сохраняется — можно
              возвращаться сколько угодно раз.
            </p>
            <motion.button
              type="button"
              className="btn-primary destiny-info__cta"
              onClick={handleStart}
              whileTap={{ scale: 0.98 }}
            >
              Построить мою матрицу
            </motion.button>
          </section>
        )}
      </div>
    </div>
  );
}
