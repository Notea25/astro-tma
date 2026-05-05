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

/** Small radial inset so lines don't kiss the inner circle stroke. */
const EDGE_INSET = 4;

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
        ? [...aspects].sort((a, b) => b.orb - a.orb)
        : aspects,
    [aspects, isReferenceWheel],
  );
  const r = isReferenceWheel ? WHEEL.planetR - 48 : WHEEL.innerR - EDGE_INSET;

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
        const referenceOpacity = Math.max(0.24, Math.min(0.62, 0.72 - asp.orb * 0.06));

        return isReferenceWheel ? (
          <g key={`${asp.planet1}-${asp.planet2}-${asp.type}-${i}`}>
            <line
              x1={p1.x}
              y1={p1.y}
              x2={p2.x}
              y2={p2.y}
              stroke="var(--natal-accent)"
              strokeWidth={1.8}
              strokeLinecap="round"
              opacity={0.07}
            />
            <line
              x1={p1.x}
              y1={p1.y}
              x2={p2.x}
              y2={p2.y}
              stroke="var(--natal-accent)"
              strokeWidth={0.78}
              strokeLinecap="round"
              opacity={referenceOpacity}
            >
              <title>
                {`${asp.planet1} ${asp.type} ${asp.planet2} (orb ${asp.orb.toFixed(1)}°)`}
              </title>
            </line>
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
          >
            <title>
              {`${asp.planet1} ${asp.type} ${asp.planet2} (orb ${asp.orb.toFixed(1)}°)`}
            </title>
          </line>
        );
      })}
    </g>
  );
}
