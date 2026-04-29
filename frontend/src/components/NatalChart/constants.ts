import type { Element, PlanetName, ZodiacSign } from './types';

export const ZODIAC_ORDER: ZodiacSign[] = [
  'aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo',
  'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces',
];

// U+FE0E (text presentation selector) prevents browsers from rendering these
// code points as color emoji — we want monochrome line-art glyphs.
const TEXT = '︎';

export const ZODIAC_GLYPH: Record<ZodiacSign, string> = {
  aries:       '♈' + TEXT,
  taurus:      '♉' + TEXT,
  gemini:      '♊' + TEXT,
  cancer:      '♋' + TEXT,
  leo:         '♌' + TEXT,
  virgo:       '♍' + TEXT,
  libra:       '♎' + TEXT,
  scorpio:     '♏' + TEXT,
  sagittarius: '♐' + TEXT,
  capricorn:   '♑' + TEXT,
  aquarius:    '♒' + TEXT,
  pisces:      '♓' + TEXT,
};

export const ZODIAC_ELEMENT: Record<ZodiacSign, Element> = {
  aries: 'fire', leo: 'fire', sagittarius: 'fire',
  taurus: 'earth', virgo: 'earth', capricorn: 'earth',
  gemini: 'air', libra: 'air', aquarius: 'air',
  cancer: 'water', scorpio: 'water', pisces: 'water',
};

export const ZODIAC_LABEL: Record<ZodiacSign, string> = {
  aries: 'Овен', taurus: 'Телец', gemini: 'Близнецы', cancer: 'Рак',
  leo: 'Лев', virgo: 'Дева', libra: 'Весы', scorpio: 'Скорпион',
  sagittarius: 'Стрелец', capricorn: 'Козерог',
  aquarius: 'Водолей', pisces: 'Рыбы',
};

export const ELEMENT_LABEL: Record<Element, string> = {
  fire: 'ОГОНЬ',
  earth: 'ЗЕМЛЯ',
  air: 'ВОЗДУХ',
  water: 'ВОДА',
};

export const PLANET_GLYPH: Record<PlanetName, string> = {
  sun:       '☉' + TEXT,
  moon:      '☽' + TEXT,
  mercury:   '☿' + TEXT,
  venus:     '♀' + TEXT,
  mars:      '♂' + TEXT,
  jupiter:   '♃' + TEXT,
  saturn:    '♄' + TEXT,
  uranus:    '♅' + TEXT,
  neptune:   '♆' + TEXT,
  pluto:     '♇' + TEXT,
  northNode: '☊' + TEXT,
  chiron:    '⚷' + TEXT,
};

export const PLANET_LABEL: Record<PlanetName, string> = {
  sun: 'Солнце', moon: 'Луна', mercury: 'Меркурий', venus: 'Венера',
  mars: 'Марс', jupiter: 'Юпитер', saturn: 'Сатурн', uranus: 'Уран',
  neptune: 'Нептун', pluto: 'Плутон',
  northNode: 'Северный узел', chiron: 'Хирон',
};

export const PLANET_DRAW_ORDER: PlanetName[] = [
  'sun', 'moon', 'mercury', 'venus', 'mars',
  'jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
  'northNode', 'chiron',
];

export const ROMAN: readonly string[] = [
  'I', 'II', 'III', 'IV', 'V', 'VI',
  'VII', 'VIII', 'IX', 'X', 'XI', 'XII',
];

export const RETROGRADE_MARK = '℞'; // ℞

/**
 * Chart-wheel layout. All dimensions are in SVG user units of the 1000×1400
 * viewBox. Kept together so the whole composition can be retuned in one place.
 */
export const WHEEL = {
  cx: 500,
  cy: 820,
  outerR: 340,    // zodiac ring outer edge
  middleR: 280,   // zodiac/house boundary
  innerR: 210,    // house/planet boundary
  planetR: 175,   // nominal radius for planet glyphs
} as const;
