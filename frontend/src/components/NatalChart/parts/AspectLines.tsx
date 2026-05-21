import { useMemo } from 'react';
import type { Aspect, ChartBodyName, ChartVariant } from '../types';
import { WHEEL } from '../constants';
import { polar, zodiacToSvgAngle } from '../utils/geometry';
import { getAspectStyle } from '../utils/aspects';

interface Props {
  aspects: Aspect[];
  bodyDegrees: Record<ChartBodyName, number>;
  ascendantDegree: number;
  variant?: ChartVariant;
}

/** Keep aspect lines inside the planet glyph ring so they don't visually cross labels. */
const EDGE_INSET = 4;
const REFERENCE_ASPECT_R = 156;
const REFERENCE_MAX_ASPECTS = 7;

export function AspectLines({
  aspects,
  bodyDegrees,
  ascendantDegree,
  variant = 'editorial',
}: Props) {
  const isReferenceWheel = variant === 'reference-wheel';
  const angles = useMemo(() => {
    const out = {} as Record<ChartBodyName, number>;
    (Object.keys(bodyDegrees) as ChartBodyName[]).forEach((name) => {
      out[name] = zodiacToSvgAngle(bodyDegrees[name], ascendantDegree);
    });
    return out;
  }, [bodyDegrees, ascendantDegree]);

  const displayAspects = useMemo(
    () =>
      isReferenceWheel
        ? [...aspects].sort((a, b) => a.orb - b.orb).slice(0, REFERENCE_MAX_ASPECTS)
        : aspects,
    [aspects, isReferenceWheel],
  );
  const r = isReferenceWheel ? REFERENCE_ASPECT_R : WHEEL.innerR - EDGE_INSET;

  return (
    <g data-part="aspect-lines">
      {displayAspects.map((asp, i) => {
        const a1 = angles[asp.planet1];
        const a2 = angles[asp.planet2];
        // Skip if we somehow don't have a position for either planet.
        if (a1 === undefined || a2 === undefined) return null;

        const p1 = polar(0, 0, r, a1);
        const p2 = polar(0, 0, r, a2);
        const s = getAspectStyle(asp.type);
        const referenceOpacity = Math.max(0.18, Math.min(0.46, 0.54 - asp.orb * 0.055));

        return isReferenceWheel ? (
          <g key={`${asp.planet1}-${asp.planet2}-${asp.type}-${i}`}>
            <polyline
              points={`${p1.x},${p1.y} 0,0 ${p2.x},${p2.y}`}
              fill="none"
              stroke="var(--natal-accent)"
              strokeWidth={2.1}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={0.07}
            />
            <polyline
              points={`${p1.x},${p1.y} 0,0 ${p2.x},${p2.y}`}
              fill="none"
              stroke="var(--natal-accent)"
              strokeWidth={0.65}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={referenceOpacity}
            />
          </g>
        ) : (
          <line
            key={`${asp.planet1}-${asp.planet2}-${asp.type}-${i}`}
            x1={p1.x}
            y1={p1.y}
            x2={p2.x}
            y2={p2.y}
            stroke={s.stroke}
            strokeWidth={1}
            strokeDasharray={s.dasharray}
            opacity={s.opacity}
          />
        );
      })}
    </g>
  );
}
