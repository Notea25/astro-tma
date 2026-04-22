import { useMemo } from 'react';
import type { PlanetName } from '../types';
import type { PlacedPlanet } from '../utils/planetLayout';
import { WHEEL } from '../constants';
import { polar, zodiacToSvgAngle } from '../utils/geometry';
import { formatDegreeMinute } from '../utils/formatting';
import styles from '../NatalChart.module.css';

interface Props {
  placed: PlacedPlanet[];
  ascendantDegree: number;
}

/** Tangent-oriented rotation that flips so the text always reads right-side-up.
 *  At north: 0°. At east: +90° (top-to-bottom). At south: 0° (flipped back).
 *  At west: -90° (bottom-to-top). Diagonals interpolate. */
function labelRotation(svgAng: number): number {
  const n = ((svgAng % 360) + 360) % 360;
  // For the "bottom half" (n in (0, 180)) subtract 90 to avoid upside-down text;
  // elsewhere add 90 for tangent orientation.
  const r = n > 0 && n < 180 ? n - 90 : n + 90;
  return ((r + 180) % 360 + 360) % 360 - 180;
}

/** Push each label forward along the ring so consecutive labels stay at least
 *  MIN_ANGLE apart. A single forward pass — safe for our ≤ 12 bodies, stops
 *  labels from piling up in tight clusters (e.g. stellium in Virgo/Libra). */
const MIN_LABEL_ANGLE = 5.5;

function resolveLabelAngles(placed: PlacedPlanet[]): Map<PlanetName, number> {
  const sorted = [...placed].sort((a, b) => a.absDeg - b.absDeg);
  const out = new Map<PlanetName, number>();
  let prev = Number.NEGATIVE_INFINITY;
  for (const p of sorted) {
    const angle = Math.max(p.absDeg, prev + MIN_LABEL_ANGLE);
    out.set(p.name, angle);
    prev = angle;
  }
  return out;
}

const LABEL_R = WHEEL.outerR + 26;
const LEADER_INNER_R = WHEEL.outerR + 2;
const LEADER_OUTER_R = WHEEL.outerR + 16;

export function DegreeLabels({ placed, ascendantDegree }: Props) {
  const labelAngles = useMemo(() => resolveLabelAngles(placed), [placed]);

  return (
    <g data-part="degree-labels">
      {placed.map(({ name, position, absDeg, radius }) => {
        const planetSvg = zodiacToSvgAngle(absDeg, ascendantDegree);
        const labelAbs = labelAngles.get(name) ?? absDeg;
        const labelSvg = zodiacToSvgAngle(labelAbs, ascendantDegree);

        // Inward hairline: from ring edge down to the planet glyph — makes it
        // obvious which planet a label belongs to when the glyph has been
        // pushed inward by collision resolution.
        const innerHairlineStart = polar(0, 0, WHEEL.middleR, planetSvg);
        const innerHairlineEnd = polar(0, 0, radius + 14, planetSvg);

        // Outward leader: from just outside the ring at the planet's angle,
        // kinking out to the (possibly offset) label position.
        const l1 = polar(0, 0, LEADER_INNER_R, planetSvg);
        const l2 = polar(0, 0, LEADER_OUTER_R, labelSvg);
        const labelPos = polar(0, 0, LABEL_R, labelSvg);
        const rot = labelRotation(labelSvg);

        return (
          <g key={name} data-planet={name}>
            {/* hairline inward — only drawn when the planet has been offset
                radially (otherwise it would sit directly under the glyph) */}
            {radius < WHEEL.planetR && (
              <line
                x1={innerHairlineStart.x}
                y1={innerHairlineStart.y}
                x2={innerHairlineEnd.x}
                y2={innerHairlineEnd.y}
                stroke="var(--natal-dim)"
                strokeWidth={1}
              />
            )}
            <line
              x1={l1.x}
              y1={l1.y}
              x2={l2.x}
              y2={l2.y}
              stroke="var(--natal-dim)"
              strokeWidth={1}
            />
            <text
              x={labelPos.x}
              y={labelPos.y}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={10}
              fill="var(--natal-primary)"
              className={styles.bodyText}
              opacity={0.85}
              transform={`rotate(${rot.toFixed(2)}, ${labelPos.x.toFixed(2)}, ${labelPos.y.toFixed(2)})`}
            >
              {formatDegreeMinute(position)}
            </text>
          </g>
        );
      })}
    </g>
  );
}
