import { useMemo } from 'react';
import type { ChartBodyName, ChartVariant, NatalChartData, PlanetName } from '../types';
import { WHEEL } from '../constants';
import { polar, positionToAbsoluteDegree, zodiacToSvgAngle } from '../utils/geometry';
import { layOutPlanets } from '../utils/planetLayout';
import { AspectLines } from './AspectLines';
import { CenterGlyph } from './CenterGlyph';
import { DegreeLabels } from './DegreeLabels';
import { HouseRing } from './HouseRing';
import { PlanetLayer } from './PlanetLayer';
import { PosterMandala } from './PosterMandala';
import { TickMarks } from './TickMarks';
import { ZodiacRing } from './ZodiacRing';
import { ZodiacSymbolIcon } from './SymbolIcons';
import styles from '../NatalChart.module.css';

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

  const isPoster = variant === 'zodiac-poster';
  const isReferenceWheel = variant === 'reference-wheel';
  const isSquareWheel = isPoster || isReferenceWheel;
  const placed = useMemo(
    () => layOutPlanets(data.planets, isReferenceWheel ? 'zodiac-band' : 'stacked'),
    [data.planets, isReferenceWheel],
  );
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
      const planet = data.planets[name];
      if (!planet || planet.hidden) return;
      out[name] = positionToAbsoluteDegree(planet);
    });

    return out;
  }, [data.ascendant, data.midheaven, data.planets]);
  const aspectBodyDegrees = useMemo(() => {
    if (!isReferenceWheel) return bodyDegrees;

    const out = { ...bodyDegrees };
    placed.forEach((planet) => {
      out[planet.name] = planet.displayAbsDeg;
    });
    return out;
  }, [bodyDegrees, isReferenceWheel, placed]);
  const centerRays = useMemo(
    () =>
      Array.from({ length: 60 }, (_, i) => {
        const angle = i * 6 - 90;
        const big = i % 5 === 0;
        const p1 = polar(0, 0, 48, angle);
        const p2 = polar(0, 0, big ? 61 : 56, angle);
        return { ...p1, x2: p2.x, y2: p2.y, big };
      }),
    [],
  );

  return (
    <g data-part="chart-wheel" transform={`translate(${WHEEL.cx} ${WHEEL.cy})`}>
      {isReferenceWheel && (
        <circle
          r={WHEEL.outerR + 3}
          fill="rgba(24, 14, 58, 0.18)"
          stroke="none"
        />
      )}

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
      {isReferenceWheel && (
        <>
          <circle r={WHEEL.innerR - 12} fill="none" stroke="var(--natal-accent)" strokeWidth={0.8} opacity={0.28} />
          <circle r={WHEEL.innerR - 42} fill="none" stroke="var(--natal-accent)" strokeWidth={0.75} opacity={0.24} />
          <circle r={WHEEL.innerR - 54} fill="none" stroke="var(--natal-accent)" strokeWidth={0.7} opacity={0.2} />
          <circle r={WHEEL.innerR - 104} fill="none" stroke="var(--natal-accent)" strokeWidth={0.7} opacity={0.17} />
        </>
      )}

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
          {Array.from({ length: 12 }, (_, i) => {
            const svgAng = zodiacToSvgAngle(i * 30, ascendantDegree);
            const p1 = polar(0, 0, WHEEL.innerR - 54, svgAng);
            const p2 = polar(0, 0, WHEEL.innerR - 12, svgAng);
            return (
              <line
                key={`planet-band-divider-${i}`}
                x1={p1.x}
                y1={p1.y}
                x2={p2.x}
                y2={p2.y}
                stroke="var(--natal-accent)"
                strokeWidth={0.6}
                opacity={0.18}
              />
            );
          })}
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
        bodyDegrees={aspectBodyDegrees}
        ascendantDegree={ascendantDegree}
        variant={variant}
      />

      <PlanetLayer
        placed={placed}
        ascendantDegree={ascendantDegree}
        variant={variant}
        onPlanetClick={onPlanetClick}
      />

      {!isPoster && !isReferenceWheel && (
        <DegreeLabels placed={placed} ascendantDegree={ascendantDegree} />
      )}

      {isPoster ? (
        <PosterMandala />
      ) : isReferenceWheel ? (
        <g data-part="reference-center">
          {centerRays.map((ray, i) => (
            <line
              key={i}
              x1={ray.x}
              y1={ray.y}
              x2={ray.x2}
              y2={ray.y2}
              stroke="var(--natal-accent)"
              strokeWidth={ray.big ? 0.85 : 0.45}
              opacity={ray.big ? 0.5 : 0.2}
            />
          ))}
          <circle
            r={44}
            fill="rgba(5, 7, 24, 0.92)"
            stroke="var(--natal-accent)"
            strokeWidth={1.4}
            opacity={0.96}
          />
          <circle
            r={38}
            fill="none"
            stroke="var(--natal-accent)"
            strokeWidth={0.6}
            opacity={0.72}
          />
          <circle
            r={14}
            fill="rgba(5, 7, 24, 0.72)"
            stroke="var(--natal-accent)"
            strokeWidth={0.65}
            opacity={0.9}
          />
          <g transform="translate(-34 -34)" className={styles.referenceCenterSymbol}>
            <ZodiacSymbolIcon sign={data.ascendant.sign} size={68} strokeWidth={1.9} />
          </g>
        </g>
      ) : (
        <CenterGlyph />
      )}
    </g>
  );
}
