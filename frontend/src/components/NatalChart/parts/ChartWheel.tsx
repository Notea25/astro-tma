import { useMemo } from 'react';
import type { ChartVariant, NatalChartData, PlanetName } from '../types';
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
  const isPoster = variant === 'zodiac-poster';

  return (
    <g data-part="chart-wheel" transform={`translate(${WHEEL.cx} ${WHEEL.cy})`}>
      {isPoster && (
        <g data-part="poster-outer-rings">
          <circle r={WHEEL.outerR + 66} fill="none" stroke="var(--natal-accent)" strokeWidth={2} opacity={0.9} />
          <circle r={WHEEL.outerR + 52} fill="none" stroke="var(--natal-accent)" strokeWidth={1} opacity={0.62} />
          <circle
            r={WHEEL.outerR + 38}
            fill="none"
            stroke="var(--natal-accent)"
            strokeWidth={2}
            strokeDasharray="1 12"
            strokeLinecap="round"
            opacity={0.7}
          />
          <circle r={WHEEL.outerR + 16} fill="none" stroke="var(--natal-dim)" strokeWidth={1} opacity={0.62} />
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

      <AspectLines
        aspects={data.aspects}
        planets={data.planets}
        ascendantDegree={ascendantDegree}
      />

      <PlanetLayer
        placed={placed}
        ascendantDegree={ascendantDegree}
        onPlanetClick={onPlanetClick}
      />

      {!isPoster && (
        <DegreeLabels placed={placed} ascendantDegree={ascendantDegree} />
      )}

      {isPoster ? <PosterMandala /> : <CenterGlyph />}
    </g>
  );
}
