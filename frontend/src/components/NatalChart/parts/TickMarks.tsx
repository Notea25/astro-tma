import type { ChartVariant } from '../types';
import { WHEEL } from '../constants';
import { polar, zodiacToSvgAngle } from '../utils/geometry';

interface Props {
  ascendantDegree: number;
  variant?: ChartVariant;
}

const TICK_STEP = 5;
const MINOR_LEN = 4;
const MAJOR_LEN = 9;

/** Tick marks sitting just outside the zodiac (outer) ring — every 5°, with
 *  longer ticks on sign boundaries. */
export function TickMarks({ ascendantDegree, variant = 'editorial' }: Props) {
  const ticks: React.ReactElement[] = [];
  const isPoster = variant === 'zodiac-poster';
  const outerR = isPoster ? WHEEL.outerR + 52 : WHEEL.outerR;
  for (let d = 0; d < 360; d += TICK_STEP) {
    const isMajor = d % 30 === 0;
    const svgAng = zodiacToSvgAngle(d, ascendantDegree);
    const p1 = polar(0, 0, outerR, svgAng);
    const p2 = polar(0, 0, outerR + (isMajor ? MAJOR_LEN : MINOR_LEN), svgAng);
    ticks.push(
      <line
        key={d}
        x1={p1.x}
        y1={p1.y}
        x2={p2.x}
        y2={p2.y}
        stroke="var(--natal-dim)"
        strokeWidth={isMajor ? 1.1 : 0.7}
        opacity={isPoster ? 0.82 : 1}
      />,
    );
  }
  return <g data-part="tick-marks">{ticks}</g>;
}
