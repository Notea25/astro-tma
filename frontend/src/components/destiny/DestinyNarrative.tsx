import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { destinyApi } from "@/services/api";

const SECTION_LABELS_RU: Record<string, string> = {
  who_you_are: "Кто вы",
  mission: "Ваше предназначение",
  money: "Деньги и реализация",
  love: "Любовь и отношения",
  health: "Тело и здоровье",
  karma: "Карма и род",
  advice: "Совет",
};

// The interpreter returns this exact order in the LLM response.
const SECTION_ORDER = [
  "who_you_are", "mission", "money", "love", "health", "karma", "advice",
] as const;

interface Props {
  enabled: boolean;
}

export function DestinyNarrative({ enabled }: Props) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["destiny-matrix", "interpretation"],
    queryFn: destinyApi.getInterpretation,
    enabled,
    staleTime: 1000 * 60 * 60 * 24 * 7, // 7 days — interpreter caches in DB anyway
  });

  if (!enabled) return null;

  if (isLoading) {
    return (
      <div className="destiny-narrative__loading">
        <p>Астролог пишет ваш разбор…</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="destiny-narrative__loading">
        <p>Не удалось загрузить разбор.</p>
        <button type="button" className="btn-ghost" onClick={() => refetch()}>
          Повторить
        </button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <section className="destiny-narrative">
      <h3 className="destiny-narrative__title">Личный разбор</h3>
      {SECTION_ORDER.map((key, idx) => {
        const text = data.sections[key];
        if (!text) return null;
        return (
          <motion.div
            key={key}
            className="destiny-narrative__section"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 * idx, duration: 0.3 }}
          >
            <h4 className="destiny-narrative__section-title">
              {SECTION_LABELS_RU[key] ?? key}
            </h4>
            <p className="destiny-narrative__section-text">{text}</p>
          </motion.div>
        );
      })}
    </section>
  );
}
