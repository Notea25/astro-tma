import { useId, useMemo } from "react";

export type ElementId = "fire" | "water" | "earth" | "air";

interface CosmicElementOrbProps {
  element: ElementId;
  size?: number;
}

interface OrbPalette {
  core: string;
  inner: string;
  mid: string;
  deep: string;
  voidC: string;
  arm: string;
  dust: string;
  glow: string;
  starTint: string;
}

const PALETTES: Record<ElementId, OrbPalette> = {
  fire: {
    core: "#ffe7a8",
    inner: "#ffb04d",
    mid: "#e8401a",
    deep: "#5a0a08",
    voidC: "#0a0204",
    arm: "#ff7a2a",
    dust: "#8a1810",
    glow: "#ffd28a",
    starTint: "#ffe6c2",
  },
  water: {
    core: "#d8f0ff",
    inner: "#7cc8ff",
    mid: "#2a78d8",
    deep: "#0e2a55",
    voidC: "#020816",
    arm: "#5aa8f0",
    dust: "#10325a",
    glow: "#a8d8ff",
    starTint: "#d8f0ff",
  },
  earth: {
    core: "#e8ffd8",
    inner: "#9ae08a",
    mid: "#2e8a4a",
    deep: "#0e3a1f",
    voidC: "#020a05",
    arm: "#6ec870",
    dust: "#1a4a28",
    glow: "#bce8a8",
    starTint: "#e8ffd8",
  },
  air: {
    core: "#f2e8ff",
    inner: "#cba8f0",
    mid: "#7858c0",
    deep: "#2a1a55",
    voidC: "#08041a",
    arm: "#a888e0",
    dust: "#3a2868",
    glow: "#d8c0f0",
    starTint: "#f2e8ff",
  },
};

function makeRng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

export function CosmicElementOrb({
  element,
  size = 200,
}: CosmicElementOrbProps) {
  const uid = useId().replace(/:/g, "");
  const palette = PALETTES[element];
  const { core, inner, mid, deep, voidC, arm, dust, glow, starTint } = palette;

  const stars = useMemo(() => {
    const seed = element.charCodeAt(0) * 17 + element.length;
    const r = makeRng(seed);
    const out: { x: number; y: number; sz: number; op: number }[] = [];
    for (let i = 0; i < 90; i += 1) {
      const ang = r() * Math.PI * 2;
      const rad = Math.sqrt(r()) * 76;
      out.push({
        x: 100 + Math.cos(ang) * rad,
        y: 100 + Math.sin(ang) * rad,
        sz: r() < 0.85 ? 0.5 + r() * 0.7 : 1.0 + r() * 0.8,
        op: 0.45 + r() * 0.55,
      });
    }
    return out;
  }, [element]);

  const turbSeed = element.charCodeAt(0);

  return (
    <svg
      width={size}
      height={size * 1.18}
      viewBox="0 0 200 236"
      aria-hidden="true"
      style={{ display: "block" }}
    >
      <defs>
        <radialGradient id={`base-${uid}`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor={deep} />
          <stop offset="55%" stopColor={voidC} />
          <stop offset="100%" stopColor="#000" />
        </radialGradient>
        <radialGradient id={`rim-${uid}`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="62%" stopColor="#000" stopOpacity="0" />
          <stop offset="88%" stopColor="#000" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#000" stopOpacity="0.95" />
        </radialGradient>
        <radialGradient id={`core-${uid}`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor={core} />
          <stop offset="22%" stopColor={inner} stopOpacity="0.85" />
          <stop offset="55%" stopColor={mid} stopOpacity="0.35" />
          <stop offset="100%" stopColor={mid} stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`armGrad-${uid}`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor={glow} stopOpacity="0.85" />
          <stop offset="60%" stopColor={arm} stopOpacity="0.6" />
          <stop offset="100%" stopColor={dust} stopOpacity="0" />
        </radialGradient>
        <filter id={`neb-${uid}`} x="-15%" y="-15%" width="130%" height="130%">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.018"
            numOctaves={3}
            seed={turbSeed}
          />
          <feDisplacementMap in="SourceGraphic" scale="22" />
          <feGaussianBlur stdDeviation="1.4" />
        </filter>
        <filter id={`gas-${uid}`} x="-20%" y="-20%" width="140%" height="140%">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.04"
            numOctaves={2}
            seed={turbSeed + 11}
          />
          <feDisplacementMap in="SourceGraphic" scale="14" />
          <feGaussianBlur stdDeviation="3" />
        </filter>
        <filter id={`glow-${uid}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.2" />
        </filter>
        <filter
          id={`spike-${uid}`}
          x="-50%"
          y="-50%"
          width="200%"
          height="200%"
        >
          <feGaussianBlur stdDeviation="0.6" />
        </filter>
        <radialGradient id={`gloss-${uid}`} cx="0.4" cy="0.22" r="0.32">
          <stop offset="0%" stopColor="#fff" stopOpacity="0.55" />
          <stop offset="55%" stopColor="#fff" stopOpacity="0.12" />
          <stop offset="100%" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`spec-${uid}`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor="#fff" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`bounce-${uid}`} cx="0.5" cy="1" r="0.6">
          <stop offset="0%" stopColor={glow} stopOpacity="0.18" />
          <stop offset="100%" stopColor={glow} stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`aura-${uid}`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="55%" stopColor={glow} stopOpacity="0" />
          <stop offset="72%" stopColor={glow} stopOpacity="0.18" />
          <stop offset="100%" stopColor={glow} stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`shadow-${uid}`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor="#000" stopOpacity="0.6" />
          <stop offset="60%" stopColor="#000" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#000" stopOpacity="0" />
        </radialGradient>
        <clipPath id={`clip-${uid}`}>
          <circle cx="100" cy="100" r="86" />
        </clipPath>
      </defs>

      <circle cx="100" cy="100" r="110" fill={`url(#aura-${uid})`} />
      <ellipse cx="100" cy="212" rx="74" ry="9" fill={`url(#shadow-${uid})`} />
      <circle cx="100" cy="100" r="86" fill={`url(#base-${uid})`} />

      <g clipPath={`url(#clip-${uid})`}>
        <g filter={`url(#gas-${uid})`} opacity="0.7">
          <ellipse cx="92" cy="92" rx="70" ry="58" fill={dust} opacity="0.55" />
          <ellipse
            cx="112"
            cy="116"
            rx="62"
            ry="52"
            fill={mid}
            opacity="0.45"
          />
          <ellipse
            cx="100"
            cy="100"
            rx="48"
            ry="42"
            fill={inner}
            opacity="0.35"
          />
        </g>

        <g
          filter={`url(#neb-${uid})`}
          opacity="0.95"
          style={{ mixBlendMode: "screen" }}
        >
          <path
            d="M 100 100 m -60 0 a 60 30 -25 1 1 120 0 a 60 30 -25 1 1 -120 0 Z"
            fill="none"
            stroke={`url(#armGrad-${uid})`}
            strokeWidth="22"
            opacity="0.85"
          />
          <path
            d="M 100 100 m -42 0 a 42 22 35 1 1 84 0 a 42 22 35 1 1 -84 0 Z"
            fill="none"
            stroke={`url(#armGrad-${uid})`}
            strokeWidth="14"
            opacity="0.75"
          />
          <path
            d="M 36 88 Q 100 40 168 96 Q 130 130 100 100"
            fill="none"
            stroke={arm}
            strokeWidth="3"
            opacity="0.55"
            strokeLinecap="round"
          />
          <path
            d="M 30 122 Q 90 170 168 130"
            fill="none"
            stroke={glow}
            strokeWidth="2"
            opacity="0.5"
            strokeLinecap="round"
          />
        </g>

        <g filter={`url(#neb-${uid})`} opacity="0.9">
          <path
            d="M 100 100 m -55 -8 a 55 14 -18 1 1 110 0 a 55 14 -18 1 1 -110 0 Z"
            fill="#000"
            opacity="0.45"
          />
        </g>

        <circle
          cx="100"
          cy="100"
          r="60"
          fill={`url(#core-${uid})`}
          opacity="0.9"
        />
        <circle
          cx="100"
          cy="100"
          r="8"
          fill={core}
          filter={`url(#glow-${uid})`}
          opacity="0.85"
        />
        <circle cx="100" cy="100" r="3" fill="#fff" opacity="0.95" />

        <g>
          {stars.map((s, i) => (
            <circle
              key={i}
              cx={s.x}
              cy={s.y}
              r={s.sz}
              fill={s.sz > 1.0 ? "#fff" : starTint}
              opacity={s.op}
            />
          ))}
        </g>

        {[
          { x: 72, y: 76, sz: 1.6 },
          { x: 134, y: 88, sz: 1.4 },
          { x: 88, y: 134, sz: 1.5 },
          { x: 132, y: 126, sz: 1.2 },
          { x: 118, y: 64, sz: 1.0 },
        ].map((s, i) => (
          <g key={`bs-${i}`} filter={`url(#spike-${uid})`}>
            <circle
              cx={s.x}
              cy={s.y}
              r={s.sz + 1.2}
              fill={core}
              opacity="0.5"
            />
            <circle cx={s.x} cy={s.y} r={s.sz} fill="#fff" />
            <line
              x1={s.x - 6}
              y1={s.y}
              x2={s.x + 6}
              y2={s.y}
              stroke="#fff"
              strokeWidth="0.5"
              opacity="0.7"
            />
            <line
              x1={s.x}
              y1={s.y - 6}
              x2={s.x}
              y2={s.y + 6}
              stroke="#fff"
              strokeWidth="0.5"
              opacity="0.7"
            />
          </g>
        ))}

        <ellipse
          cx="100"
          cy="100"
          rx="86"
          ry="86"
          fill={mid}
          opacity="0.06"
          style={{ mixBlendMode: "screen" }}
        />
        <circle cx="100" cy="100" r="86" fill={`url(#bounce-${uid})`} />
      </g>

      <circle cx="100" cy="100" r="86" fill={`url(#rim-${uid})`} />
      <ellipse cx="78" cy="62" rx="42" ry="32" fill={`url(#gloss-${uid})`} />
      <ellipse
        cx="72"
        cy="56"
        rx="9"
        ry="5.5"
        fill={`url(#spec-${uid})`}
        transform="rotate(-25 72 56)"
      />
      <ellipse
        cx="64"
        cy="124"
        rx="14"
        ry="5"
        fill="#fff"
        opacity="0.05"
        transform="rotate(-30 64 124)"
      />
      <circle
        cx="100"
        cy="100"
        r="86"
        fill="none"
        stroke="#000"
        strokeOpacity="0.5"
        strokeWidth="0.8"
      />
    </svg>
  );
}
