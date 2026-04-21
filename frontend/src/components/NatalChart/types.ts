export type PlanetName =
  | 'sun' | 'moon' | 'mercury' | 'venus' | 'mars'
  | 'jupiter' | 'saturn' | 'uranus' | 'neptune' | 'pluto'
  | 'northNode' | 'chiron';

export type ZodiacSign =
  | 'aries' | 'taurus' | 'gemini' | 'cancer' | 'leo' | 'virgo'
  | 'libra' | 'scorpio' | 'sagittarius' | 'capricorn' | 'aquarius' | 'pisces';

export type Element = 'fire' | 'earth' | 'air' | 'water';

export type AspectType = 'conjunction' | 'opposition' | 'trine' | 'square' | 'sextile';

export type ThemeName = 'midnight-gold' | 'purple-silver' | 'forest-gold';

export interface PlanetPosition {
  sign: ZodiacSign;
  degree: number;   // 0–29
  minute: number;   // 0–59
  house: number;    // 1–12
  retrograde?: boolean;
}

export interface HousePosition {
  number: number;       // 1–12
  cuspDegree: number;   // absolute 0–359
  sign: ZodiacSign;
}

export interface Aspect {
  planet1: PlanetName;
  planet2: PlanetName;
  type: AspectType;
  orb: number;
}

export interface BirthLocation {
  city: string;
  country: string;
  latitude: number;
  longitude: number;
  timezone: string;
}

export interface NatalChartData {
  name?: string;
  birthDate: string;   // ISO "YYYY-MM-DD"
  birthTime: string;   // "HH:MM"
  birthLocation: BirthLocation;
  sun: PlanetPosition;
  ascendant: PlanetPosition;
  midheaven: PlanetPosition;
  planets: Record<PlanetName, PlanetPosition>;
  houses: HousePosition[];
  aspects: Aspect[];
}

export interface NatalChartProps {
  data: NatalChartData;
  theme?: ThemeName;
  size?: number;
  title?: string;
  showDecorative?: boolean;
  showSideFigures?: boolean;
  className?: string;
  onPlanetClick?: (planet: PlanetName) => void;
  onHouseClick?: (house: number) => void;
}
