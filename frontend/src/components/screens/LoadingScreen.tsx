const CX = 250;
const CY = 250;

const R_TEXT_OUT  = 244;
const R_TEXT_IN   = 222;
const R_SYM_OUT   = 218;
const R_SYM_IN    = 165;
const R_MID_OUT   = 160;
const R_MID_IN    = 118;
const R_INNER_OUT = 113;
const R_INNER_IN  = 82;
const R_SUN_BODY  = 70;

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
._lsz_innerRing { transform-origin: 250px 250px; animation: _lsz_spinCw 150s linear infinite; }

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
              <feGaussianBlur stdDeviation="1.2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          <circle cx={CX} cy={CY} r={R_TEXT_OUT}  fill="none" stroke={GOLD_DIM} strokeWidth={1.4} opacity={0.85} />
          <circle cx={CX} cy={CY} r={R_TEXT_IN}   fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
          <circle cx={CX} cy={CY} r={R_SYM_OUT}   fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
          <circle cx={CX} cy={CY} r={R_SYM_IN}    fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
          <circle cx={CX} cy={CY} r={R_MID_OUT}   fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
          <circle cx={CX} cy={CY} r={R_MID_IN}    fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
          <circle cx={CX} cy={CY} r={R_INNER_OUT} fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />
          <circle cx={CX} cy={CY} r={R_INNER_IN}  fill="none" stroke={GOLD_DIM} strokeWidth={1}   opacity={0.65} />

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

          <g className="_lsz_namesRing">
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
                <textPath href={`#arcText${i}`} startOffset="50%" textAnchor="middle">
                  {name}
                </textPath>
              </text>
            ))}
          </g>

          <g className="_lsz_symRing">
            {ZODIAC.map(({ g }, i) => {
              const midAngle = i * 30 + 15;
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

          <g className="_lsz_midRing">
            {ZODIAC.map(({ g }, i) => {
              const midAngle = i * 30 + 15;
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

          <g className="_lsz_innerRing">
            {ZODIAC.map(({ g }, i) => {
              const midAngle = i * 30 + 15;
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

          <g className="_lsz_centerSun">
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

            <circle cx={CX} cy={CY} r={R_SUN_BODY - 8} fill="none" stroke={GOLD_DIM} strokeWidth={1.5} />

            <circle cx={CX} cy={CY} r={5.5} fill={GOLD} />
            <circle cx={CX} cy={CY} r={3.5} fill="rgba(6, 4, 21, 0.9)" />
            <circle cx={CX} cy={CY} r={1.6} fill={GOLD} />
          </g>

          <circle
            cx={CX} cy={CY} r={R_SUN_BODY + 4}
            fill="none"
            stroke="rgba(232, 200, 98, 0.45)"
            strokeWidth={5}
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
