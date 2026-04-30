import { polar } from '../utils/geometry';

function starPolygon(radiusOuter: number, radiusInner: number, points = 12): string {
  const coords: string[] = [];
  for (let i = 0; i < points * 2; i++) {
    const radius = i % 2 === 0 ? radiusOuter : radiusInner;
    const angle = -90 + (i * 180) / points;
    const p = polar(0, 0, radius, angle);
    coords.push(`${p.x.toFixed(2)},${p.y.toFixed(2)}`);
  }
  return coords.join(' ');
}

export function PosterMandala() {
  return (
    <g data-part="poster-mandala">
      <circle r={86} fill="none" stroke="var(--natal-accent)" strokeWidth={1} opacity={0.42} />
      <circle r={62} fill="none" stroke="var(--natal-dim)" strokeWidth={1} opacity={0.58} />
      <polygon
        points={starPolygon(86, 34, 12)}
        fill="none"
        stroke="var(--natal-accent)"
        strokeWidth={1}
        opacity={0.5}
      />
      <polygon
        points={starPolygon(62, 22, 8)}
        fill="none"
        stroke="var(--natal-accent)"
        strokeWidth={0.9}
        opacity={0.42}
        transform="rotate(11)"
      />
      {Array.from({ length: 24 }, (_, index) => {
        const angle = index * 15;
        const inner = polar(0, 0, 70, angle);
        const outer = polar(0, 0, 88, angle);
        return (
          <line
            key={angle}
            x1={inner.x}
            y1={inner.y}
            x2={outer.x}
            y2={outer.y}
            stroke="var(--natal-accent)"
            strokeWidth={0.7}
            opacity={0.34}
          />
        );
      })}
      <circle r={18} fill="var(--natal-bg)" stroke="var(--natal-accent)" strokeWidth={1.1} opacity={0.92} />
    </g>
  );
}
