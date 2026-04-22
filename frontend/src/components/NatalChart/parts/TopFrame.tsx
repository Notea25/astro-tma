/** Thin outward-facing crescent. `facing` = the side its opening faces. */
function Crescent({
  cx, cy, r, facing,
}: { cx: number; cy: number; r: number; facing: 'left' | 'right' }) {
  const innerRx = r * 0.55;
  const innerRy = r;
  // In SVG y-down: CCW from top → via left-extreme → bottom = sweep-flag 0.
  // Inner arc: from bottom back to top through the inside of the crescent.
  // For a right-facing crescent (opens right): both arcs on the left half → sweep 0.
  const sweep = facing === 'right' ? 0 : 1;
  const top = `${cx} ${cy - r}`;
  const bot = `${cx} ${cy + r}`;
  return (
    <path
      d={`M ${top} A ${r} ${r} 0 0 ${sweep} ${bot} A ${innerRx} ${innerRy} 0 0 ${sweep} ${top} Z`}
      fill="none"
      stroke="var(--natal-primary)"
      strokeWidth={1}
    />
  );
}

/** Eight-pointed "sparkle" star used in the celestial motif. Long cardinal
 *  rays, short diagonal rays. */
function FourPointStar({ cx, cy, size }: { cx: number; cy: number; size: number }) {
  const outerR = size;
  const innerR = size * 0.28;
  const points: string[] = [];
  for (let i = 0; i < 8; i++) {
    const ang = (i * 45 - 90) * (Math.PI / 180);
    const r = i % 2 === 0 ? outerR : innerR;
    points.push(`${cx + r * Math.cos(ang)},${cy + r * Math.sin(ang)}`);
  }
  return (
    <polygon
      points={points.join(' ')}
      fill="none"
      stroke="var(--natal-accent)"
      strokeWidth={1}
    />
  );
}

/** Zone 1 — shallow symmetric arches + crescent · star · crescent motif. */
export function TopFrame() {
  const motifY = 60;
  return (
    <g data-part="top-frame">
      {/* left and right shallow arches meeting near the top-center */}
      <path
        d="M 100 130 Q 300 40 500 95"
        fill="none"
        stroke="var(--natal-primary)"
        strokeWidth={1}
        opacity={0.55}
      />
      <path
        d="M 900 130 Q 700 40 500 95"
        fill="none"
        stroke="var(--natal-primary)"
        strokeWidth={1}
        opacity={0.55}
      />

      {/* dotted accent curves parallel to the arches */}
      <path
        d="M 115 128 Q 305 60 495 108"
        fill="none"
        stroke="var(--natal-accent)"
        strokeWidth={1}
        strokeDasharray="1 4"
        opacity={0.7}
      />
      <path
        d="M 885 128 Q 695 60 505 108"
        fill="none"
        stroke="var(--natal-accent)"
        strokeWidth={1}
        strokeDasharray="1 4"
        opacity={0.7}
      />

      {/* celestial motif: small crescent · 4-point star · mirrored crescent */}
      <Crescent cx={435} cy={motifY} r={9} facing="right" />
      <FourPointStar cx={500} cy={motifY} size={14} />
      <Crescent cx={565} cy={motifY} r={9} facing="left" />
    </g>
  );
}
