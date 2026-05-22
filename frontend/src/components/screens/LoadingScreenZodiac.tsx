import styles from './LoadingScreenZodiac.module.css';

const CX = 250;
const CY = 250;

// Seeded stars for cosmic background (consistent renders)
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

// Ring boundaries (matching reference proportions)
const R_TEXT_OUT  = 244;
const R_TEXT_IN   = 222;
const R_SYM_OUT   = 218;
const R_SYM_IN    = 165;
const R_MID_OUT   = 160;
const R_MID_IN    = 118;
const R_INNER_OUT = 113;
const R_INNER_IN  = 82;
const R_SUN_BODY  = 70;

// 12 zodiac signs in English (clockwise from top)
const ZODIAC = [
  { g: '♈', name: 'ARIES'       },
  { g: '♉', name: 'TAURUS'      },
  { g: '♊', name: 'GEMINI'      },
  { g: '♋', name: 'CANCER'      },
  { g: '♌', name: 'LEO'         },
  { g: '♍', name: 'VIRGO'       },
  { g: '♎', name: 'LIBRA'       },
  { g: '♏', name: 'SCORPIO'     },
  { g: '♐', name: 'SAGITTARIUS' },
  { g: '♑', name: 'CAPRICORN'   },
  { g: '♒', name: 'AQUARIUS'    },
  { g: '♓', name: 'PISCES'      },
];

// Single gold palette — everything in shades of gold on transparent
const GOLD       = '#E8C862';  // bright gold for text & glyphs
const GOLD_DIM   = '#C4A35A';  // dim gold for borders / rings
const GOLD_FAINT = '#8B6B3A';  // faint gold for dividers

function pt(r: number, angleDeg: number) {
  const rad = (angleDeg - 90) * (Math.PI / 180);
  return {
    x: +(CX + r * Math.cos(rad)).toFixed(2),
    y: +(CY + r * Math.sin(rad)).toFixed(2),
  };
}

// Arc path for text-on-arc (from a1 → a2 along radius r)
function arcPath(r: number, a1: number, a2: number, id: string) {
  const p1 = pt(r, a1);
  const p2 = pt(r, a2);
  // sweep = 1 for clockwise (top arc)
  return <path id={id} d={`M ${p1.x} ${p1.y} A ${r} ${r} 0 0 1 ${p2.x} ${p2.y}`} fill="none" />;
}

export function LoadingScreenZodiac() {
  return (
    <div className={styles.screen}>

      {/* Cosmic background — stars + nebula glow */}
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
          {/* Arc paths for zodiac names — each sector midline */}
          {ZODIAC.map((_, i) => {
            // Text radius — slightly inset from outer ring
            const r = (R_TEXT_OUT + R_TEXT_IN) / 2;
            // Sector: a1 → a2
            const a1 = i * 30;
            const a2 = a1 + 30;
            return (
              <g key={`arcDef${i}`}>
                {arcPath(r, a1, a2, `arcText${i}`)}
              </g>
            );
          })}

          <filter id="zSoftGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="1.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* === CONCENTRIC RING BORDERS (gold) === */}
        <circle cx={CX} cy={CY} r={R_TEXT_OUT}  fill="none" stroke={GOLD_DIM} strokeWidth={1.4} opacity={0.85} />
        <circle cx={CX} cy={CY} r={R_TEXT_IN}   fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
        <circle cx={CX} cy={CY} r={R_SYM_OUT}   fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
        <circle cx={CX} cy={CY} r={R_SYM_IN}    fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
        <circle cx={CX} cy={CY} r={R_MID_OUT}   fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
        <circle cx={CX} cy={CY} r={R_MID_IN}    fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
        <circle cx={CX} cy={CY} r={R_INNER_OUT} fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
        <circle cx={CX} cy={CY} r={R_INNER_IN}  fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />

        {/* === RADIAL DIVIDERS (12 lines, only between outer rings) === */}
        {Array.from({ length: 12 }).map((_, i) => {
          const angle = i * 30;
          const a = pt(R_INNER_IN, angle);
          const b = pt(R_TEXT_OUT, angle);
          return (
            <line
              key={`div${i}`}
              x1={a.x} y1={a.y} x2={b.x} y2={b.y}
              stroke={GOLD_FAINT}
              strokeWidth={0.8}
              opacity={0.55}
            />
          );
        })}

        {/* === RING 1 (OUTERMOST): zodiac NAMES on arcs === */}
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

        {/* === RING 2: LARGE SYMBOLS (transparent sectors, gold glyphs) === */}
        <g className={styles.symRing}>
          {ZODIAC.map(({ g }, i) => {
            const a1 = i * 30;
            const midAngle = a1 + 15;
            const labelR = (R_SYM_OUT + R_SYM_IN) / 2;
            const { x, y } = pt(labelR, midAngle);
            return (
              <text
                key={`s${i}`}
                x={x} y={y}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={28}
                fill={GOLD}
                style={{ fontFamily: '"Inter", "Segoe UI Symbol", sans-serif', fontWeight: 600 }}
                filter="url(#zSoftGlow)"
              >{g}</text>
            );
          })}
        </g>

        {/* === RING 3 (MIDDLE): dim-gold glyphs === */}
        <g className={styles.midRing}>
          {ZODIAC.map(({ g }, i) => {
            const a1 = i * 30;
            const midAngle = a1 + 15;
            const labelR = (R_MID_OUT + R_MID_IN) / 2;
            const { x, y } = pt(labelR, midAngle);
            return (
              <text
                key={`m${i}`}
                x={x} y={y}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={22}
                fill={GOLD_DIM}
                opacity={0.9}
                style={{ fontFamily: '"Inter", "Segoe UI Symbol", sans-serif', fontWeight: 500 }}
              >{g}</text>
            );
          })}
        </g>

        {/* === RING 4 (INNER): small bright glyphs === */}
        <g className={styles.innerRing}>
          {ZODIAC.map(({ g }, i) => {
            const a1 = i * 30;
            const midAngle = a1 + 15;
            const labelR = (R_INNER_OUT + R_INNER_IN) / 2;
            const { x, y } = pt(labelR, midAngle);
            return (
              <text
                key={`in${i}`}
                x={x} y={y}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={13}
                fill={GOLD}
                opacity={0.85}
                style={{ fontFamily: '"Inter", "Segoe UI Symbol", sans-serif', fontWeight: 500 }}
              >{g}</text>
            );
          })}
        </g>

        {/* === CENTER SUN (all gold, transparent body) === */}
        <g className={styles.centerSun}>
          {/* Long pointed rays (12) */}
          {Array.from({ length: 12 }).map((_, i) => {
            const angle = i * 30;
            const tip = pt(R_SUN_BODY + 10, angle);
            const b1 = pt(R_SUN_BODY - 2, angle - 4);
            const b2 = pt(R_SUN_BODY - 2, angle + 4);
            return (
              <polygon
                key={`ry${i}`}
                points={`${b1.x},${b1.y} ${tip.x},${tip.y} ${b2.x},${b2.y}`}
                fill={GOLD_DIM}
              />
            );
          })}
          {/* Short rays (12, offset by 15°) */}
          {Array.from({ length: 12 }).map((_, i) => {
            const angle = i * 30 + 15;
            const inner = pt(R_SUN_BODY - 4, angle);
            const outer = pt(R_SUN_BODY + 3, angle);
            return (
              <line
                key={`ry2${i}`}
                x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y}
                stroke={GOLD_DIM}
                strokeWidth={1.4}
                strokeLinecap="round"
              />
            );
          })}

          {/* Sun body — transparent with gold outline */}
          <circle cx={CX} cy={CY} r={R_SUN_BODY - 8} fill="none" stroke={GOLD_DIM} strokeWidth={1.5} />

          {/* Classical astrological Sun ☉ — circle with center dot */}
          <circle cx={CX} cy={CY} r={5.5} fill={GOLD} />
          <circle cx={CX} cy={CY} r={3.5} fill="rgba(6, 4, 21, 0.9)" />
          <circle cx={CX} cy={CY} r={1.6} fill={GOLD} />
        </g>

        {/* Subtle center pulse aura */}
        <circle
          cx={CX} cy={CY} r={R_SUN_BODY + 4}
          fill="none"
          stroke="rgba(232, 200, 98, 0.45)"
          strokeWidth={5}
          className={styles.centerAura}
        />
      </svg>

      {/* Footer */}
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
