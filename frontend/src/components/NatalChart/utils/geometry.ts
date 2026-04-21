import type { PlanetPosition } from '../types';
import { ZODIAC_ORDER } from '../constants';

export interface Point {
  x: number;
  y: number;
}

export function toRadians(deg: number): number {
  return (deg * Math.PI) / 180;
}

export function polar(cx: number, cy: number, r: number, angleDeg: number): Point {
  const a = toRadians(angleDeg);
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}

/**
 * Absolute ecliptic degree (0 = 0° Aries) → SVG angle in degrees, rotated so
 * the ascendant sits at the 9 o'clock (west) position.
 *
 * SVG's default y-down coordinate means angles increase clockwise, while the
 * zodiac advances counter-clockwise from the ascendant on an astrology chart.
 * This helper does the rotation and the handedness flip in one place so
 * nothing else has to think about it.
 */
export function zodiacToSvgAngle(absDegree: number, ascendantDegree: number): number {
  return 180 - (absDegree - ascendantDegree);
}

/** Convert a sign/degree/minute position into absolute ecliptic degrees. */
export function positionToAbsoluteDegree(p: PlanetPosition): number {
  const signIndex = ZODIAC_ORDER.indexOf(p.sign);
  return ((signIndex * 30 + p.degree + p.minute / 60) % 360 + 360) % 360;
}

/**
 * SVG path for a donut slice between two radii over an absolute-degree range.
 * The slice is drawn with the zodiac's CCW handedness built in.
 */
export function sectorPath(
  innerR: number,
  outerR: number,
  startAbsDeg: number,
  endAbsDeg: number,
  ascendantDegree: number,
): string {
  const a1 = zodiacToSvgAngle(startAbsDeg, ascendantDegree);
  const a2 = zodiacToSvgAngle(endAbsDeg, ascendantDegree);
  const outer1 = polar(0, 0, outerR, a1);
  const outer2 = polar(0, 0, outerR, a2);
  const inner2 = polar(0, 0, innerR, a2);
  const inner1 = polar(0, 0, innerR, a1);
  // |a1 - a2| is always < 360 for our use (sector ≤ 180°), so:
  const sweep = ((a1 - a2) % 360 + 360) % 360;
  const largeArc = sweep > 180 ? 1 : 0;
  return (
    `M ${outer1.x} ${outer1.y} ` +
    `A ${outerR} ${outerR} 0 ${largeArc} 0 ${outer2.x} ${outer2.y} ` +
    `L ${inner2.x} ${inner2.y} ` +
    `A ${innerR} ${innerR} 0 ${largeArc} 1 ${inner1.x} ${inner1.y} Z`
  );
}
