import type { PlanetPosition } from '../types';
import { ZODIAC_GLYPH } from '../constants';

const MONTHS = [
  'JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE',
  'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER',
];

/** "1982-08-28" → "28 AUGUST 1982" */
export function formatBirthDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  const month = MONTHS[m - 1] ?? '';
  return `${String(d).padStart(2, '0')} ${month} ${y}`;
}

/** PlanetPosition → "6°25' ♍" */
export function formatPositionWithGlyph(p: PlanetPosition): string {
  return `${p.degree}°${String(p.minute).padStart(2, '0')}' ${ZODIAC_GLYPH[p.sign]}`;
}

/** PlanetPosition → "6°25'" (no sign) */
export function formatDegreeMinute(p: PlanetPosition): string {
  return `${p.degree}°${String(p.minute).padStart(2, '0')}'`;
}
