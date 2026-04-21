import type { BirthLocation } from '../types';
import { formatBirthDate } from '../utils/formatting';
import styles from '../NatalChart.module.css';

interface Props {
  title: string;
  birthDate: string;
  birthTime: string;
  birthLocation: BirthLocation;
}

export function Header({ title, birthDate, birthTime, birthLocation }: Props) {
  const date = formatBirthDate(birthDate);
  const locationLine = `${birthTime} · ${birthLocation.city}, ${birthLocation.country}`;

  // wide letter-spacing ("tracked out") for Art Deco feel — applied via CSS class
  return (
    <g data-part="header">
      <text
        x={500}
        y={210}
        textAnchor="middle"
        className={styles.titleText}
        fontSize={42}
      >
        {title}
      </text>

      {/* hairline divider under the title */}
      <line
        x1={445}
        x2={555}
        y1={235}
        y2={235}
        stroke="var(--natal-accent)"
        strokeWidth={1}
        opacity={0.6}
      />

      <text
        x={500}
        y={265}
        textAnchor="middle"
        className={styles.subtitleText}
        fontSize={20}
      >
        {date}
      </text>

      <text
        x={500}
        y={295}
        textAnchor="middle"
        className={styles.bodyText}
        fontSize={12}
        opacity={0.8}
      >
        {locationLine}
      </text>
    </g>
  );
}
