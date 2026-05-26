import { useState } from "react";
import { motion } from "framer-motion";
import { useAppStore } from "@/stores/app";
import { useHaptic, useTelegramBackButton } from "@/hooks/useTelegram";

const HERO_BULLETS = [
  "Кто вы по своей сути",
  "Ваше предназначение",
  "Финансовый канал и зоны реализации",
  "Сценарий отношений и любви",
  "Кармические задачи и родовые программы",
  "Точки силы и зоны роста",
];

export function DestinyMatrixInfo() {
  const { setScreen, user } = useAppStore();
  const { impact } = useHaptic();
  const [howOpen, setHowOpen] = useState(false);

  const goBack = () => setScreen("discover", "back");
  useTelegramBackButton(goBack, true);

  // UserProfile doesn't expose birth_date — proxy on sun_sign (onboarding
  // populates both together, so sun_sign present ⇔ birth_date present).
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
          {/* Preview octagram — static, no numbers */}
          <svg
            className="destiny-info__preview"
            viewBox="0 0 200 200"
            aria-hidden="true"
          >
            <g fill="none" stroke="rgba(232,200,98,0.55)" strokeWidth="0.9">
              {/* Big diamond */}
              <path d="M100 18 L182 100 L100 182 L18 100 Z" />
              {/* Small square (rotated 45°) — same center, same radius */}
              <path d="M42 42 L158 42 L158 158 L42 158 Z" />
              {/* Center mark */}
              <circle cx="100" cy="100" r="3" fill="rgba(232,200,98,0.7)" stroke="none" />
              {/* 8 axis dots */}
              {[
                [100, 18], [182, 100], [100, 182], [18, 100],
                [42, 42], [158, 42], [158, 158], [42, 158],
              ].map(([x, y], i) => (
                <circle key={i} cx={x} cy={y} r="3.5" fill="rgba(232,200,98,0.85)" stroke="none" />
              ))}
            </g>
          </svg>

          <h3 className="destiny-info__title">
            Расшифровка вашей даты рождения через 22 аркана
          </h3>
          <p className="destiny-info__lead">
            Матрица Судьбы превращает день, месяц и год вашего рождения в
            восемь смысловых точек на схеме-октаграмме. Каждая точка — это
            аркан Таро, который описывает конкретную сферу вашей жизни.
          </p>
        </motion.div>

        <section className="destiny-info__section">
          <h4 className="destiny-info__section-title">Что вы узнаете</h4>
          <ul className="destiny-info__bullets">
            {HERO_BULLETS.map((b) => (
              <li key={b}>
                <span aria-hidden="true">✦</span>
                {b}
              </li>
            ))}
          </ul>
        </section>

        <section className="destiny-info__section">
          <button
            type="button"
            className="destiny-info__how-toggle"
            onClick={() => setHowOpen((v) => !v)}
          >
            <span>Как это работает</span>
            <span className="destiny-info__how-chev" aria-hidden="true">
              {howOpen ? "−" : "+"}
            </span>
          </button>
          {howOpen && (
            <p className="destiny-info__how-text">
              Дата рождения переводится в числа арканов 1–22: день → энергия
              дня, месяц → эмоциональный план, сумма цифр года → опыт рода.
              Из этих трёх чисел вырастает «личность» и «центр» — главная
              задача жизни. Дальше формируется октаграмма: восемь углов
              описывают отношения, финансы, здоровье, кармические программы и
              дополнительные линии судьбы. Каждое число интерпретируется как
              аркан в контексте конкретной сферы.
            </p>
          )}
        </section>

        {!hasBirthData ? (
          <section className="destiny-info__cta-block">
            <p className="destiny-info__hint">
              Для расчёта нужна только ваша дата рождения. Сейчас она не
              заполнена в профиле.
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
            <motion.button
              type="button"
              className="btn-primary destiny-info__cta"
              onClick={handleStart}
              whileTap={{ scale: 0.98 }}
            >
              Перейти к расчёту
            </motion.button>
          </section>
        )}
      </div>
    </div>
  );
}
