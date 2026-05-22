import type { ZodiacSign } from '@/components/NatalChart/types';

// Hand-crafted SVG paths for each zodiac sign. ViewBox 0 0 24 24, centred on
// 12,12. Designed to be drawn as outline (stroke="currentColor", no fill).
// Stored here as plain strings so they can also be reused inside any other
// inline <svg> (e.g. the natal chart wheel) by emitting <path d={...}/>.
export const ZODIAC_PATH: Record<ZodiacSign, string> = {
  aries:       'M 12 19 C 6 19 5 5 10 5 M 12 19 C 18 19 19 5 14 5',
  taurus:      'M 8 17 a 4 4 0 1 0 8 0 a 4 4 0 1 0 -8 0 M 5 8 Q 8 4 12 8 Q 16 4 19 8',
  gemini:      'M 7 5 L 7 19 M 13 5 L 13 19 M 5 5 L 15 5 M 5 19 L 15 19',
  cancer:      'M 5 8 a 2 2 0 1 0 4 0 a 2 2 0 1 0 -4 0 M 9 8 Q 17 8 16 14 M 13 16 a 2 2 0 1 0 4 0 a 2 2 0 1 0 -4 0 M 13 16 Q 5 16 6 10',
  leo:         'M 6 9 a 3 3 0 1 0 6 0 a 3 3 0 1 0 -6 0 M 11 11 Q 16 13 17 18 Q 17 21 14 20',
  virgo:       'M 4 18 L 4 7 L 8 18 L 8 7 L 12 18 L 12 7 L 16 18 Q 19 18 19 14 Q 19 11 16 13 Q 17 17 19 18',
  libra:       'M 5 11 Q 12 5 19 11 M 4 17 L 20 17 M 9 17 Q 12 13 15 17',
  scorpio:     'M 4 18 L 4 7 L 8 18 L 8 7 L 12 18 L 12 7 L 16 18 L 20 14 M 18 14 L 20 14 L 20 16',
  sagittarius: 'M 5 19 L 19 5 M 13 5 L 19 5 L 19 11 M 9 11 L 13 15',
  capricorn:   'M 4 7 L 9 19 L 14 7 Q 17 7 17 12 Q 17 17 13 17 Q 11 17 12 14',
  aquarius:    'M 3 10 Q 6 7 9 10 Q 12 13 15 10 Q 18 7 21 10 M 3 15 Q 6 12 9 15 Q 12 18 15 15 Q 18 12 21 15',
  pisces:      'M 5 5 Q 9 12 5 19 M 19 5 Q 15 12 19 19 M 5 12 L 19 12',
};

const ZODIAC_LABEL_RU: Record<ZodiacSign, string> = {
  aries: 'Овен', taurus: 'Телец', gemini: 'Близнецы', cancer: 'Рак',
  leo: 'Лев', virgo: 'Дева', libra: 'Весы', scorpio: 'Скорпион',
  sagittarius: 'Стрелец', capricorn: 'Козерог',
  aquarius: 'Водолей', pisces: 'Рыбы',
};

interface ZodiacIconProps {
  sign: ZodiacSign;
  size?: number;
  color?: string;
  strokeWidth?: number;
  className?: string;
  style?: React.CSSProperties;
}

export function ZodiacIcon({
  sign,
  size = 24,
  color,
  strokeWidth = 1.6,
  className,
  style,
}: ZodiacIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color ?? 'currentColor'}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={style}
      aria-label={ZODIAC_LABEL_RU[sign]}
    >
      <title>{ZODIAC_LABEL_RU[sign]}</title>
      <path d={ZODIAC_PATH[sign]} />
    </svg>
  );
}
