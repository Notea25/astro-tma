import type { PlanetName, PlanetPosition } from '../types';
import { PLANET_DRAW_ORDER, WHEEL } from '../constants';
import { positionToAbsoluteDegree } from './geometry';

export interface PlacedPlanet {
  name: PlanetName;
  position: PlanetPosition;
  absDeg: number;
  /** Radius at which the glyph is drawn (after collision offset). */
  radius: number;
}

const COLLISION_GAP = 3.5;   // degrees within which we offset radially
const RADIAL_STEP = 26;      // px per stack level

/** Sort planets by absolute degree, then push stacked radii inward when
 *  successive planets fall within `COLLISION_GAP`. */
export function layOutPlanets(planets: Record<PlanetName, PlanetPosition>): PlacedPlanet[] {
  const placed: PlacedPlanet[] = PLANET_DRAW_ORDER.map((name) => ({
    name,
    position: planets[name],
    absDeg: positionToAbsoluteDegree(planets[name]),
    radius: WHEEL.planetR,
  }));

  placed.sort((a, b) => a.absDeg - b.absDeg);

  for (let i = 1; i < placed.length; i++) {
    const diff = placed[i].absDeg - placed[i - 1].absDeg;
    if (diff < COLLISION_GAP) {
      placed[i].radius = placed[i - 1].radius - RADIAL_STEP;
    }
  }

  return placed;
}
