import { ZODIAC_GLYPH, ZODIAC_ORDER, WHEEL } from '../constants';
import { polar, sectorPath, zodiacToSvgAngle } from '../utils/geometry';
import styles from '../NatalChart.module.css';

interface Props {
  ascendantDegree: number;
}

const GLYPH_FONT_SIZE = 33;

export function ZodiacRing({ ascendantDegree }: Props) {
  const glyphR = (WHEEL.outerR + WHEEL.middleR) / 2;

  return (
    <g data-part="zodiac-ring">
      {/* alternating subtle fills — every other sector */}
      {ZODIAC_ORDER.map((sign, i) => {
        if (i % 2 !== 0) return null;
        const d = sectorPath(
          WHEEL.middleR,
          WHEEL.outerR,
          i * 30,
          (i + 1) * 30,
          ascendantDegree,
        );
        return (
          <path
            key={`fill-${sign}`}
            d={d}
            fill="var(--natal-secondary)"
            opacity={0.13}
          />
        );
      })}

      {/* 12 radial dividers at sign boundaries */}
      {ZODIAC_ORDER.map((sign, i) => {
        const svgAng = zodiacToSvgAngle(i * 30, ascendantDegree);
        const p1 = polar(0, 0, WHEEL.middleR, svgAng);
        const p2 = polar(0, 0, WHEEL.outerR, svgAng);
        return (
          <line
            key={`div-${sign}`}
            x1={p1.x}
            y1={p1.y}
            x2={p2.x}
            y2={p2.y}
            stroke="var(--natal-primary)"
            strokeWidth={1.3}
            opacity={0.7}
          />
        );
      })}

      {/* glyphs — upright, centered in each sector */}
      {ZODIAC_ORDER.map((sign, i) => {
        const midSvgAng = zodiacToSvgAngle(i * 30 + 15, ascendantDegree);
        const pos = polar(0, 0, glyphR, midSvgAng);
        return (
          <text
            key={`glyph-${sign}`}
            x={pos.x}
            y={pos.y}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={GLYPH_FONT_SIZE}
            fill="var(--natal-primary)"
            className={styles.glyphText}
          >
            {ZODIAC_GLYPH[sign]}
          </text>
        );
      })}
    </g>
  );
}
