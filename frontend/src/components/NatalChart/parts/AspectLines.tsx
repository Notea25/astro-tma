import { useMemo } from 'react';
import type { Aspect, PlanetName, PlanetPosition } from '../types';
import { WHEEL } from '../constants';
import { polar, positionToAbsoluteDegree, zodiacToSvgAngle } from '../utils/geometry';
import { getAspectStyle } from '../utils/aspects';

interface Props {
  aspects: Aspect[];
  planets: Record<PlanetName, PlanetPosition>;
  ascendantDegree: number;
}

/** Small radial inset so lines don't kiss the inner circle stroke. */
const EDGE_INSET = 4;

export function AspectLines({ aspects, planets, ascendantDegree }: Props) {
  const angles = useMemo(() => {
    const out = {} as Record<PlanetName, number>;
    (Object.keys(planets) as PlanetName[]).forEach((name) => {
      out[name] = zodiacToSvgAngle(
        positionToAbsoluteDegree(planets[name]),
        ascendantDegree,
      );
    });
    return out;
  }, [planets, ascendantDegree]);

  const r = WHEEL.innerR - EDGE_INSET;

  return (
    <g data-part="aspect-lines">
      {aspects.map((asp, i) => {
        const a1 = angles[asp.planet1];
        const a2 = angles[asp.planet2];
        // Skip if we somehow don't have a position for either planet.
        if (a1 === undefined || a2 === undefined) return null;

        const p1 = polar(0, 0, r, a1);
        const p2 = polar(0, 0, r, a2);
        const s = getAspectStyle(asp.type);

        return (
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
