import { useMemo } from 'react';
import type { ChartBodyName, ChartVariant, NatalChartData, PlanetName } from '../types';
import { WHEEL } from '../constants';
import { positionToAbsoluteDegree } from '../utils/geometry';
import { layOutPlanets } from '../utils/planetLayout';
import { AspectLines } from './AspectLines';
import { CenterGlyph } from './CenterGlyph';
import { DegreeLabels } from './DegreeLabels';
import { HouseRing } from './HouseRing';
import { PlanetLayer } from './PlanetLayer';
import { PosterMandala } from './PosterMandala';
import { TickMarks } from './TickMarks';
import { ZodiacRing } from './ZodiacRing';

interface Props {
  data: NatalChartData;
  variant?: ChartVariant;
  onPlanetClick?: (planet: PlanetName) => void;
  onHouseClick?: (house: number) => void;
}

export function ChartWheel({
  data,
  variant = 'editorial',
  onPlanetClick,
  onHouseClick,
}: Props) {
  const ascendantDegree = useMemo(
    () => positionToAbsoluteDegree(data.ascendant),
    [data.ascendant],
  );

  const placed = useMemo(() => layOutPlanets(data.planets), [data.planets]);
  const bodyDegrees = useMemo(() => {
    const ascendantAbs = positionToAbsoluteDegree(data.ascendant);
    const midheavenAbs = positionToAbsoluteDegree(data.midheaven);
    const out = {
      ascendant: ascendantAbs,
      descendant: (ascendantAbs + 180) % 360,
      midheaven: midheavenAbs,
      imumCoeli: (midheavenAbs + 180) % 360,
    } as Record<ChartBodyName, number>;

    (Object.keys(data.planets) as PlanetName[]).forEach((name) => {
      out[name] = positionToAbsoluteDegree(data.planets[name]);
    });

    return out;
  }, [data.ascendant, data.midheaven, data.planets]);
  const isPoster = variant === 'zodiac-poster';
  const isReferenceWheel = variant === 'reference-wheel';
  const isSquareWheel = isPoster || isReferenceWheel;

  return (
    <g data-part="chart-wheel" transform={`translate(${WHEEL.cx} ${WHEEL.cy})`}>
      {isSquareWheel && (
        <g data-part="poster-outer-rings">
          <circle
            r={WHEEL.outerR + 66}
            fill="none"
            stroke="var(--natal-accent)"
            strokeWidth={2}
            opacity={0.9}
          />
          <circle
            r={WHEEL.outerR + 52}
            fill="none"
            stroke="var(--natal-accent)"
            strokeWidth={1}
            opacity={isReferenceWheel ? 0.32 : 0.62}
          />
          {!isReferenceWheel && (
            <circle
              r={WHEEL.outerR + 38}
              fill="none"
              stroke="var(--natal-accent)"
              strokeWidth={2}
              strokeDasharray="1 12"
              strokeLinecap="round"
              opacity={0.7}
            />
          )}
          <circle
            r={WHEEL.outerR + 16}
            fill="none"
            stroke="var(--natal-dim)"
            strokeWidth={1}
            opacity={0.62}
          />
        </g>
      )}

      {/* three master circles — the armature of the wheel */}
      <circle r={WHEEL.outerR}  fill="none" stroke="var(--natal-primary)" strokeWidth={1.5} opacity={0.9} />
      <circle r={WHEEL.middleR} fill="none" stroke="var(--natal-primary)" strokeWidth={1.5} opacity={0.9} />
      <circle r={WHEEL.innerR}  fill="none" stroke="var(--natal-primary)" strokeWidth={1.2} opacity={0.8} />

      <TickMarks ascendantDegree={ascendantDegree} variant={variant} />
      <ZodiacRing ascendantDegree={ascendantDegree} variant={variant} />
      <HouseRing
        houses={data.houses}
        ascendantDegree={ascendantDegree}
        variant={variant}
        onHouseClick={onHouseClick}
      />

      {isReferenceWheel && (
        <g data-part="reference-aspect-field">
          <circle
            r={WHEEL.planetR - 36}
            fill="rgba(4, 7, 26, 0.22)"
            stroke="var(--natal-accent)"
            strokeWidth={0.9}
            opacity={0.34}
          />
          <circle
            r={WHEEL.planetR - 82}
            fill="none"
            stroke="var(--natal-accent)"
            strokeWidth={0.7}
            opacity={0.24}
          />
        </g>
      )}

      <AspectLines
        aspects={data.aspects}
        bodyDegrees={bodyDegrees}
        ascendantDegree={ascendantDegree}
        variant={variant}
      />

      <PlanetLayer
        placed={placed}
        ascendantDegree={ascendantDegree}
        variant={variant}
        onPlanetClick={onPlanetClick}
      />

      {!isPoster && (
        <DegreeLabels placed={placed} ascendantDegree={ascendantDegree} />
      )}

      {isPoster ? (
        <PosterMandala />
      ) : isReferenceWheel ? (
        <g data-part="reference-center">
          <circle
            r={12}
            fill="rgba(6, 9, 30, 0.72)"
            stroke="var(--natal-accent)"
            strokeWidth={1.5}
            opacity={0.9}
          />
          <circle
            r={38}
            fill="none"
            stroke="var(--natal-accent)"
            strokeWidth={0.6}
            strokeDasharray="1 7"
            opacity={0.18}
          />
        </g>
      ) : (
        <CenterGlyph />
      )}
    </g>
  );
}
