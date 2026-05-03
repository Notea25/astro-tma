/**
 * Full synastry report — the celestial-styled equivalent of geocult's layout.
 *
 *   1. Pair summary (LLM-generated, single short paragraph)
 *   2. Sphere bars (love / communication / trust / passion / overall)
 *   3. Bi-wheel chart (SynastryBiWheel)
 *   4. Two planet tables (one per partner)
 *   5. Per-aspect interpretations grouped by planet, with aspect glyph + orb
 *
 * Reusable across SynastryInvite (incoming link) and the regular Synastry
 * screen (manual / past results) — all data comes from a SynastryResult.
 */
import { motion } from "framer-motion";
import type { SynastryResult } from "@/types";
import { SynastryBiWheel } from "./SynastryBiWheel";

const PLANET_GLYPH: Record<string, string> = {
  sun: "☉",
  moon: "☽",
  mercury: "☿",
  venus: "♀",
  mars: "♂",
  jupiter: "♃",
  saturn: "♄",
  uranus: "♅",
  neptune: "♆",
  pluto: "♇",
  chiron: "⚷",
  true_node: "☊",
  mean_node: "☊",
  lilith: "⚸",
};

const ASPECT_SYMBOL: Record<string, string> = {
  conjunction: "☌",
  trine: "△",
  sextile: "⚹",
  square: "□",
  opposition: "☍",
};

const ASPECT_COLOR: Record<string, string> = {
  conjunction: "#e8c97e",
  trine: "#8bc89b",
  sextile: "#7ec8e3",
  square: "#e88b8b",
  opposition: "#c58be8",
};

const PLANET_ORDER = [
  "sun",
  "moon",
  "mercury",
  "venus",
  "mars",
  "jupiter",
  "saturn",
  "uranus",
  "neptune",
  "pluto",
];

const SPHERE_LABELS: { key: keyof SynastryResult["scores"]; label: string }[] = [
  { key: "overall", label: "Общая" },
  { key: "love", label: "Любовь" },
  { key: "communication", label: "Общение" },
  { key: "trust", label: "Доверие" },
  { key: "passion", label: "Страсть" },
];

interface Props {
  result: SynastryResult;
}

export function SynastryReport({ result }: Props) {
  const interpretationsByPlanet = groupInterpretationsByPlanet(result);

  return (
    <div className="synastry-report">
      {/* ── Header pair ── */}
      <div className="horoscope-card">
        <div
          className="horoscope-card__period"
          style={{ marginBottom: 14, textAlign: "center" }}
        >
          {result.initiator_name ?? "—"} <span style={{ opacity: 0.5 }}>×</span>{" "}
          {result.partner_name ?? "—"}
        </div>

        {/* Sphere bars */}
        <div className="energy-bars">
          {SPHERE_LABELS.map(({ key, label }) => (
            <div key={key} className="energy-row">
              <span className="energy-label">{label}</span>
              <div className="energy-track">
                <motion.div
                  className="energy-fill"
                  initial={{ width: 0 }}
                  animate={{ width: `${result.scores[key]}%` }}
                  transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
                />
              </div>
              <span className="energy-val">{result.scores[key]}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Pair summary ── */}
      {result.summary_ru && (
        <div className="horoscope-card">
          <div
            className="horoscope-card__period"
            style={{ marginBottom: 10 }}
          >
            ✦ Портрет отношений
          </div>
          <p style={{ whiteSpace: "pre-wrap", lineHeight: 1.55, fontSize: 14 }}>
            {result.summary_ru}
          </p>
        </div>
      )}

      {/* ── Bi-wheel chart ── */}
      {(result.planets_a.length > 0 || result.planets_b.length > 0) && (
        <div className="horoscope-card">
          <div
            className="horoscope-card__period"
            style={{ marginBottom: 12 }}
          >
            Биколесо
          </div>
          <SynastryBiWheel
            planetsA={result.planets_a}
            planetsB={result.planets_b}
            housesA={result.houses_a}
            aspects={result.aspects}
            initiatorName={result.initiator_name}
            partnerName={result.partner_name}
          />
        </div>
      )}

      {/* ── Planet tables ── */}
      {result.planets_a.length > 0 && (
        <PlanetTable
          name={result.initiator_name}
          planets={result.planets_a}
        />
      )}
      {result.planets_b.length > 0 && (
        <PlanetTable
          name={result.partner_name}
          planets={result.planets_b}
        />
      )}

      {/* ── Per-aspect interpretations grouped by planet ── */}
      {result.interpretations.length > 0 && (
        <div className="horoscope-card">
          <div
            className="horoscope-card__period"
            style={{ marginBottom: 10 }}
          >
            Аспекты по планетам
          </div>
          {PLANET_ORDER.map((planet) => {
            const items = interpretationsByPlanet[planet];
            if (!items || items.length === 0) return null;
            return (
              <div key={planet} className="syn-planet-block">
                <h4 className="syn-planet-block__title">
                  <span className="syn-planet-block__glyph">
                    {PLANET_GLYPH[planet] ?? "●"}
                  </span>
                  {capitalize(items[0].anchorName)}
                </h4>
                {items.map((it, idx) => (
                  <motion.div
                    key={`${planet}-${idx}`}
                    className="syn-aspect-card"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: idx * 0.04 }}
                  >
                    <div className="syn-aspect-card__header">
                      <span>
                        {it.p1_name_ru} {it.aspect_ru} {it.p2_name_ru}
                      </span>
                      <span
                        className="syn-aspect-card__symbol"
                        style={{
                          color:
                            ASPECT_COLOR[it.aspect] ?? "var(--gold-dim)",
                        }}
                      >
                        {ASPECT_SYMBOL[it.aspect] ?? it.aspect_ru}
                      </span>
                      <span className="syn-aspect-card__orb">
                        {it.orb.toFixed(1)}°
                      </span>
                    </div>
                    <p className="syn-aspect-card__text">{it.text_ru}</p>
                  </motion.div>
                ))}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Raw aspect table (compact, kept for reference) ── */}
      {result.aspects.length > 0 && (
        <div className="horoscope-card">
          <div
            className="horoscope-card__period"
            style={{ marginBottom: 12 }}
          >
            Все ключевые аспекты ({result.total_aspects} всего)
          </div>
          <div className="transits-list">
            {result.aspects.map((a, idx) => (
              <div key={idx} className="transit-row">
                <span className="transit-row__planet">
                  {PLANET_GLYPH[a.p1_name.toLowerCase()] ?? "●"}{" "}
                  {a.p1_name_ru}
                </span>
                <span
                  className="transit-row__aspect"
                  style={{
                    color: ASPECT_COLOR[a.aspect] ?? "var(--text-dim)",
                  }}
                >
                  {ASPECT_SYMBOL[a.aspect] ?? a.aspect_ru}
                </span>
                <span className="transit-row__planet">
                  {PLANET_GLYPH[a.p2_name.toLowerCase()] ?? "●"}{" "}
                  {a.p2_name_ru}
                </span>
                <span className="transit-row__orb">{a.orb.toFixed(1)}°</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function PlanetTable({
  name,
  planets,
}: {
  name: string | null;
  planets: SynastryResult["planets_a"];
}) {
  return (
    <div className="horoscope-card">
      <div className="horoscope-card__period" style={{ marginBottom: 10 }}>
        Планеты — {name ?? "—"}
      </div>
      <div className="syn-planet-table">
        {planets
          .filter((p) => PLANET_ORDER.includes(p.name.toLowerCase()))
          .map((p) => (
            <div key={p.name} className="syn-planet-row">
              <span className="syn-planet-row__glyph">
                {PLANET_GLYPH[p.name.toLowerCase()] ?? "●"}
              </span>
              <span className="syn-planet-row__name">{p.name_ru}</span>
              <span className="syn-planet-row__sign">
                {p.sign_ru || p.sign}
                {p.retrograde && (
                  <span className="syn-planet-row__retro"> ℞</span>
                )}
              </span>
              <span className="syn-planet-row__deg">
                {p.sign_degree.toFixed(0)}°
              </span>
              <span className="syn-planet-row__house">
                {p.house ? `${p.house} дом` : "—"}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
}

type PlanetGroupItem = SynastryResult["interpretations"][number] & {
  anchorName: string;
};

/** Groups each interpretation under the planet with the higher significance
 * (Sun > Moon > inner > social > outer). The first planet listed is what
 * the user sees as the section anchor. */
function groupInterpretationsByPlanet(
  result: SynastryResult,
): Record<string, PlanetGroupItem[]> {
  const groups: Record<string, PlanetGroupItem[]> = {};
  for (const it of result.interpretations) {
    const a = it.p1_name.toLowerCase();
    const b = it.p2_name.toLowerCase();
    const idxA = PLANET_ORDER.indexOf(a);
    const idxB = PLANET_ORDER.indexOf(b);
    let anchor: string;
    let anchorRu: string;
    if (idxA === -1 && idxB === -1) {
      anchor = a;
      anchorRu = it.p1_name_ru;
    } else if (idxA === -1) {
      anchor = b;
      anchorRu = it.p2_name_ru;
    } else if (idxB === -1) {
      anchor = a;
      anchorRu = it.p1_name_ru;
    } else {
      anchor = idxA <= idxB ? a : b;
      anchorRu = idxA <= idxB ? it.p1_name_ru : it.p2_name_ru;
    }
    if (!groups[anchor]) groups[anchor] = [];
    groups[anchor].push({ ...it, anchorName: anchorRu });
  }
  return groups;
}

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}
