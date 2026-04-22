import type { NatalChartData } from './types';

export const sampleData: NatalChartData = {
  name: 'Anton',
  birthDate: '1982-08-28',
  birthTime: '20:30',
  birthLocation: {
    city: 'Warsaw',
    country: 'Poland',
    latitude: 52.2297,
    longitude: 21.0122,
    timezone: 'Europe/Warsaw',
  },
  // Sun in Virgo 6°25' (house 6)
  sun: { sign: 'virgo', degree: 6, minute: 25, house: 6 },
  // Ascendant (Rising) in Pisces 6°25' (house 1)
  ascendant: { sign: 'pisces', degree: 6, minute: 25, house: 1 },
  midheaven: { sign: 'sagittarius', degree: 18, minute: 12, house: 10 },
  planets: {
    sun:       { sign: 'virgo',       degree: 6,  minute: 25, house: 6 },
    moon:      { sign: 'cancer',      degree: 14, minute: 40, house: 5 },
    mercury:   { sign: 'virgo',       degree: 22, minute: 10, house: 7 },
    venus:     { sign: 'libra',       degree: 3,  minute: 55, house: 7 },
    mars:      { sign: 'scorpio',     degree: 11, minute: 20, house: 8 },
    jupiter:   { sign: 'scorpio',     degree: 2,  minute: 44, house: 8, retrograde: true },
    saturn:    { sign: 'libra',       degree: 19, minute: 30, house: 8 },
    uranus:    { sign: 'sagittarius', degree: 1,  minute: 10, house: 9, retrograde: true },
    neptune:   { sign: 'sagittarius', degree: 24, minute: 52, house: 10, retrograde: true },
    pluto:     { sign: 'libra',       degree: 24, minute: 17, house: 8 },
    northNode: { sign: 'cancer',      degree: 17, minute: 5,  house: 5 },
    chiron:    { sign: 'taurus',      degree: 27, minute: 48, house: 3, retrograde: true },
  },
  // Whole-sign-ish houses for a Pisces ascendant — cuspDegree absolute (0 = 0° Aries)
  houses: [
    { number: 1,  cuspDegree: 336, sign: 'pisces' },      // 6° Pisces
    { number: 2,  cuspDegree: 6,   sign: 'aries' },
    { number: 3,  cuspDegree: 36,  sign: 'taurus' },
    { number: 4,  cuspDegree: 66,  sign: 'gemini' },
    { number: 5,  cuspDegree: 96,  sign: 'cancer' },
    { number: 6,  cuspDegree: 126, sign: 'leo' },
    { number: 7,  cuspDegree: 156, sign: 'virgo' },
    { number: 8,  cuspDegree: 186, sign: 'libra' },
    { number: 9,  cuspDegree: 216, sign: 'scorpio' },
    { number: 10, cuspDegree: 246, sign: 'sagittarius' },
    { number: 11, cuspDegree: 276, sign: 'capricorn' },
    { number: 12, cuspDegree: 306, sign: 'aquarius' },
  ],
  aspects: [
    { planet1: 'sun',     planet2: 'jupiter', type: 'opposition',  orb: 3.7 },
    { planet1: 'sun',     planet2: 'saturn',  type: 'square',      orb: 2.1 },
    { planet1: 'moon',    planet2: 'venus',   type: 'trine',       orb: 1.4 },
    { planet1: 'moon',    planet2: 'mars',    type: 'opposition',  orb: 2.8 },
    { planet1: 'mercury', planet2: 'saturn',  type: 'trine',       orb: 2.7 },
    { planet1: 'venus',   planet2: 'mars',    type: 'sextile',     orb: 1.2 },
    { planet1: 'mars',    planet2: 'neptune', type: 'trine',       orb: 2.4 },
    { planet1: 'jupiter', planet2: 'pluto',   type: 'sextile',     orb: 1.6 },
    { planet1: 'saturn',  planet2: 'uranus',  type: 'square',      orb: 3.0 },
  ],
};
