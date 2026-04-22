import { useMemo } from 'react';
import type { NatalChartData, PlanetName } from '../types';
import { WHEEL } from '../constants';
import { positionToAbsoluteDegree } from '../utils/geometry';
import { layOutPlanets } from '../utils/planetLayout';
import { AspectLines } from './AspectLines';
import { CenterGlyph } from './CenterGlyph';
import { DegreeLabels } from './DegreeLabels';
import { HouseRing } from './HouseRing';
import { PlanetLayer } from './PlanetLayer';
import { TickMarks } from './TickMarks';
import { ZodiacRing } from './ZodiacRing';

interface Props {
  data: NatalChartData;
  onPlanetClick?: (planet: PlanetName) => void;
  onHouseClick?: (house: number) => void;
}

export function ChartWheel({ data, onPlanetClick, onHouseClick }: Props) {
  const ascendantDegree = useMemo(
    () => positionToAbsoluteDegree(data.ascendant),
    [data.ascendant],
  );

  const placed = useMemo(() => layOutPlanets(data.planets), [data.planets]);

  return (
    <g data-part="chart-wheel" transform={`translate(${WHEEL.cx} ${WHEEL.cy})`}>
      {/* three master circles — the armature of the wheel */}
      <circle r={WHEEL.outerR}  fill="none" stroke="var(--natal-primary)" strokeWidth={1.5} opacity={0.9} />
      <circle r={WHEEL.middleR} fill="none" stroke="var(--natal-primary)" strokeWidth={1.5} opacity={0.9} />
      <circle r={WHEEL.innerR}  fill="none" stroke="var(--natal-primary)" strokeWidth={1.2} opacity={0.8} />

      <TickMarks ascendantDegree={ascendantDegree} />
      <ZodiacRing ascendantDegree={ascendantDegree} />
      <HouseRing
        houses={data.houses}
        ascendantDegree={ascendantDegree}
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

      <DegreeLabels placed={placed} ascendantDegree={ascendantDegree} />

      <CenterGlyph />
    </g>
  );
}
