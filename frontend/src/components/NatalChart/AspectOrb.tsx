import { useId, useMemo } from "react";

interface AspectOrbProps {
  type: string;
  symbol: string;
  color: string;
  size?: number;
}

function makeRng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

export function AspectOrb({ type, symbol, color, size = 96 }: AspectOrbProps) {
  const uid = useId().replace(/:/g, "");

  const stars = useMemo(() => {
    const seed = type.charCodeAt(0) * 13 + type.length * 7 + 11;
    const r = makeRng(seed);
    const out: {
      x: number;
      y: number;
      sz: number;
      op: number;
      tint: boolean;
    }[] = [];
    for (let i = 0; i < 30; i += 1) {
      const ang = r() * Math.PI * 2;
      const rad = 8 + Math.sqrt(r()) * 36;
      out.push({
        x: 50 + Math.cos(ang) * rad,
        y: 50 + Math.sin(ang) * rad,
        sz: r() < 0.8 ? 0.3 + r() * 0.5 : 0.7 + r() * 0.5,
        op: 0.45 + r() * 0.5,
        tint: r() > 0.6,
      });
    }
    return out;
  }, [type]);

  const dust = useMemo(() => {
    const seed = type.charCodeAt(0) * 5 + 31;
    const r = makeRng(seed);
    const out: { x: number; y: number; sz: number; op: number }[] = [];
    for (let i = 0; i < 16; i += 1) {
      const ang = r() * Math.PI * 2;
      const rad = 30 + r() * 17;
      out.push({
        x: 50 + Math.cos(ang) * rad,
        y: 50 + Math.sin(ang) * rad,
        sz: 0.35 + r() * 0.7,
        op: 0.35 + r() * 0.5,
      });
    }
    return out;
  }, [type]);

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      aria-hidden="true"
      style={{ display: "block" }}
    >
      <defs>
        <radialGradient id={`a-disc-${uid}`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#1a1238" />
          <stop offset="0.7" stopColor="#0a0626" />
          <stop offset="1" stopColor="#06031a" />
        </radialGradient>
        <radialGradient id={`a-halo-${uid}`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor={color} stopOpacity="0.6" />
          <stop offset="0.45" stopColor={color} stopOpacity="0.2" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`a-aura-${uid}`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0.55" stopColor={color} stopOpacity="0" />
          <stop offset="0.85" stopColor={color} stopOpacity="0.2" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </radialGradient>
        <filter
          id={`a-glow-${uid}`}
          x="-50%"
          y="-50%"
          width="200%"
          height="200%"
        >
          <feGaussianBlur stdDeviation="1.6" />
        </filter>
      </defs>

      <circle cx="50" cy="50" r="50" fill={`url(#a-aura-${uid})`} />
      <circle cx="50" cy="50" r="44" fill={`url(#a-disc-${uid})`} />
      <circle cx="50" cy="50" r="40" fill={`url(#a-halo-${uid})`} />

      <g>
        {stars.map((s, i) => (
          <circle
            key={i}
            cx={s.x}
            cy={s.y}
            r={s.sz}
            fill={s.tint ? color : "#ffffff"}
            opacity={s.op}
          />
        ))}
      </g>

      <g fill={color}>
        {dust.map((d, i) => (
          <circle key={`d-${i}`} cx={d.x} cy={d.y} r={d.sz} opacity={d.op} />
        ))}
      </g>

      <circle
        cx="50"
        cy="50"
        r="44"
        fill="none"
        stroke={color}
        strokeOpacity="0.6"
        strokeWidth="0.7"
      />
      <circle
        cx="50"
        cy="50"
        r="40"
        fill="none"
        stroke={color}
        strokeOpacity="0.22"
        strokeWidth="0.4"
        strokeDasharray="0.8 2.2"
      />

      <text
        x="50"
        y="50"
        fontFamily="Cormorant, Georgia, serif"
        fontSize="36"
        fontWeight="500"
        fill={color}
        textAnchor="middle"
        dominantBaseline="central"
        filter={`url(#a-glow-${uid})`}
        opacity="0.85"
      >
        {symbol}
      </text>
      <text
        x="50"
        y="50"
        fontFamily="Cormorant, Georgia, serif"
        fontSize="36"
        fontWeight="500"
        fill={color}
        textAnchor="middle"
        dominantBaseline="central"
      >
        {symbol}
      </text>
    </svg>
  );
}
