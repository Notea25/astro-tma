import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { destinyV3Api, type V3ReadingResponse } from "@/services/api";

interface Props {
  enabled: boolean;
  onUpgrade?: () => void;
}

/**
 * 15-section accordion. Top-level loading state covers the cold-start
 * (~60s while Sonnet generates everything). Once cached in DB, the
 * `/reading` endpoint returns instantly and the accordion shows all
 * sections.
 *
 * For non-premium users only the two `free_keys` sections come back
 * with real content; the other 13 carry a teaser string and are
 * rendered with a lock badge.
 */
export function DestinyV3Narrative({ enabled, onUpgrade }: Props) {
  const [openKey, setOpenKey] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery<V3ReadingResponse>({
    queryKey: ["destiny-matrix-v3", "reading"],
    queryFn: destinyV3Api.getReading,
    enabled,
    staleTime: 1000 * 60 * 60 * 24 * 7,
    gcTime: 1000 * 60 * 60 * 24 * 7,
  });

  if (!enabled) return null;

  if (isLoading) {
    return (
      <div className="destiny-narrative__loading">
        <p>Готовим ваш разбор по 20 разделам…</p>
        <p className="destiny-v3__hint">
          Это занимает 30–60 секунд при первом запуске.
        </p>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="destiny-narrative__loading">
        <p>Не удалось загрузить разбор.</p>
        <button type="button" className="btn-ghost" onClick={() => refetch()}>
          Повторить
        </button>
      </div>
    );
  }

  return (
    <section className="destiny-narrative destiny-v3">
      <h3 className="destiny-narrative__title">Личный разбор · 20 разделов</h3>

      {data.year_energy && (
        <p className="destiny-v3__year-energy">
          Энергия года: <strong>{data.year_energy.current}</strong>
          {" → "}
          <strong>{data.year_energy.upcoming}</strong>{" "}
          <span className="destiny-v3__year-hint">
            (текущий → следующий после Дня рождения)
          </span>
        </p>
      )}

      {data.sections.map((section, idx) => {
        const isOpen = openKey === section.key;
        const isLocked = section.locked;
        const titleSuffix = sectionTitleSuffix(section.key, data);

        return (
          <motion.div
            key={section.key}
            className={`destiny-narrative__section${isLocked ? " is-locked" : ""}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.03 * idx, duration: 0.25 }}
          >
            <button
              type="button"
              className="destiny-v3__head"
              onClick={() => setOpenKey(isOpen ? null : section.key)}
              aria-expanded={isOpen}
            >
              <span className="destiny-narrative__section-title">
                {section.title}
                {titleSuffix && (
                  <span className="destiny-v3__title-suffix">{titleSuffix}</span>
                )}
                {isLocked && <span className="destiny-narrative__lock">🔒</span>}
              </span>
              <span className="destiny-v3__chevron" aria-hidden>
                {isOpen ? "▾" : "▸"}
              </span>
            </button>

            <AnimatePresence initial={false}>
              {isOpen && (
                <motion.div
                  key="body"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.22 }}
                  className="destiny-v3__body"
                >
                  <div className="destiny-narrative__section-text destiny-v3__content">
                    {section.content
                      ? plainText(section.content)
                      : "Раздел временно недоступен. Попробуйте обновить страницу."}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        );
      })}

      {!data.has_full_access && onUpgrade && (
        <button
          type="button"
          className="btn-stars destiny-narrative__upgrade"
          onClick={onUpgrade}
        >
          Открыть полный разбор · 20 разделов
        </button>
      )}
    </section>
  );
}

/**
 * Soft markdown→plaintext: strip leading `#` levels and `**bold**`
 * markers — the system prompt asks the model to skip markdown, but
 * Sonnet sometimes adds a header anyway. CSS `white-space: pre-line`
 * handles paragraph breaks.
 */
function plainText(raw: string): string {
  return raw
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "$1")
    // Sweep stray asterisks from unbalanced markers — never leak raw "*" into UI.
    .replace(/\*+/g, "")
    .replace(/```[\s\S]*?```/g, "")
    .trim();
}

/**
 * Section-specific title suffixes: karmic_tail gets the canonical
 * program name, year_energy gets the two arcana numbers. Everything
 * else returns an empty string.
 */
function sectionTitleSuffix(
  key: string, reading: V3ReadingResponse,
): string {
  if (key === "karmic_tail" && reading.karmic_program?.name) {
    return ` · ${reading.karmic_program.name}`;
  }
  if (key === "year_energy") {
    return ` · ${reading.year_energy.current} → ${reading.year_energy.upcoming}`;
  }
  return "";
}
