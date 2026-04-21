import type { Element, PlanetPosition, ZodiacSign } from '../types';
import {
  ELEMENT_LABEL,
  PLANET_GLYPH,
  ZODIAC_ELEMENT,
  ZODIAC_GLYPH,
  ZODIAC_LABEL,
} from '../constants';
import { formatDegreeMinute } from '../utils/formatting';
import styles from '../NatalChart.module.css';

interface Props {
  sun: PlanetPosition;
  ascendant: PlanetPosition;
}

/** Classical alchemical element triangle. */
function ElementMark({ element, size = 22 }: { element: Element; size?: number }) {
  const h = size * 0.866;
  const half = size / 2;
  const pointsUp = `0,${-h / 2} ${half},${h / 2} ${-half},${h / 2}`;
  const pointsDown = `0,${h / 2} ${half},${-h / 2} ${-half},${-h / 2}`;
  const tri = element === 'fire' || element === 'air' ? pointsUp : pointsDown;
  const hasBar = element === 'air' || element === 'earth';
  return (
    <g data-element={element}>
      <polygon
        points={tri}
        fill="none"
        stroke="var(--natal-primary)"
        strokeWidth={1.2}
      />
      {hasBar && (
        <line
          x1={-size * 0.3}
          y1={0}
          x2={size * 0.3}
          y2={0}
          stroke="var(--natal-primary)"
          strokeWidth={1.2}
        />
      )}
    </g>
  );
}

interface CornerProps {
  x: number;
  y: number;
  align: 'start' | 'end';
  mark: React.ReactNode;          // top row (glyph or element triangle)
  label: string;                  // middle row (e.g. "SUN" / "EARTH")
  value: string;                  // bottom row (e.g. "6°25' ♍" / "VIRGO")
}

function Corner({ x, y, align, mark, label, value }: CornerProps) {
  const anchor: 'start' | 'end' = align;
  // translate the mark so it sits at the same horizontal baseline as text
  const markDx = align === 'start' ? 14 : -14;
  return (
    <g data-part="corner" transform={`translate(${x} ${y})`}>
      <g transform={`translate(${markDx} 0)`}>{mark}</g>
      <text
        x={align === 'start' ? 36 : -36}
        y={-4}
        textAnchor={anchor}
        className={styles.bodyText}
        fontSize={11}
        opacity={0.75}
      >
        {label}
      </text>
      <text
        x={align === 'start' ? 36 : -36}
        y={14}
        textAnchor={anchor}
        className={styles.bodyText}
        fontSize={13}
        fill="var(--natal-primary)"
      >
        {value}
      </text>
    </g>
  );
}

export function CornerMetadata({ sun, ascendant }: Props) {
  const sunElement = ZODIAC_ELEMENT[sun.sign as ZodiacSign];
  const risingElement = ZODIAC_ELEMENT[ascendant.sign as ZodiacSign];

  const sunValue = `${formatDegreeMinute(sun)} ${ZODIAC_GLYPH[sun.sign]}`;
  const acValue = `${formatDegreeMinute(ascendant)} ${ZODIAC_GLYPH[ascendant.sign]}`;

  const glyph = (ch: string, size = 22) => (
    <text
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={size}
      fill="var(--natal-accent)"
      className={styles.glyphText}
    >
      {ch}
    </text>
  );

  return (
    <g data-part="corner-metadata">
      {/* top-left: Sun */}
      <Corner
        x={70}
        y={80}
        align="start"
        mark={glyph(PLANET_GLYPH.sun)}
        label="SUN"
        value={sunValue}
      />
      {/* top-right: Rising / Ascendant */}
      <Corner
        x={930}
        y={80}
        align="end"
        mark={
          <text
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={16}
            fill="var(--natal-accent)"
            className={styles.bodyText}
            letterSpacing="0.1em"
          >
            AC
          </text>
        }
        label="RISING"
        value={acValue}
      />
      {/* bottom-left: Sun element */}
      <Corner
        x={70}
        y={1320}
        align="start"
        mark={<ElementMark element={sunElement} />}
        label={ELEMENT_LABEL[sunElement]}
        value={ZODIAC_LABEL[sun.sign].toUpperCase()}
      />
      {/* bottom-right: Rising element */}
      <Corner
        x={930}
        y={1320}
        align="end"
        mark={<ElementMark element={risingElement} />}
        label={ELEMENT_LABEL[risingElement]}
        value={ZODIAC_LABEL[ascendant.sign].toUpperCase()}
      />
    </g>
  );
}
