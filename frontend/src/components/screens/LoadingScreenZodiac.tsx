import styles from './LoadingScreenZodiac.module.css';

const CX = 250;
const CY = 250;

// Concentric ring boundaries (outer → inner)
const R_TEXT_OUT   = 244;
const R_TEXT_IN    = 222;
const R_SYM_OUT    = 218;
const R_SYM_IN     = 168;
const R_MID_OUT    = 164;
const R_MID_IN     = 128;
const R_ARROWS_OUT = 124;
const R_ARROWS_IN  = 78;
const R_SUN_RING   = 10;

// 12 zodiac signs as hand-crafted SVG paths
// (local viewBox 0..100, centred on 50,50 — stroke-only outline)
const ZODIAC = [
  { name: 'ARIES',
    path: 'M 22 72 C 22 38 32 22 42 22 C 50 22 50 32 50 42 M 78 72 C 78 38 68 22 58 22 C 50 22 50 32 50 42' },
  { name: 'TAURUS',
    path: 'M 50 62 m -22 0 a 22 22 0 1 0 44 0 a 22 22 0 1 0 -44 0 M 28 48 C 28 26 38 18 50 36 M 72 48 C 72 26 62 18 50 36' },
  { name: 'GEMINI',
    path: 'M 32 22 L 32 78 M 68 22 L 68 78 M 26 28 L 74 28 M 26 72 L 74 72' },
  { name: 'CANCER',
    path: 'M 22 40 a 28 18 0 0 1 56 0 M 78 60 a 28 18 0 0 1 -56 0 M 30 34 m -6 0 a 6 6 0 1 0 12 0 a 6 6 0 1 0 -12 0 M 70 66 m -6 0 a 6 6 0 1 0 12 0 a 6 6 0 1 0 -12 0' },
  { name: 'LEO',
    path: 'M 36 44 m -14 0 a 14 14 0 1 1 28 0 a 14 14 0 1 1 -28 0 M 50 44 C 72 44 80 58 64 74 C 54 82 44 72 52 64' },
  { name: 'VIRGO',
    path: 'M 18 78 L 18 30 C 18 24 26 24 28 30 L 32 70 M 32 30 C 32 24 40 24 42 30 L 46 70 M 46 30 C 46 24 54 24 56 30 L 60 76 C 62 82 68 80 68 70 L 68 56 a 8 8 0 1 1 -6 12' },
  { name: 'LIBRA',
    path: 'M 14 78 L 86 78 M 14 64 L 86 64 M 26 64 a 24 16 0 0 1 48 0' },
  { name: 'SCORPIO',
    path: 'M 18 78 L 18 30 C 18 24 26 24 28 30 L 32 70 M 32 30 C 32 24 40 24 42 30 L 46 70 M 46 30 C 46 24 54 24 56 30 L 60 76 L 78 70 L 88 80 M 88 80 L 84 72 M 88 80 L 80 80' },
  { name: 'SAGITTARIUS',
    path: 'M 22 78 L 80 20 M 80 20 L 62 20 M 80 20 L 80 38 M 36 56 L 56 76' },
  { name: 'CAPRICORN',
    path: 'M 18 28 L 30 66 L 44 28 L 60 70 a 10 10 0 1 1 -4 -18 a 8 8 0 1 0 8 14' },
  { name: 'AQUARIUS',
    path: 'M 16 40 Q 24 30 32 40 T 48 40 T 64 40 T 80 40 M 16 60 Q 24 50 32 60 T 48 60 T 64 60 T 80 60' },
  { name: 'PISCES',
    path: 'M 22 22 C 12 50 12 50 22 78 M 78 22 C 88 50 88 50 78 78 M 22 50 L 78 50' },
];

const GOLD       = '#E8C862';
const GOLD_DIM   = '#C4A35A';
const GOLD_FAINT = '#8B6B3A';

function pt(r: number, angleDeg: number) {
  const rad = (angleDeg - 90) * (Math.PI / 180);
  return {
    x: +(CX + r * Math.cos(rad)).toFixed(2),
    y: +(CY + r * Math.sin(rad)).toFixed(2),
  };
}

function arcPath(r: number, a1: number, a2: number, id: string) {
  const p1 = pt(r, a1);
  const p2 = pt(r, a2);
  return <path id={id} d={`M ${p1.x} ${p1.y} A ${r} ${r} 0 0 1 ${p2.x} ${p2.y}`} fill="none" />;
}

// Render a zodiac SVG-path icon centred at (cx, cy), scaled to `size` px.
function ZodiacIcon({
  d, cx, cy, size, color, opacity = 1, strokeWidth = 2.5,
}: {
  d: string;
  cx: number;
  cy: number;
  size: number;
  color: string;
  opacity?: number;
  strokeWidth?: number;
}) {
  const scale = size / 100;
  return (
    <g transform={`translate(${cx - size / 2} ${cy - size / 2}) scale(${scale})`}>
      <path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth / scale}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={opacity}
      />
    </g>
  );
}

function makeStars(count: number) {
  let s = 0x12ab5678;
  const next = () => { s ^= s << 13; s ^= s >> 17; s ^= s << 5; return (s >>> 0) / 4294967296; };
  return Array.from({ length: count }, () => ({
    x: +(next() * 1000).toFixed(1),
    y: +(next() * 1000).toFixed(1),
    r: +(next() * 1.6 + 0.3).toFixed(2),
    o: +(next() * 0.7 + 0.28).toFixed(2),
  }));
}
const STARS = makeStars(220);

export function LoadingScreenZodiac() {
  return (
    <div className={styles.screen}>

      <svg
        className={styles.starsBg}
        viewBox="0 0 1000 1000"
        preserveAspectRatio="xMidYMid slice"
        aria-hidden="true"
      >
        <defs>
          <radialGradient id="zNeb1" cx="35%" cy="28%" r="46%">
            <stop offset="0%" stopColor="#2a1275" stopOpacity="0.65" />
            <stop offset="100%" stopColor="#2a1275" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="zNeb2" cx="70%" cy="70%" r="40%">
            <stop offset="0%" stopColor="#083a50" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#083a50" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="zNebCtr" cx="50%" cy="50%" r="22%">
            <stop offset="0%" stopColor="#CDA94B" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#CDA94B" stopOpacity="0" />
          </radialGradient>
        </defs>
        <rect width={1000} height={1000} fill="url(#zNeb1)" />
        <rect width={1000} height={1000} fill="url(#zNeb2)" />
        <rect width={1000} height={1000} fill="url(#zNebCtr)" />
        {STARS.map((s, i) => (
          <circle key={i} cx={s.x} cy={s.y} r={s.r} fill="white" opacity={s.o} />
        ))}
      </svg>

      <svg
        viewBox="0 0 500 500"
        width={350}
        style={{ maxWidth: '92vw', position: 'relative', zIndex: 1 }}
        aria-hidden="true"
      >
        <defs>
          {ZODIAC.map((_, i) => {
            const r = (R_TEXT_OUT + R_TEXT_IN) / 2;
            const a1 = i * 30;
            const a2 = a1 + 30;
            return <g key={`arcDef${i}`}>{arcPath(r, a1, a2, `arcText${i}`)}</g>;
          })}

          <filter id="zSoftGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="0.8" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* === CONCENTRIC RING BORDERS === */}
        <circle cx={CX} cy={CY} r={R_TEXT_OUT}   fill="none" stroke={GOLD_DIM} strokeWidth={1.4} opacity={0.9} />
        <circle cx={CX} cy={CY} r={R_TEXT_IN}    fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.7} />
        <circle cx={CX} cy={CY} r={R_SYM_IN}     fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
        <circle cx={CX} cy={CY} r={R_MID_OUT}    fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.55} />
        <circle cx={CX} cy={CY} r={R_MID_IN}     fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.55} />
        <circle cx={CX} cy={CY} r={R_ARROWS_OUT} fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.55} />
        <circle cx={CX} cy={CY} r={R_ARROWS_IN}  fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.55} />

        {/* === 12 RADIAL DIVIDERS (only through outer name/symbol rings) === */}
        {Array.from({ length: 12 }).map((_, i) => {
          const angle = i * 30;
          const a = pt(R_MID_IN, angle);
          const b = pt(R_TEXT_OUT, angle);
          return (
            <line
              key={`div${i}`}
              x1={a.x} y1={a.y} x2={b.x} y2={b.y}
              stroke={GOLD_FAINT}
              strokeWidth={0.8}
              opacity={0.5}
            />
          );
        })}

        {/* === OUTER RING: names on arcs (clockwise rotation) === */}
        <g className={styles.namesRing}>
          {ZODIAC.map(({ name }, i) => (
            <text
              key={`n${i}`}
              fontSize={11}
              fill={GOLD}
              style={{
                fontFamily: '"Cinzel", "Della Respira", Georgia, serif',
                letterSpacing: '0.22em',
                fontWeight: 500,
              }}
            >
              <textPath
                href={`#arcText${i}`}
                startOffset="50%"
                textAnchor="middle"
              >
                {name}
              </textPath>
            </text>
          ))}
        </g>

        {/* === RING 2: LARGE zodiac glyphs as SVG paths === */}
        <g className={styles.symRing}>
          {ZODIAC.map(({ name, path }, i) => {
            const midAngle = i * 30 + 15;
            const labelR = (R_SYM_OUT + R_SYM_IN) / 2;
            const { x, y } = pt(labelR, midAngle);
            return (
              <g key={`s${i}-${name}`} filter="url(#zSoftGlow)">
                <ZodiacIcon d={path} cx={x} cy={y} size={42} color={GOLD} strokeWidth={3} />
              </g>
            );
          })}
        </g>

        {/* === RING 3: MIDDLE zodiac glyphs === */}
        <g className={styles.midRing}>
          {ZODIAC.map(({ name, path }, i) => {
            const midAngle = i * 30 + 15;
            const labelR = (R_MID_OUT + R_MID_IN) / 2;
            const { x, y } = pt(labelR, midAngle);
            return (
              <ZodiacIcon
                key={`m${i}-${name}`}
                d={path}
                cx={x}
                cy={y}
                size={26}
                color={GOLD_DIM}
                strokeWidth={2.2}
                opacity={0.95}
              />
            );
          })}
        </g>

        {/* === RING 4: decorative arrow ring (long inward triangles + small ticks) === */}
        <g className={styles.arrowsRing}>
          {/* 12 large inward-pointing triangles */}
          {Array.from({ length: 12 }).map((_, i) => {
            const angle = i * 30 + 15;
            const tip = pt(R_ARROWS_IN + 1, angle);
            const baseR = R_ARROWS_OUT - 2;
            const b1 = pt(baseR, angle - 4);
            const b2 = pt(baseR, angle + 4);
            return (
              <polygon
                key={`ai${i}`}
                points={`${b1.x},${b1.y} ${tip.x},${tip.y} ${b2.x},${b2.y}`}
                fill={GOLD}
                opacity={0.92}
              />
            );
          })}
          {/* 12 short radial ticks between the triangles */}
          {Array.from({ length: 12 }).map((_, i) => {
            const angle = i * 30;
            const inner = pt(R_ARROWS_IN + 6, angle);
            const outer = pt(R_ARROWS_OUT - 6, angle);
            return (
              <line
                key={`tick${i}`}
                x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y}
                stroke={GOLD}
                strokeWidth={1.4}
                strokeLinecap="round"
                opacity={0.85}
              />
            );
          })}
        </g>

        {/* === CENTRE: empty dark field with tiny classical ☉ === */}
        <g className={styles.centerSun}>
          <circle cx={CX} cy={CY} r={R_SUN_RING}     fill="none" stroke={GOLD} strokeWidth={1.4} opacity={0.95} />
          <circle cx={CX} cy={CY} r={R_SUN_RING - 6} fill={GOLD} />
        </g>

        {/* Subtle pulse aura around the centre dot */}
        <circle
          cx={CX} cy={CY} r={R_SUN_RING + 4}
          fill="none"
          stroke="rgba(232, 200, 98, 0.45)"
          strokeWidth={3}
          className={styles.centerAura}
        />
      </svg>

      <div className={styles.footer}>
        <h1 className={styles.appTitle}>ASTRO</h1>
        <div className={styles.dots} aria-hidden="true">
          <div className={styles.dot} />
          <div className={styles.dot} />
          <div className={styles.dot} />
        </div>
      </div>
    </div>
  );
}
