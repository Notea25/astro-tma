import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  MoonPhaseSkeleton,
  MoonCalendarSkeleton,
} from "@/components/ui/Skeleton";
import { horoscopeApi } from "@/services/api";
import { useHaptic } from "@/hooks/useTelegram";
import { useAppStore } from "@/stores/app";

const PHASE_ENERGY: Record<string, string> = {
  Новолуние:
    "Время намерений и нового начала. Сажайте семена желаний — Луна поддержит любой старт.",
  "Растущий серп":
    "Энергия нарастает. Действуйте, стройте планы, двигайтесь вперёд.",
  "Первая четверть":
    "Момент решений. Преодолевайте препятствия — сила на вашей стороне.",
  "Растущая Луна":
    "Прилив сил. Занимайтесь творчеством, общением, новыми проектами.",
  Полнолуние:
    "Пик энергии. Завершайте начатое, практикуйте благодарность, отпускайте лишнее.",
  "Убывающая Луна":
    "Время осмысления. Делитесь знаниями и опытом. Отдавайте то, что накопили, — это освобождает пространство для нового.",
  "Последняя четверть":
    "Очищение и отпускание. Избавляйтесь от ненужного — физического и эмоционального.",
  "Убывающий серп":
    "Отдых и восстановление. Прислушайтесь к себе, замедлитесь перед новым циклом.",
};

// Phase-based action guidance (до появления серверной LLM-генерации).
const PHASE_GUIDANCE: Record<string, { favorable: string[]; avoid: string[] }> =
  {
    Новолуние: {
      favorable: [
        "Ставить намерения и цели",
        "Начинать новое дело или проект",
        "Тихие практики и медитация",
      ],
      avoid: [
        "Публичные события и громкие анонсы",
        "Важные переговоры и подписания",
        "Тяжёлые физические нагрузки",
      ],
    },
    "Растущий серп": {
      favorable: [
        "Составлять план на цикл",
        "Искать ресурсы и партнёров",
        "Учиться новому",
      ],
      avoid: [
        "Отказываться от только что начатых инициатив",
        "Затягивать с первыми шагами",
      ],
    },
    "Первая четверть": {
      favorable: [
        "Принимать решения",
        "Преодолевать сопротивление",
        "Активная работа, спорт",
      ],
      avoid: ["Долгие совещания без итогов", "Откладывать сложные разговоры"],
    },
    "Растущая Луна": {
      favorable: [
        "Творчество и самовыражение",
        "Социальные встречи и общение",
        "Продвижение проектов",
      ],
      avoid: ['Крупные траты "на эмоциях"', "Начинать диеты и ограничения"],
    },
    Полнолуние: {
      favorable: [
        "Завершать важные дела",
        "Благодарить и отпускать",
        "Отмечать результаты",
      ],
      avoid: [
        "Ссоры и острые конфликты",
        "Операции и косметические процедуры",
        "Важные решения на эмоциях",
      ],
    },
    "Убывающая Луна": {
      favorable: [
        "Делиться опытом и знаниями",
        "Убирать лишнее из жизни и дома",
        "Завершать долги и обязательства",
      ],
      avoid: [
        "Старт новых амбициозных проектов",
        "Переедание и ночные застолья",
      ],
    },
    "Последняя четверть": {
      favorable: [
        "Глубокая уборка, расхламление",
        "Прощение и отпускание обид",
        "Ревизия планов",
      ],
      avoid: ["Новые знакомства с расчётом на долгое", "Крупные покупки"],
    },
    "Убывающий серп": {
      favorable: [
        "Отдых и восстановление",
        "Медитация, природа, тишина",
        "Подведение итогов цикла",
      ],
      avoid: ["Перегрузки и стресс", "Резкие перемены и переезды"],
    },
  };

export function Moon() {
  const { impact } = useHaptic();
  const { setScreen } = useAppStore();
  const now = new Date();
  const [year] = useState(now.getFullYear());
  const [month] = useState(now.getMonth() + 1);
  const [selectedDay, setSelectedDay] = useState(now.getDate());

  const { data: moonPhase, isLoading: moonLoading } = useQuery({
    queryKey: ["moon-phase"],
    queryFn: horoscopeApi.getMoon,
    staleTime: 1000 * 60 * 60,
  });

  const { data: calendarResp, isLoading: calendarLoading } = useQuery({
    queryKey: ["moon-calendar", year, month],
    queryFn: () => horoscopeApi.getMoonCalendar(year, month),
    staleTime: 1000 * 60 * 60 * 24,
  });
  const calendar = calendarResp?.days;

  const todayNum = now.getDate();
  const selectedData = calendar?.find((d) => d.day === selectedDay);
  const isToday = selectedDay === todayNum;

  const DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

  return (
    <div className="screen moon-screen">
      <div className="screen-header screen-header--with-back">
        <button
          className="back-btn"
          onClick={() => setScreen("discover", "back")}
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
        <h2 className="screen-title">Лунный календарь</h2>
      </div>

      <div className="screen-content">
        {/* Big moon */}
        <div className="moon-hero">
          <motion.div
            key={selectedData?.emoji ?? moonPhase?.emoji}
            className="moon-hero__emoji"
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            {selectedData?.emoji ?? moonPhase?.emoji ?? "🌙"}
          </motion.div>
        </div>

        {/* Phase info for selected day */}
        {moonLoading && !selectedData && <MoonPhaseSkeleton />}
        {(selectedData || moonPhase) &&
          (() => {
            const phaseName =
              selectedData?.phase_name_ru ?? moonPhase?.phase_name_ru ?? "";
            // Prefer server-provided guidance; fall back to local dictionary.
            const serverFav =
              selectedData?.favorable_actions ?? moonPhase?.favorable_actions;
            const serverAvoid =
              selectedData?.avoid_actions ?? moonPhase?.avoid_actions;
            const local = PHASE_GUIDANCE[phaseName];
            const guidance =
              (serverFav && serverFav.length) ||
              (serverAvoid && serverAvoid.length)
                ? {
                    favorable: serverFav ?? local?.favorable ?? [],
                    avoid: serverAvoid ?? local?.avoid ?? [],
                  }
                : local;
            return (
              <>
                <div className="moon-phase-card">
                  <div className="moon-phase-card__date">
                    {selectedDay}{" "}
                    {
                      [
                        "янв",
                        "фев",
                        "мар",
                        "апр",
                        "май",
                        "июн",
                        "июл",
                        "авг",
                        "сен",
                        "окт",
                        "ноя",
                        "дек",
                      ][month - 1]
                    }
                    {isToday ? " · сегодня" : ""}
                  </div>
                  <div className="moon-phase-card__name">{phaseName}</div>
                  <div className="moon-phase-card__illum">
                    Освещённость:{" "}
                    {Math.round(
                      (selectedData?.illumination ??
                        moonPhase?.illumination ??
                        0) * 100,
                    )}
                    %
                  </div>
                  {PHASE_ENERGY[phaseName] && (
                    <p className="moon-phase-card__desc">
                      {PHASE_ENERGY[phaseName]}
                    </p>
                  )}
                </div>

                {guidance && (
                  <div className="moon-guidance">
                    <motion.div
                      key={`fav-${phaseName}`}
                      className="moon-guidance__card moon-guidance__card--favorable"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      <div className="moon-guidance__head">
                        <span className="moon-guidance__dot moon-guidance__dot--ok" />
                        <span className="moon-guidance__title">
                          Благоприятно
                        </span>
                      </div>
                      <ul className="moon-guidance__list">
                        {guidance.favorable.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </motion.div>

                    <motion.div
                      key={`avoid-${phaseName}`}
                      className="moon-guidance__card moon-guidance__card--avoid"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: 0.08 }}
                    >
                      <div className="moon-guidance__head">
                        <span className="moon-guidance__dot moon-guidance__dot--warn" />
                        <span className="moon-guidance__title">
                          Лучше избегать
                        </span>
                      </div>
                      <ul className="moon-guidance__list">
                        {guidance.avoid.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </motion.div>
                  </div>
                )}
              </>
            );
          })()}

        {/* Monthly calendar grid */}
        {calendarLoading && <MoonCalendarSkeleton />}
        {calendar && (
          <div className="moon-calendar">
            <div className="moon-calendar__days-header">
              {DAY_NAMES.map((d) => (
                <div key={d} className="moon-calendar__day-label">
                  {d}
                </div>
              ))}
            </div>
            <div className="moon-calendar__grid">
              {/* Calculate leading empty cells for month start */}
              {(() => {
                const firstDay = new Date(year, month - 1, 1).getDay();
                const leadingCells = firstDay === 0 ? 6 : firstDay - 1;
                const empties = Array.from({ length: leadingCells }, (_, i) => (
                  <div
                    key={`e${i}`}
                    className="moon-calendar__cell moon-calendar__cell--empty"
                  />
                ));
                return empties;
              })()}
              {calendar.map((day) => {
                const isTodayCell = day.day === todayNum;
                const isSelected = day.day === selectedDay;
                return (
                  <motion.div
                    key={day.day}
                    className={`moon-calendar__cell${isTodayCell ? " today" : ""}${isSelected && !isTodayCell ? " selected" : ""}`}
                    onClick={() => {
                      impact("light");
                      setSelectedDay(day.day);
                    }}
                    whileTap={{ scale: 0.88 }}
                    title={day.phase_name_ru}
                  >
                    <span className="moon-calendar__phase">{day.emoji}</span>
                    <span className="moon-calendar__num">{day.day}</span>
                  </motion.div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
