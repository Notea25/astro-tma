const STARS = [
  [58, 84, 1.2, 0.5], [122, 190, 2.6, 0.5], [78, 334, 1.4, 0.42],
  [154, 650, 3.2, 0.44], [96, 760, 1.6, 0.5], [246, 92, 1.1, 0.44],
  [324, 146, 1.8, 0.38], [382, 72, 1.2, 0.5], [472, 118, 1.6, 0.42],
  [570, 72, 1.2, 0.42], [642, 126, 2.2, 0.42], [746, 86, 1.4, 0.48],
  [884, 150, 2.8, 0.36], [930, 280, 1.5, 0.42], [846, 392, 1.1, 0.46],
  [920, 584, 1.8, 0.4], [858, 730, 3.2, 0.36], [760, 832, 1.4, 0.44],
  [614, 910, 2.2, 0.38], [492, 866, 1.3, 0.42], [312, 898, 1.6, 0.4],
  [224, 818, 2.2, 0.36],
];

const CONSTELLATIONS = [
  [[82, 216], [126, 248], [168, 232], [206, 278], [246, 260]],
  [[744, 106], [796, 78], [846, 104], [884, 150], [914, 126]],
  [[112, 820], [156, 788], [206, 802], [248, 762]],
  [[768, 830], [812, 784], [858, 808], [902, 758]],
];

export function PosterBackdrop() {
  return (
    <g data-part="poster-backdrop">
      <defs>
        <pattern id="natalPosterGridMinor" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M 20 0 L 0 0 0 20" fill="none" stroke="var(--natal-grid)" strokeWidth={1} />
        </pattern>
        <pattern id="natalPosterGridMajor" width="100" height="100" patternUnits="userSpaceOnUse">
          <path d="M 100 0 L 0 0 0 100" fill="none" stroke="var(--natal-grid)" strokeWidth={1.3} />
        </pattern>
        <radialGradient id="natalPosterVignette" cx="50%" cy="45%" r="68%">
          <stop offset="0%" stopColor="rgba(255, 135, 73, 0.08)" />
          <stop offset="56%" stopColor="rgba(255, 135, 73, 0.015)" />
          <stop offset="100%" stopColor="rgba(0, 0, 0, 0.48)" />
        </radialGradient>
      </defs>

      <rect width={1000} height={1000} fill="var(--natal-bg)" />
      <rect width={1000} height={1000} fill="url(#natalPosterGridMinor)" opacity={0.62} />
      <rect width={1000} height={1000} fill="url(#natalPosterGridMajor)" opacity={0.36} />
      <rect width={1000} height={1000} fill="url(#natalPosterVignette)" />

      <circle cx={120} cy={-28} r={72} fill="none" stroke="var(--natal-dim)" strokeWidth={2} opacity={0.52} />
      <circle cx={880} cy={-28} r={72} fill="none" stroke="var(--natal-dim)" strokeWidth={2} opacity={0.52} />

      {STARS.map(([cx, cy, r, opacity], index) => (
        <circle
          key={`star-${index}`}
          cx={cx}
          cy={cy}
          r={r}
          fill="var(--natal-accent)"
          opacity={opacity}
        />
      ))}

      {CONSTELLATIONS.map((points, index) => (
        <g key={`constellation-${index}`} opacity={0.42}>
          <polyline
            points={points.map(([x, y]) => `${x},${y}`).join(' ')}
            fill="none"
            stroke="var(--natal-accent)"
            strokeWidth={1.1}
          />
          {points.map(([cx, cy], pointIndex) => (
            <circle
              key={`${index}-${pointIndex}`}
              cx={cx}
              cy={cy}
              r={2.8}
              fill="var(--natal-accent)"
            />
          ))}
        </g>
      ))}
    </g>
  );
}
