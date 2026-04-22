import type { NatalSummaryResponse } from '@/types'
import type {
  NatalChartData,
  PlanetName,
  PlanetPosition,
  ZodiacSign,
  AspectType,
} from './types'

const VALID_ASPECT_TYPES = new Set<string>([
  'conjunction', 'opposition', 'trine', 'square', 'sextile',
])

const VALID_PLANETS = new Set<string>([
  'sun', 'moon', 'mercury', 'venus', 'mars',
  'jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
  'northNode', 'chiron',
])

function toSignLower(s: string): ZodiacSign {
  return s.toLowerCase() as ZodiacSign
}

function fromSignDegree(signDegree: number): { degree: number; minute: number } {
  const d = Math.floor(signDegree)
  const m = Math.floor((signDegree - d) * 60)
  return { degree: d, minute: m }
}

function makePlanet(data: {
  sign: string
  sign_degree: number
  house: number
  retrograde: boolean
}): PlanetPosition {
  const { degree, minute } = fromSignDegree(data.sign_degree)
  return {
    sign: toSignLower(data.sign),
    degree,
    minute,
    house: data.house,
    retrograde: data.retrograde,
  }
}

const FALLBACK_PLANET: PlanetPosition = {
  sign: 'aries',
  degree: 0,
  minute: 0,
  house: 1,
  retrograde: false,
}

export function toNatalChartData(
  summary: NatalSummaryResponse,
): NatalChartData | null {
  if (!summary.has_chart || !summary.planets || !summary.houses) return null

  const planets = summary.planets
  const houses = summary.houses

  // Build planets record — northNode and chiron may not exist in backend data
  const planetsRecord = {} as Record<PlanetName, PlanetPosition>
  for (const name of VALID_PLANETS) {
    const raw = planets[name]
    planetsRecord[name as PlanetName] = raw ? makePlanet(raw) : FALLBACK_PLANET
  }

  // House 1 cusp = ascendant
  const h1 = houses.find(h => h.number === 1)
  const h10 = houses.find(h => h.number === 10)

  const ascSignDegree = h1 ? (h1.degree % 30 + 30) % 30 : 0
  const mcSignDegree = h10 ? (h10.degree % 30 + 30) % 30 : 0

  const ascendant: PlanetPosition = {
    sign: toSignLower(summary.ascendant_sign || h1?.sign || 'aries'),
    ...fromSignDegree(ascSignDegree),
    house: 1,
  }
  const midheaven: PlanetPosition = {
    sign: toSignLower(summary.mc_sign || h10?.sign || 'capricorn'),
    ...fromSignDegree(mcSignDegree),
    house: 10,
  }

  const mappedHouses = houses.map(h => ({
    number: h.number,
    cuspDegree: h.degree,
    sign: toSignLower(h.sign),
  }))

  const aspects = (summary.aspects ?? [])
    .filter(a => VALID_ASPECT_TYPES.has(a.aspect) && VALID_PLANETS.has(a.p1) && VALID_PLANETS.has(a.p2))
    .map(a => ({
      planet1: a.p1 as PlanetName,
      planet2: a.p2 as PlanetName,
      type: a.aspect as AspectType,
      orb: a.orb,
    }))

  return {
    name: undefined,
    birthDate: summary.birth_date ?? '2000-01-01',
    birthTime: summary.birth_time ?? '12:00',
    birthLocation: {
      city: summary.birth_city ?? '',
      country: '',
      latitude: summary.birth_lat ?? 0,
      longitude: summary.birth_lng ?? 0,
      timezone: summary.birth_tz ?? 'UTC',
    },
    sun: planetsRecord.sun,
    ascendant,
    midheaven,
    planets: planetsRecord,
    houses: mappedHouses,
    aspects,
  }
}
