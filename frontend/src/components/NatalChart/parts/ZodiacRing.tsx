import type { ChartVariant } from '../types';
import { ZODIAC_EN_LABEL, ZODIAC_GLYPH, ZODIAC_ORDER, WHEEL } from '../constants';
import { polar, sectorPath, zodiacToSvgAngle } from '../utils/geometry';
import styles from '../NatalChart.module.css';

interface Props {
  ascendantDegree: number;
  variant?: ChartVariant;
}

const GLYPH_FONT_SIZE = 33;

function readableTangentRotation(svgAng: number): number {
  const raw = svgAng + 90;
  const normalized = ((raw % 360) + 360) % 360;
  return normalized > 90 && normalized < 270 ? raw + 180 : raw;
}

export function ZodiacRing({ ascendantDegree, variant = 'editorial' }: Props) {
  const isPoster = variant === 'zodiac-poster';
  const glyphR = isPoster ? WHEEL.outerR - 68 : (WHEEL.outerR + WHEEL.middleR) / 2;
  const labelR = WHEEL.outerR + 44;
  const dividerOuterR = isPoster ? WHEEL.outerR + 58 : WHEEL.outerR;

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
        const p2 = polar(0, 0, dividerOuterR, svgAng);
        return (
          <line
            key={`div-${sign}`}
            x1={p1.x}
            y1={p1.y}
            x2={p2.x}
            y2={p2.y}
            stroke="var(--natal-primary)"
            strokeWidth={isPoster ? 1.1 : 1.3}
            opacity={isPoster ? 0.72 : 0.7}
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
            fontSize={isPoster ? 58 : GLYPH_FONT_SIZE}
            fill={isPoster ? 'var(--natal-accent)' : 'var(--natal-primary)'}
            className={isPoster ? styles.posterGlyphText : styles.glyphText}
          >
            {ZODIAC_GLYPH[sign]}
          </text>
        );
      })}

      {isPoster &&
        ZODIAC_ORDER.map((sign, i) => {
          const midSvgAng = zodiacToSvgAngle(i * 30 + 15, ascendantDegree);
          const pos = polar(0, 0, labelR, midSvgAng);
          const rot = readableTangentRotation(midSvgAng);

          return (
            <text
              key={`label-${sign}`}
              x={pos.x}
              y={pos.y}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={22}
              fill="var(--natal-accent)"
              className={styles.posterLabelText}
              transform={`rotate(${rot.toFixed(2)}, ${pos.x.toFixed(2)}, ${pos.y.toFixed(2)})`}
            >
              {ZODIAC_EN_LABEL[sign]}
            </text>
          );
        })}
    </g>
  );
}
