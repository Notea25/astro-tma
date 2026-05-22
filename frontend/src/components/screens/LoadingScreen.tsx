const CX = 250;
const CY = 250;

const R_TEXT_OUT  = 244;
const R_TEXT_IN   = 222;
const R_SYM_OUT   = 218;
const R_SYM_IN    = 162;
const R_MID_OUT   = 158;
const R_MID_IN    = 120;
const R_ARROWS_OUT = 115;
const R_ARROWS_IN  = 88;
const R_INNER_OUT  = 85;
const R_INNER_IN   = 58;
const R_SUN_BODY   = 22;

// Кастомные SVG-пути для каждого знака зодиака — outline-style, в локальном
// viewBox 100×100, центрированы по (50, 50). Размер регулируется через scale().
const ZODIAC_PATHS: Record<string, string> = {
  ARIES:
    "M 30 70 C 30 38 32 25 40 22 C 46 20 50 26 50 35 C 50 26 54 20 60 22 C 68 25 70 38 70 70",
  TAURUS:
    "M 50 75 m -16 0 a 16 16 0 1 0 32 0 a 16 16 0 1 0 -32 0 " +
    "M 34 55 C 30 40 18 30 18 30 M 66 55 C 70 40 82 30 82 30",
  GEMINI:
    "M 28 25 L 28 75 M 28 25 C 38 30 50 30 50 30 M 28 75 C 38 70 50 70 50 70 " +
    "M 72 25 L 72 75 M 72 25 C 62 30 50 30 50 30 M 72 75 C 62 70 50 70 50 70",
  CANCER:
    "M 25 38 a 12 12 0 1 1 24 0 M 51 62 a 12 12 0 1 1 24 0 " +
    "M 30 38 m -5 0 a 5 5 0 1 0 10 0 a 5 5 0 1 0 -10 0 " +
    "M 70 62 m -5 0 a 5 5 0 1 0 10 0 a 5 5 0 1 0 -10 0",
  LEO:
    "M 38 60 a 14 14 0 1 1 28 0 L 66 76 a 8 8 0 0 0 14 -2",
  VIRGO:
    "M 22 78 L 22 30 C 22 26 26 26 28 30 L 32 70 L 32 30 " +
    "C 32 26 36 26 38 30 L 42 70 L 42 30 C 42 26 46 26 48 30 L 52 75 " +
    "C 55 80 60 78 60 70 L 60 50 a 10 10 0 1 1 -8 18",
  LIBRA:
    "M 18 78 L 82 78 M 18 64 L 82 64 " +
    "M 30 64 a 20 20 0 1 1 40 0",
  SCORPIO:
    "M 22 78 L 22 30 C 22 26 26 26 28 30 L 32 70 L 32 30 " +
    "C 32 26 36 26 38 30 L 42 70 L 42 30 C 42 26 46 26 48 30 L 52 75 " +
    "L 64 75 L 70 68 M 70 68 L 78 75 M 78 75 L 70 75",
  SAGITTARIUS:
    "M 25 78 L 78 25 M 78 25 L 65 25 M 78 25 L 78 38 " +
    "M 38 50 L 55 67",
  CAPRICORN:
    "M 22 28 L 32 60 L 42 28 L 56 70 " +
    "M 56 70 a 10 10 0 1 1 -2 -16 a 8 8 0 1 0 6 14",
  AQUARIUS:
    "M 18 40 L 30 30 L 42 40 L 54 30 L 66 40 L 78 30 " +
    "M 18 62 L 30 52 L 42 62 L 54 52 L 66 62 L 78 52",
  PISCES:
    "M 24 22 C 16 50 16 50 24 78 M 76 22 C 84 50 84 50 76 78 " +
    "M 20 50 L 80 50",
};

const ZODIAC: { name: keyof typeof ZODIAC_PATHS; label: string }[] = [
  { name: "ARIES",       label: "ARIES" },
  { name: "TAURUS",      label: "TAURUS" },
  { name: "GEMINI",      label: "GEMINI" },
  { name: "CANCER",      label: "CANCER" },
  { name: "LEO",         label: "LEO" },
  { name: "VIRGO",       label: "VIRGO" },
  { name: "LIBRA",       label: "LIBRA" },
  { name: "SCORPIO",     label: "SCORPIO" },
  { name: "SAGITTARIUS", label: "SAGITTARIUS" },
  { name: "CAPRICORN",   label: "CAPRICORN" },
  { name: "AQUARIUS",    label: "AQUARIUS" },
  { name: "PISCES",      label: "PISCES" },
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

// Helper: render a zodiac sign as an SVG path, centered at (cx, cy), scaled to `size`.
function ZodiacIcon({
  name, cx, cy, size, stroke, opacity = 1, strokeWidth = 2,
}: {
  name: keyof typeof ZODIAC_PATHS;
  cx: number;
  cy: number;
  size: number;
  stroke: string;
  opacity?: number;
  strokeWidth?: number;
}) {
  const scale = size / 100;
  return (
    <g transform={`translate(${cx - size / 2}, ${cy - size / 2}) scale(${scale})`}>
      <path
        d={ZODIAC_PATHS[name]}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth / scale}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={opacity}
      />
    </g>
  );
}

const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600&display=swap');

._lsz_screen {
  position: relative;
  width: 100%;
  height: 100dvh;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: radial-gradient(ellipse at 50% 40%, #0e0928 0%, #060718 50%, #020408 100%);
  overflow: hidden;
}

._lsz_starsBg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

._lsz_namesRing { transform-origin: 250px 250px; animation: _lsz_spinCw  70s linear infinite; }
._lsz_symRing   { transform-origin: 250px 250px; animation: _lsz_spinCw  70s linear infinite; }
._lsz_midRing   { transform-origin: 250px 250px; animation: _lsz_spinCcw 90s linear infinite; }
._lsz_arrowsRing{ transform-origin: 250px 250px; animation: _lsz_spinCw  40s linear infinite; }
._lsz_innerRing { transform-origin: 250px 250px; animation: _lsz_spinCcw 150s linear infinite; }

._lsz_centerSun {
  transform-origin: 250px 250px;
  animation: _lsz_pulseSun 4.4s ease-in-out infinite;
}

._lsz_centerAura {
  transform-box: fill-box;
  transform-origin: center;
  animation: _lsz_pulseAura 3.6s ease-out infinite;
}

._lsz_footer {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  margin-top: 28px;
  pointer-events: none;
}

._lsz_appTitle {
  margin: 0;
  padding: 0;
  font-family: "Cinzel", "Della Respira", Georgia, serif;
  font-size: 28px;
  font-weight: 500;
  letter-spacing: 0.28em;
  color: #E8C862;
  animation: _lsz_shimmer 4s ease-in-out infinite;
  text-shadow:
    0 0 18px rgba(232, 200, 98, 0.7),
    0 0 45px rgba(232, 200, 98, 0.35);
}

._lsz_dots { display: flex; gap: 9px; }
._lsz_dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(232, 200, 98, 0.65);
  animation: _lsz_dotPulse 1.4s ease-in-out infinite;
}
._lsz_dot:nth-child(2) { animation-delay: 0.22s; }
._lsz_dot:nth-child(3) { animation-delay: 0.44s; }

@keyframes _lsz_spinCw  { to { transform: rotate(360deg);  } }
@keyframes _lsz_spinCcw { to { transform: rotate(-360deg); } }
@keyframes _lsz_pulseSun {
  0%, 100% { transform: scale(1);    }
  50%       { transform: scale(1.05); }
}
@keyframes _lsz_pulseAura {
  0%        { transform: scale(0.9);  opacity: 0.45; }
  60%, 100% { transform: scale(1.7);  opacity: 0;    }
}
@keyframes _lsz_shimmer {
  0%, 100% { opacity: 0.88; }
  50%       { opacity: 1;    }
}
@keyframes _lsz_dotPulse {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40%           { transform: scale(1);   opacity: 1;   }
}
`;

export function LoadingScreenFull() {
  return (
    <>
      <style>{CSS}</style>
      <div className="_lsz_screen">

        <svg
          className="_lsz_starsBg"
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
              const p1 = pt(r, a1);
              const p2 = pt(r, a2);
              return (
                <path
                  key={`arc${i}`}
                  id={`arcText${i}`}
                  d={`M ${p1.x} ${p1.y} A ${r} ${r} 0 0 1 ${p2.x} ${p2.y}`}
                  fill="none"
                />
              );
            })}

            <filter id="zSoftGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="0.8" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Концентрические золотые обводки колец */}
          <circle cx={CX} cy={CY} r={R_TEXT_OUT}  fill="none" stroke={GOLD_DIM} strokeWidth={1.4} opacity={0.85} />
          <circle cx={CX} cy={CY} r={R_TEXT_IN}   fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
          <circle cx={CX} cy={CY} r={R_SYM_IN}    fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
          <circle cx={CX} cy={CY} r={R_MID_IN}    fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
          <circle cx={CX} cy={CY} r={R_ARROWS_OUT} fill="none" stroke={GOLD_DIM} strokeWidth={1}  opacity={0.6} />
          <circle cx={CX} cy={CY} r={R_ARROWS_IN}  fill="none" stroke={GOLD_DIM} strokeWidth={1}  opacity={0.6} />
          <circle cx={CX} cy={CY} r={R_INNER_IN}  fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.55} />

          {/* 12 радиальных делителей через все кольца знаков */}
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

          {/* Внешнее кольцо — названия зодиаков по дуге (CW 70s) */}
          <g className="_lsz_namesRing">
            {ZODIAC.map(({ label }, i) => (
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
                <textPath href={`#arcText${i}`} startOffset="50%" textAnchor="middle">
                  {label}
                </textPath>
              </text>
            ))}
          </g>

          {/* Большие нарисованные SVG-символы знаков (CW 70s) */}
          <g className="_lsz_symRing">
            {ZODIAC.map(({ name }, i) => {
              const midAngle = i * 30 + 15;
              const labelR = (R_SYM_OUT + R_SYM_IN) / 2;
              const { x, y } = pt(labelR, midAngle);
              return (
                <ZodiacIcon
                  key={`s${i}`}
                  name={name}
                  cx={x}
                  cy={y}
                  size={42}
                  stroke={GOLD}
                  strokeWidth={2.2}
                  opacity={0.95}
                />
              );
            })}
          </g>

          {/* Среднее кольцо — те же знаки но мельче (CCW 90s) */}
          <g className="_lsz_midRing">
            {ZODIAC.map(({ name }, i) => {
              const midAngle = i * 30 + 15;
              const labelR = (R_MID_OUT + R_MID_IN) / 2;
              const { x, y } = pt(labelR, midAngle);
              return (
                <ZodiacIcon
                  key={`m${i}`}
                  name={name}
                  cx={x}
                  cy={y}
                  size={26}
                  stroke={GOLD_DIM}
                  strokeWidth={1.6}
                  opacity={0.9}
                />
              );
            })}
          </g>

          {/* Декоративное кольцо со стрелками-треугольниками (CW 40s) */}
          <g className="_lsz_arrowsRing">
            {/* 12 наружных треугольников (тонкое колесо астролябии) */}
            {Array.from({ length: 12 }).map((_, i) => {
              const angle = i * 30 + 15;
              const tip = pt(R_ARROWS_OUT - 1, angle);
              const baseR = R_ARROWS_OUT - 11;
              const b1 = pt(baseR, angle - 4);
              const b2 = pt(baseR, angle + 4);
              return (
                <polygon
                  key={`ao${i}`}
                  points={`${b1.x},${b1.y} ${tip.x},${tip.y} ${b2.x},${b2.y}`}
                  fill={GOLD}
                  opacity={0.85}
                />
              );
            })}
            {/* 12 внутренних треугольников, направленных внутрь */}
            {Array.from({ length: 12 }).map((_, i) => {
              const angle = i * 30 + 15;
              const tip = pt(R_ARROWS_IN + 1, angle);
              const baseR = R_ARROWS_IN + 11;
              const b1 = pt(baseR, angle - 4);
              const b2 = pt(baseR, angle + 4);
              return (
                <polygon
                  key={`ai${i}`}
                  points={`${b1.x},${b1.y} ${tip.x},${tip.y} ${b2.x},${b2.y}`}
                  fill={GOLD}
                  opacity={0.85}
                />
              );
            })}
          </g>

          {/* Внутреннее кольцо — те же знаки мелкими (CCW 150s) */}
          <g className="_lsz_innerRing">
            {ZODIAC.map(({ name }, i) => {
              const midAngle = i * 30 + 15;
              const labelR = (R_INNER_OUT + R_INNER_IN) / 2;
              const { x, y } = pt(labelR, midAngle);
              return (
                <ZodiacIcon
                  key={`in${i}`}
                  name={name}
                  cx={x}
                  cy={y}
                  size={16}
                  stroke={GOLD}
                  strokeWidth={1.3}
                  opacity={0.85}
                />
              );
            })}
          </g>

          {/* Центральное солнце — минимальное (точка с обводкой) */}
          <g className="_lsz_centerSun" filter="url(#zSoftGlow)">
            <circle cx={CX} cy={CY} r={R_SUN_BODY} fill="none" stroke={GOLD_DIM} strokeWidth={1.5} />
            <circle cx={CX} cy={CY} r={5.5} fill={GOLD} />
            <circle cx={CX} cy={CY} r={3.5} fill="rgba(6, 4, 21, 0.95)" />
            <circle cx={CX} cy={CY} r={1.8} fill={GOLD} />
          </g>

          {/* Пульсирующая аура вокруг солнца */}
          <circle
            cx={CX} cy={CY} r={R_SUN_BODY + 4}
            fill="none"
            stroke="rgba(232, 200, 98, 0.45)"
            strokeWidth={4}
            className="_lsz_centerAura"
          />
        </svg>

        <div className="_lsz_footer">
          <h1 className="_lsz_appTitle">ASTRO</h1>
          <div className="_lsz_dots" aria-hidden="true">
            <div className="_lsz_dot" />
            <div className="_lsz_dot" />
            <div className="_lsz_dot" />
          </div>
        </div>

      </div>
    </>
  );
}
