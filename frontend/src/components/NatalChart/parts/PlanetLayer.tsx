import clsx from 'clsx';
import type { PlacedPlanet } from '../utils/planetLayout';
import type { PlanetName } from '../types';
import { PLANET_GLYPH, PLANET_LABEL, RETROGRADE_MARK, ZODIAC_LABEL } from '../constants';
import { polar, zodiacToSvgAngle } from '../utils/geometry';
import { formatDegreeMinute } from '../utils/formatting';
import styles from '../NatalChart.module.css';

interface Props {
  placed: PlacedPlanet[];
  ascendantDegree: number;
  onPlanetClick?: (planet: PlanetName) => void;
}

const GLYPH_FONT_SIZE = 27;

export function PlanetLayer({ placed, ascendantDegree, onPlanetClick }: Props) {
  return (
    <g data-part="planet-layer">
      {placed.map(({ name, position, absDeg, radius }) => {
        const svgAng = zodiacToSvgAngle(absDeg, ascendantDegree);
        const pos = polar(0, 0, radius, svgAng);

        const interactive = Boolean(onPlanetClick);
        const handleClick = onPlanetClick ? () => onPlanetClick(name) : undefined;
        const handleKey = onPlanetClick
          ? (e: React.KeyboardEvent) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onPlanetClick(name);
              }
            }
          : undefined;

        const retroSuffix = position.retrograde ? ' ' + RETROGRADE_MARK : '';
        const srDescription =
          `${PLANET_LABEL[name]} ${formatDegreeMinute(position)} в знаке ${ZODIAC_LABEL[position.sign]}` +
          (position.retrograde ? ' (ретроградная)' : '') +
          `, дом ${position.house}`;

        return (
          <g
            key={name}
            data-planet={name}
            className={clsx(interactive && styles.interactive)}
            tabIndex={interactive ? 0 : undefined}
            onClick={handleClick}
            onKeyDown={handleKey}
            role={interactive ? 'button' : undefined}
            aria-label={interactive ? srDescription : undefined}
          >
            <title>{srDescription}</title>
            <text
              x={pos.x}
              y={pos.y}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={GLYPH_FONT_SIZE}
              fill="var(--natal-primary)"
              className={styles.glyphText}
            >
              {PLANET_GLYPH[name]}{retroSuffix}
            </text>
          </g>
        );
      })}
    </g>
  );
}
