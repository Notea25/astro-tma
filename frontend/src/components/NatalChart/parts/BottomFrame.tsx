function Crescent({
  cx, cy, r, facing,
}: { cx: number; cy: number; r: number; facing: 'left' | 'right' }) {
  const innerRx = r * 0.55;
  const innerRy = r;
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

/** Zone 6 — mirror of TopFrame flipped vertically around y = 1400. */
export function BottomFrame() {
  // Mirror the top-frame coordinates across y = 700 (viewBox mid-point isn't
  // relevant; what matters is that bottom-frame sits at symmetric distance
  // from the bottom as top-frame does from the top).
  const motifY = 1340;
  return (
    <g data-part="bottom-frame">
      {/* arches — bowing downward, mirror of top frame */}
      <path
        d="M 100 1270 Q 300 1360 500 1305"
        fill="none"
        stroke="var(--natal-primary)"
        strokeWidth={1}
        opacity={0.55}
      />
      <path
        d="M 900 1270 Q 700 1360 500 1305"
        fill="none"
        stroke="var(--natal-primary)"
        strokeWidth={1}
        opacity={0.55}
      />

      <path
        d="M 115 1272 Q 305 1340 495 1292"
        fill="none"
        stroke="var(--natal-accent)"
        strokeWidth={1}
        strokeDasharray="1 4"
        opacity={0.7}
      />
      <path
        d="M 885 1272 Q 695 1340 505 1292"
        fill="none"
        stroke="var(--natal-accent)"
        strokeWidth={1}
        strokeDasharray="1 4"
        opacity={0.7}
      />

      <Crescent cx={435} cy={motifY} r={9} facing="right" />
      <FourPointStar cx={500} cy={motifY} size={14} />
      <Crescent cx={565} cy={motifY} r={9} facing="left" />
    </g>
  );
}
