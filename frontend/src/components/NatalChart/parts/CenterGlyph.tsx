import { polar } from '../utils/geometry';

/**
 * A small 4-point star at the wheel's center — the keyhole / fixed eye the
 * brief calls for. Geometric, not pictorial: two thin diamonds offset at 45°.
 */
export function CenterGlyph() {
  const outerR = 10;
  const innerR = 3;
  const rotations = [0, 45];

  return (
    <g data-part="center-glyph">
      {rotations.map((rot) => (
        <polygon
          key={rot}
          points={[0, 1, 2, 3]
            .map((i) => {
              const r = i % 2 === 0 ? outerR : innerR;
              const ang = rot + i * 90;
              const p = polar(0, 0, r, ang);
              return `${p.x},${p.y}`;
            })
            .join(' ')}
          fill="var(--natal-accent)"
          opacity={rot === 0 ? 1 : 0.55}
        />
      ))}
      <circle r={1.5} fill="var(--natal-bg)" />
    </g>
  );
}
