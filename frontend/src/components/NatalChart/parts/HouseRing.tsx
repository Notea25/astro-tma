import clsx from 'clsx';
import type { ChartVariant, HousePosition } from '../types';
import { ROMAN, WHEEL, ZODIAC_LABEL } from '../constants';
import { polar, sectorPath, zodiacToSvgAngle } from '../utils/geometry';
import styles from '../NatalChart.module.css';

interface Props {
  houses: HousePosition[];
  ascendantDegree: number;
  variant?: ChartVariant;
  onHouseClick?: (house: number) => void;
}

const ROMAN_FONT_SIZE = 19;

function midpointCCW(fromDeg: number, toDeg: number): number {
  const span = ((toDeg - fromDeg) % 360 + 360) % 360;
  return (fromDeg + span / 2) % 360;
}

export function HouseRing({
  houses,
  ascendantDegree,
  variant = 'editorial',
  onHouseClick,
}: Props) {
  const romanR = (WHEEL.middleR + WHEEL.innerR) / 2;
  const ordered = [...houses].sort((a, b) => a.number - b.number);
  const interactive = Boolean(onHouseClick);
  const isPoster = variant === 'zodiac-poster';

  return (
    <g data-part="house-ring">
      {ordered.map((house, i) => {
        const next = ordered[(i + 1) % 12];
        const cuspSvg = zodiacToSvgAngle(house.cuspDegree, ascendantDegree);
        const p1 = polar(0, 0, WHEEL.innerR, cuspSvg);
        const p2 = polar(0, 0, WHEEL.middleR, cuspSvg);

        const midAbs = midpointCCW(house.cuspDegree, next.cuspDegree);
        const midSvg = zodiacToSvgAngle(midAbs, ascendantDegree);
        const romanPos = polar(0, 0, romanR, midSvg);

        const isAxis =
          house.number === 1 || house.number === 7 ||
          house.number === 4 || house.number === 10;

        const onClick = onHouseClick ? () => onHouseClick(house.number) : undefined;
        const onKeyDown = onHouseClick
          ? (e: React.KeyboardEvent) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onHouseClick(house.number);
              }
            }
          : undefined;

        const ariaLabel = `Дом ${house.number} в знаке ${ZODIAC_LABEL[house.sign]}`;
        const hitPath = sectorPath(
          WHEEL.innerR,
          WHEEL.middleR,
          house.cuspDegree,
          next.cuspDegree,
          ascendantDegree,
        );

        return (
          <g
            key={`house-${house.number}`}
            data-house={house.number}
            className={clsx(interactive && styles.interactive)}
            tabIndex={interactive ? 0 : undefined}
            role={interactive ? 'button' : undefined}
            aria-label={interactive ? ariaLabel : undefined}
            onClick={onClick}
            onKeyDown={onKeyDown}
          >
            {interactive && <title>{ariaLabel}</title>}

            {/* invisible hit target over the whole house wedge */}
            {interactive && (
              <path d={hitPath} fill="transparent" />
            )}

            <line
              x1={p1.x}
              y1={p1.y}
              x2={p2.x}
              y2={p2.y}
              stroke="var(--natal-primary)"
              strokeWidth={isAxis ? 1.5 : 0.9}
              opacity={isAxis ? 0.84 : isPoster ? 0.42 : 0.55}
            />

            <text
              x={romanPos.x}
              y={romanPos.y}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={isPoster ? 13 : ROMAN_FONT_SIZE}
              fill="var(--natal-primary)"
              className={styles.bodyText}
              opacity={isPoster ? 0.58 : 0.85}
            >
              {ROMAN[house.number - 1]}
            </text>
          </g>
        );
      })}
    </g>
  );
}
