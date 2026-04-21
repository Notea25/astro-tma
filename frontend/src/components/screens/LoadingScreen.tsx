import styles from './LoadingScreen.module.css';

const CX = 250;
const CY = 250;
const ZODIAC_OUTER = 212;
const ZODIAC_INNER = 172;
const DASH_R = 150;
const ORBIT_R = 116;
const CENTER_R = 28;

const ZODIAC_GLYPHS = [
  '♈︎', '♉︎', '♊︎', '♋︎',
  '♌︎', '♍︎', '♎︎', '♏︎',
  '♐︎', '♑︎', '♒︎', '♓︎',
];

const PLANETS = [
  { g: '☉', a: 22  },
  { g: '☽', a: 68  },
  { g: '☿', a: 108 },
  { g: '♀︎', a: 152 },
  { g: '♂︎', a: 196 },
  { g: '♃', a: 242 },
  { g: '♄', a: 285 },
  { g: '♆', a: 328 },
];

const ASPECT_PAIRS: [number, number][] = [
  [0, 4], [1, 5], [2, 6], [3, 7],
  [0, 2], [4, 6],
];

// Seeded star positions — consistent across renders
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

function pt(r: number, angleDeg: number) {
  const rad = (angleDeg - 90) * (Math.PI / 180);
  return {
    x: +(CX + r * Math.cos(rad)).toFixed(2),
    y: +(CY + r * Math.sin(rad)).toFixed(2),
  };
}

function sectorPath(r1: number, r2: number, a1: number, a2: number): string {
  const p1 = pt(r2, a1), p2 = pt(r2, a2);
  const p3 = pt(r1, a2), p4 = pt(r1, a1);
  return `M ${p1.x} ${p1.y} A ${r2} ${r2} 0 0 1 ${p2.x} ${p2.y} L ${p3.x} ${p3.y} A ${r1} ${r1} 0 0 0 ${p4.x} ${p4.y} Z`;
}

export function LoadingScreenFull() {
  return (
    <div className={styles.screen}>

      {/* Cosmic background — full-screen star + comet layer */}
      <svg
        className={styles.starsBg}
        viewBox="0 0 1000 1000"
        preserveAspectRatio="xMidYMid slice"
        aria-hidden="true"
      >
        <defs>
          <radialGradient id="nebF1" cx="35%" cy="28%" r="46%">
            <stop offset="0%" stopColor="#2a1275" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#2a1275" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="nebF2" cx="70%" cy="70%" r="40%">
            <stop offset="0%" stopColor="#083a50" stopOpacity="0.7" />
            <stop offset="100%" stopColor="#083a50" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="nebF3" cx="15%" cy="75%" r="32%">
            <stop offset="0%" stopColor="#1e0845" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#1e0845" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="glowCenterF" cx="50%" cy="50%" r="22%">
            <stop offset="0%" stopColor="#C9A961" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#C9A961" stopOpacity="0" />
          </radialGradient>
        </defs>

        <rect width={1000} height={1000} fill="url(#nebF1)" />
        <rect width={1000} height={1000} fill="url(#nebF2)" />
        <rect width={1000} height={1000} fill="url(#nebF3)" />
        <rect width={1000} height={1000} fill="url(#glowCenterF)" />

        {/* Stars */}
        {STARS.map((s, i) => (
          <circle key={i} cx={s.x} cy={s.y} r={s.r} fill="white" opacity={s.o} />
        ))}

        {/* Comet 1 — slight upward-right, y≈430 */}
        <g opacity="0">
          <line x1="-168" y1="478" x2="-88" y2="452" stroke="rgba(255,255,255,0.18)" strokeWidth={0.7} />
          <line x1="-88" y1="452" x2="-28" y2="432" stroke="rgba(255,255,255,0.52)" strokeWidth={1.1} />
          <line x1="-28" y1="432" x2="2" y2="422" stroke="rgba(255,255,255,0.95)" strokeWidth={2} />
          <circle cx="2" cy="422" r="2.2" fill="white" />
          <animateTransform attributeName="transform" type="translate" from="0 0" to="1180 -340" dur="2.2s" begin="2s;cm1t.end+14s" id="cm1t" />
          <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.06;0.78;1" dur="2.2s" begin="2s;cm1t.end+14s" />
        </g>

        {/* Comet 2 — steeper, y≈660 */}
        <g opacity="0">
          <line x1="-155" y1="718" x2="-82" y2="678" stroke="rgba(255,255,255,0.15)" strokeWidth={0.6} />
          <line x1="-82" y1="678" x2="-26" y2="648" stroke="rgba(255,255,255,0.48)" strokeWidth={1} />
          <line x1="-26" y1="648" x2="2" y2="632" stroke="rgba(255,255,255,0.92)" strokeWidth={1.8} />
          <circle cx="2" cy="632" r="2" fill="white" />
          <animateTransform attributeName="transform" type="translate" from="0 0" to="1060 -570" dur="2.6s" begin="9s;cm2t.end+18s" id="cm2t" />
          <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.06;0.76;1" dur="2.6s" begin="9s;cm2t.end+18s" />
        </g>

        {/* Comet 3 — shallow, y≈245 */}
        <g opacity="0">
          <line x1="-162" y1="272" x2="-84" y2="254" stroke="rgba(255,255,255,0.15)" strokeWidth={0.6} />
          <line x1="-84" y1="254" x2="-26" y2="240" stroke="rgba(255,255,255,0.46)" strokeWidth={1} />
          <line x1="-26" y1="240" x2="2" y2="232" stroke="rgba(255,255,255,0.9)" strokeWidth={1.7} />
          <circle cx="2" cy="232" r="1.9" fill="white" />
          <animateTransform attributeName="transform" type="translate" from="0 0" to="1240 -265" dur="2s" begin="18s;cm3t.end+22s" id="cm3t" />
          <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.07;0.78;1" dur="2s" begin="18s;cm3t.end+22s" />
        </g>
      </svg>

      {/* Wheel animation */}
      <svg
        viewBox="0 0 500 500"
        width={350}
        style={{ maxWidth: '92vw', position: 'relative', zIndex: 1 }}
        aria-hidden="true"
      >
        <defs>
          {/* Gold glow for planets */}
          <filter id="glwGoldF" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {/* Strong glow for center star */}
          <filter id="glwStarF" x="-120%" y="-120%" width="340%" height="340%">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {/* Subtle ring glow */}
          <filter id="glwRingF" x="-8%" y="-8%" width="116%" height="116%">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Depth rings */}
        <circle cx={CX} cy={CY} r={165} fill="none" stroke="rgba(245,230,200,0.04)" strokeWidth={1} />
        <circle cx={CX} cy={CY} r={137} fill="none" stroke="rgba(245,230,200,0.04)" strokeWidth={1} />

        {/* Zodiac ring — glowing, rotates CW */}
        <g className={styles.zodiacRing} filter="url(#glwRingF)">
          {ZODIAC_GLYPHS.map((_, i) =>
            i % 2 === 0 ? (
              <path
                key={`sf${i}`}
                d={sectorPath(ZODIAC_INNER, ZODIAC_OUTER, i * 30, (i + 1) * 30)}
                fill="#4A7C7E"
                opacity={0.15}
              />
            ) : null
          )}
          <circle cx={CX} cy={CY} r={ZODIAC_OUTER} fill="none" stroke="#D4B86A" strokeWidth={1.2} opacity={0.75} />
          <circle cx={CX} cy={CY} r={ZODIAC_INNER} fill="none" stroke="#D4B86A" strokeWidth={0.7} opacity={0.45} />
          {ZODIAC_GLYPHS.map((_, i) => {
            const a = pt(ZODIAC_INNER, i * 30);
            const b = pt(ZODIAC_OUTER, i * 30);
            return (
              <line key={`d${i}`}
                x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke="#D4B86A" strokeWidth={0.6} opacity={0.4}
              />
            );
          })}
          {ZODIAC_GLYPHS.map((g, i) => {
            const midR = (ZODIAC_OUTER + ZODIAC_INNER) / 2;
            const { x, y } = pt(midR, (i + 0.5) * 30);
            return (
              <text key={`zg${i}`}
                x={x} y={y}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={15}
                fill="#F0DCB0"
                opacity={0.8}
                style={{ fontFamily: '"Inter", "Helvetica Neue", sans-serif' }}
              >{g}</text>
            );
          })}
        </g>

        {/* Inner dashed ring — rotates CCW */}
        <g className={styles.innerDashRing}>
          <circle cx={CX} cy={CY} r={DASH_R}
            fill="none"
            stroke="rgba(74,124,126,0.4)"
            strokeWidth={1}
            strokeDasharray="2 7"
          />
        </g>

        {/* Orbit track */}
        <circle cx={CX} cy={CY} r={ORBIT_R}
          fill="none"
          stroke="rgba(245,230,200,0.08)"
          strokeWidth={1}
        />

        {/* Aspect lines — alternating gold / teal, draw in */}
        {ASPECT_PAIRS.map(([a, b], i) => {
          const pa = pt(ORBIT_R, PLANETS[a].a);
          const pb = pt(ORBIT_R, PLANETS[b].a);
          const len = Math.ceil(Math.hypot(pb.x - pa.x, pb.y - pa.y));
          const color = i % 2 === 0 ? '#E8C862' : '#5BAAAD';
          return (
            <line key={`al${i}`}
              x1={pa.x} y1={pa.y} x2={pb.x} y2={pb.y}
              stroke={color}
              strokeWidth={1.2}
              opacity={0.55}
              strokeDasharray={len}
              strokeDashoffset={len}
              className={styles.aspectLine}
              style={{ animationDelay: `${0.8 + i * 0.22}s` }}
            />
          );
        })}

        {/* Planet nodes — glow, staggered appearance */}
        {PLANETS.map(({ g, a }, i) => {
          const { x, y } = pt(ORBIT_R, a);
          return (
            <g key={`pl${i}`}
              className={styles.planet}
              style={{ animationDelay: `${i * 0.13}s` }}
              filter="url(#glwGoldF)"
            >
              <circle cx={x} cy={y} r={14}
                fill="#0d1630"
                stroke="#E8C862"
                strokeWidth={1.5}
              />
              <text x={x} y={y}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={13}
                fill="#F0DC90"
                style={{ fontFamily: '"Inter", "Helvetica Neue", sans-serif' }}
              >{g}</text>
            </g>
          );
        })}

        {/* Center aura — expanding pulse ring */}
        <circle
          cx={CX} cy={CY} r={CENTER_R + 8}
          fill="none"
          stroke="rgba(232,200,98,0.5)"
          strokeWidth={18}
          className={styles.centerAura}
        />

        {/* Center star — strong glow */}
        <g className={styles.centerStarFull} filter="url(#glwStarF)">
          <circle cx={CX} cy={CY} r={CENTER_R}
            fill="none"
            stroke="rgba(232,200,98,0.35)"
            strokeWidth={1}
          />
          <polygon
            points={`${CX},${CY - 15} ${CX + 4.5},${CY - 4.5} ${CX + 15},${CY} ${CX + 4.5},${CY + 4.5} ${CX},${CY + 15} ${CX - 4.5},${CY + 4.5} ${CX - 15},${CY} ${CX - 4.5},${CY - 4.5}`}
            fill="#FFD966"
          />
          <polygon
            points={`${CX},${CY - 10} ${CX + 3},${CY - 3} ${CX + 10},${CY} ${CX + 3},${CY + 3} ${CX},${CY + 10} ${CX - 3},${CY + 3} ${CX - 10},${CY} ${CX - 3},${CY - 3}`}
            fill="#FFD966"
            opacity={0.55}
            transform={`rotate(45 ${CX} ${CY})`}
          />
          <circle cx={CX} cy={CY} r={2} fill="#0b0e2c" />
        </g>
      </svg>

      {/* Footer — pinned to bottom, independent of wheel */}
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
