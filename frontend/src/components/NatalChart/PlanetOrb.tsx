import { useId } from "react";

type Frame = "ring" | "glow";

interface PlanetOrbProps {
  id: string;
  size?: number;
  frame?: Frame;
  showGlyph?: boolean;
}

function CosmicDisc({ uid }: { uid: string }) {
  return (
    <>
      <defs>
        <radialGradient id={`disc-${uid}`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#15102a" />
          <stop offset="0.7" stopColor="#0a0626" />
          <stop offset="1" stopColor="#06031a" />
        </radialGradient>
        <radialGradient id={`nebula-${uid}`} cx="0.3" cy="0.7" r="0.6">
          <stop offset="0" stopColor="#3a1d6a" stopOpacity="0.45" />
          <stop offset="1" stopColor="#3a1d6a" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="50" cy="50" r="49" fill={`url(#disc-${uid})`} />
      <circle cx="50" cy="50" r="49" fill={`url(#nebula-${uid})`} />
      <g fill="#fff">
        <circle cx="22" cy="20" r="0.5" opacity="0.85" />
        <circle cx="78" cy="24" r="0.4" opacity="0.7" />
        <circle cx="84" cy="62" r="0.5" opacity="0.8" />
        <circle cx="18" cy="68" r="0.4" opacity="0.7" />
        <circle cx="14" cy="44" r="0.3" opacity="0.55" />
        <circle cx="88" cy="40" r="0.35" opacity="0.55" />
        <circle cx="32" cy="84" r="0.3" opacity="0.55" />
        <circle cx="68" cy="82" r="0.4" opacity="0.65" />
      </g>
    </>
  );
}

function RingFrame() {
  return (
    <g>
      <circle
        cx="50"
        cy="50"
        r="48"
        fill="none"
        stroke="rgba(212,178,84,0.5)"
        strokeWidth="0.6"
      />
      <circle
        cx="50"
        cy="50"
        r="46"
        fill="none"
        stroke="rgba(212,178,84,0.25)"
        strokeWidth="0.4"
        strokeDasharray="0.6 2.4"
      />
    </g>
  );
}

export function PlanetOrb({
  id,
  size = 88,
  frame = "ring",
  showGlyph = true,
}: PlanetOrbProps) {
  const uid = useId().replace(/:/g, "");
  const ring = frame === "ring" ? <RingFrame /> : null;

  if (id === "sun") {
    return (
      <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
        <CosmicDisc uid={uid} />
        <defs>
          <radialGradient id={`s-halo-${uid}`} cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stopColor="#ffd067" stopOpacity="0.9" />
            <stop offset="0.35" stopColor="#ff8a18" stopOpacity="0.45" />
            <stop offset="0.75" stopColor="#a02a04" stopOpacity="0.18" />
            <stop offset="1" stopColor="#a02a04" stopOpacity="0" />
          </radialGradient>
          <radialGradient id={`s-body-${uid}`} cx="0.4" cy="0.36" r="0.65">
            <stop offset="0" stopColor="#fff5c0" />
            <stop offset="0.3" stopColor="#ffd067" />
            <stop offset="0.65" stopColor="#ff7a18" />
            <stop offset="0.92" stopColor="#a02a04" />
            <stop offset="1" stopColor="#5a1304" />
          </radialGradient>
          <radialGradient id={`s-spec-${uid}`} cx="0.38" cy="0.32" r="0.35">
            <stop offset="0" stopColor="#fff" stopOpacity="0.9" />
            <stop offset="1" stopColor="#fff" stopOpacity="0" />
          </radialGradient>
          <radialGradient id={`s-core-${uid}`} cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stopColor="#fff" stopOpacity="0.95" />
            <stop offset="0.5" stopColor="#ffe8a0" stopOpacity="0.5" />
            <stop offset="1" stopColor="#ffe8a0" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="50" cy="50" r="44" fill={`url(#s-halo-${uid})`} />
        <g stroke="#ffd067" strokeLinecap="round" opacity="0.75">
          {Array.from({ length: 24 }).map((_, i) => {
            const a = (i * 15 * Math.PI) / 180;
            const r1 = 32;
            const r2 = 32 + (i % 2 === 0 ? 8 : 4);
            return (
              <line
                key={i}
                x1={50 + Math.cos(a) * r1}
                y1={50 + Math.sin(a) * r1}
                x2={50 + Math.cos(a) * r2}
                y2={50 + Math.sin(a) * r2}
                strokeWidth={i % 2 === 0 ? 0.7 : 0.4}
                strokeOpacity={i % 2 === 0 ? 0.85 : 0.5}
              />
            );
          })}
        </g>
        <circle cx="50" cy="50" r="22" fill={`url(#s-body-${uid})`} />
        <g fill="#a02a04" opacity="0.35">
          <ellipse
            cx="44"
            cy="56"
            rx="6"
            ry="1.3"
            transform="rotate(20 44 56)"
          />
          <ellipse
            cx="56"
            cy="48"
            rx="4"
            ry="1"
            transform="rotate(-10 56 48)"
          />
          <ellipse cx="50" cy="62" rx="3" ry="0.8" />
        </g>
        <circle cx="50" cy="50" r="10" fill={`url(#s-core-${uid})`} />
        <ellipse
          cx="44"
          cy="42"
          rx="6"
          ry="9"
          fill={`url(#s-spec-${uid})`}
          transform="rotate(-25 44 42)"
          opacity="0.85"
        />
        {ring}
        {showGlyph && (
          <g opacity="0.95">
            <circle
              cx="50"
              cy="50"
              r="2.2"
              fill="none"
              stroke="#fff"
              strokeWidth="0.9"
            />
            <circle cx="50" cy="50" r="0.9" fill="#fff" />
          </g>
        )}
      </svg>
    );
  }

  if (id === "moon") {
    return (
      <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
        <CosmicDisc uid={uid} />
        <defs>
          <radialGradient id={`m-halo-${uid}`} cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stopColor="#aa96f0" stopOpacity="0.55" />
            <stop offset="0.5" stopColor="#5a3fa0" stopOpacity="0.18" />
            <stop offset="1" stopColor="#5a3fa0" stopOpacity="0" />
          </radialGradient>
          <radialGradient id={`m-body-${uid}`} cx="0.32" cy="0.28" r="0.85">
            <stop offset="0" stopColor="#f6f0ff" />
            <stop offset="0.35" stopColor="#c5b3ff" />
            <stop offset="0.7" stopColor="#5a3fa0" />
            <stop offset="1" stopColor="#1f0e44" />
          </radialGradient>
          <radialGradient id={`m-shadow-${uid}`} cx="0.7" cy="0.55" r="0.6">
            <stop offset="0" stopColor="#1a0d3a" stopOpacity="0" />
            <stop offset="0.55" stopColor="#0a0426" stopOpacity="0.92" />
            <stop offset="1" stopColor="#000" />
          </radialGradient>
        </defs>
        <circle cx="50" cy="50" r="42" fill={`url(#m-halo-${uid})`} />
        <circle cx="50" cy="50" r="26" fill={`url(#m-body-${uid})`} />
        <circle cx="56" cy="50" r="25" fill={`url(#m-shadow-${uid})`} />
        <path
          d="M50 26 A 24 24 0 0 0 50 74"
          stroke="rgba(255,255,255,0.4)"
          strokeWidth="0.7"
          fill="none"
        />
        <g fill="rgba(90,63,160,0.6)">
          <ellipse cx="40" cy="42" rx="3.2" ry="2.4" />
          <ellipse cx="36" cy="54" rx="2.2" ry="1.6" />
          <ellipse cx="44" cy="60" rx="1.6" ry="1.2" />
          <ellipse cx="32" cy="46" rx="1.0" ry="0.8" />
          <ellipse cx="48" cy="36" rx="1.2" ry="0.9" />
        </g>
        <ellipse
          cx="36"
          cy="38"
          rx="3"
          ry="6"
          fill="#fff"
          opacity="0.32"
          transform="rotate(-25 36 38)"
        />
        <ellipse
          cx="35"
          cy="36"
          rx="0.9"
          ry="2"
          fill="#fff"
          opacity="0.85"
          transform="rotate(-25 35 36)"
        />
        <g fill="#fff">
          <circle cx="76" cy="32" r="0.7" opacity="0.95" />
          <circle cx="80" cy="38" r="0.4" opacity="0.6" />
          <circle cx="22" cy="74" r="0.55" opacity="0.85" />
        </g>
        {ring}
      </svg>
    );
  }

  if (id === "mercury") {
    return (
      <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
        <CosmicDisc uid={uid} />
        <defs>
          <radialGradient id={`mc-halo-${uid}`} cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stopColor="#7cd6f5" stopOpacity="0.55" />
            <stop offset="0.55" stopColor="#1f6da0" stopOpacity="0.16" />
            <stop offset="1" stopColor="#1f6da0" stopOpacity="0" />
          </radialGradient>
          <radialGradient id={`mc-body-${uid}`} cx="0.36" cy="0.32" r="0.78">
            <stop offset="0" stopColor="#eafaff" />
            <stop offset="0.35" stopColor="#9be4ff" />
            <stop offset="0.65" stopColor="#3a8ec0" />
            <stop offset="0.92" stopColor="#103a5a" />
            <stop offset="1" stopColor="#06192e" />
          </radialGradient>
          <linearGradient id={`mc-band-${uid}`} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="rgba(255,255,255,0)" />
            <stop offset="0.5" stopColor="rgba(255,255,255,0.45)" />
            <stop offset="1" stopColor="rgba(255,255,255,0)" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="42" fill={`url(#mc-halo-${uid})`} />
        <ellipse
          cx="50"
          cy="50"
          rx="38"
          ry="11"
          fill="none"
          stroke="rgba(124,214,245,0.4)"
          strokeWidth="0.5"
          strokeDasharray="1.6 3"
          transform="rotate(-22 50 50)"
        />
        <circle cx="50" cy="50" r="26" fill={`url(#mc-body-${uid})`} />
        <g stroke={`url(#mc-band-${uid})`} strokeWidth="0.7" fill="none">
          <path d="M28 44 Q 50 38 72 46" />
          <path d="M27 56 Q 50 62 73 54" opacity="0.7" />
          <path d="M30 64 Q 50 70 70 62" opacity="0.5" />
        </g>
        <ellipse
          cx="40"
          cy="38"
          rx="5"
          ry="8"
          fill="#fff"
          opacity="0.4"
          transform="rotate(-25 40 38)"
        />
        <ellipse
          cx="40"
          cy="38"
          rx="1.6"
          ry="2.8"
          fill="#fff"
          opacity="0.95"
          transform="rotate(-25 40 38)"
        />
        {showGlyph && (
          <text
            x="50"
            y="56"
            fontFamily="Cormorant, Georgia, serif"
            fontSize="22"
            fontWeight="500"
            fill="rgba(255,255,255,0.92)"
            textAnchor="middle"
            style={{ filter: "drop-shadow(0 0 6px rgba(124,214,245,0.85))" }}
          >
            ☿
          </text>
        )}
        {ring}
      </svg>
    );
  }

  if (id === "venus") {
    return (
      <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
        <CosmicDisc uid={uid} />
        <defs>
          <radialGradient id={`v-halo-${uid}`} cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stopColor="#ec86c4" stopOpacity="0.55" />
            <stop offset="0.55" stopColor="#a03a78" stopOpacity="0.18" />
            <stop offset="1" stopColor="#a03a78" stopOpacity="0" />
          </radialGradient>
          <radialGradient id={`v-body-${uid}`} cx="0.36" cy="0.32" r="0.78">
            <stop offset="0" stopColor="#fff0fa" />
            <stop offset="0.32" stopColor="#f7b8dc" />
            <stop offset="0.6" stopColor="#cc4f96" />
            <stop offset="0.9" stopColor="#5d1844" />
            <stop offset="1" stopColor="#1f0814" />
          </radialGradient>
          <linearGradient id={`v-cloud-${uid}`} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="rgba(255,235,250,0)" />
            <stop offset="0.5" stopColor="rgba(255,235,250,0.55)" />
            <stop offset="1" stopColor="rgba(255,235,250,0)" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="42" fill={`url(#v-halo-${uid})`} />
        <circle cx="50" cy="50" r="26" fill={`url(#v-body-${uid})`} />
        <g stroke={`url(#v-cloud-${uid})`} strokeWidth="0.8" fill="none">
          <path d="M26 42 Q 38 36 50 42 T 74 44" />
          <path d="M26 50 Q 38 56 52 50 T 74 52" />
          <path d="M28 58 Q 42 64 54 58 T 72 62" opacity="0.7" />
          <path d="M30 64 Q 44 70 56 64 T 70 68" opacity="0.5" />
        </g>
        <ellipse
          cx="40"
          cy="38"
          rx="5"
          ry="8"
          fill="#fff"
          opacity="0.32"
          transform="rotate(-25 40 38)"
        />
        <ellipse
          cx="40"
          cy="38"
          rx="1.5"
          ry="2.6"
          fill="#fff"
          opacity="0.95"
          transform="rotate(-25 40 38)"
        />
        {showGlyph && (
          <text
            x="50"
            y="58"
            fontFamily="Cormorant, Georgia, serif"
            fontSize="22"
            fontWeight="500"
            fill="rgba(255,255,255,0.92)"
            textAnchor="middle"
            style={{ filter: "drop-shadow(0 0 8px rgba(236,134,196,0.95))" }}
          >
            ♀
          </text>
        )}
        {ring}
      </svg>
    );
  }

  if (id === "mars") {
    return (
      <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
        <CosmicDisc uid={uid} />
        <defs>
          <radialGradient id={`mr-halo-${uid}`} cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stopColor="#ec5c46" stopOpacity="0.55" />
            <stop offset="0.55" stopColor="#7a1d0a" stopOpacity="0.18" />
            <stop offset="1" stopColor="#7a1d0a" stopOpacity="0" />
          </radialGradient>
          <radialGradient id={`mr-body-${uid}`} cx="0.36" cy="0.32" r="0.78">
            <stop offset="0" stopColor="#ffd6b0" />
            <stop offset="0.3" stopColor="#ff7a52" />
            <stop offset="0.65" stopColor="#a02a18" />
            <stop offset="0.92" stopColor="#3d0a04" />
            <stop offset="1" stopColor="#1a0402" />
          </radialGradient>
        </defs>
        <circle cx="50" cy="50" r="42" fill={`url(#mr-halo-${uid})`} />
        <circle cx="50" cy="50" r="26" fill={`url(#mr-body-${uid})`} />
        <g fill="rgba(122,30,18,0.62)">
          <ellipse
            cx="42"
            cy="46"
            rx="6"
            ry="3"
            transform="rotate(-15 42 46)"
          />
          <ellipse
            cx="58"
            cy="56"
            rx="4.5"
            ry="2"
            transform="rotate(20 58 56)"
          />
          <ellipse
            cx="46"
            cy="62"
            rx="3"
            ry="1.4"
            transform="rotate(-30 46 62)"
          />
          <ellipse
            cx="58"
            cy="42"
            rx="2.6"
            ry="1.2"
            transform="rotate(15 58 42)"
          />
          <ellipse
            cx="38"
            cy="56"
            rx="1.6"
            ry="1"
            transform="rotate(40 38 56)"
          />
        </g>
        <ellipse
          cx="50"
          cy="28"
          rx="6"
          ry="1.6"
          fill="rgba(255,225,200,0.65)"
        />
        <ellipse
          cx="50"
          cy="72"
          rx="4"
          ry="1.2"
          fill="rgba(255,225,200,0.45)"
        />
        <ellipse
          cx="40"
          cy="38"
          rx="5"
          ry="7"
          fill="#fff"
          opacity="0.25"
          transform="rotate(-25 40 38)"
        />
        <ellipse
          cx="40"
          cy="38"
          rx="1.5"
          ry="2.4"
          fill="#fff"
          opacity="0.85"
          transform="rotate(-25 40 38)"
        />
        {showGlyph && (
          <text
            x="50"
            y="58"
            fontFamily="Cormorant, Georgia, serif"
            fontSize="22"
            fontWeight="500"
            fill="rgba(255,255,255,0.92)"
            textAnchor="middle"
            style={{ filter: "drop-shadow(0 0 8px rgba(236,92,70,0.95))" }}
          >
            ♂
          </text>
        )}
        {ring}
      </svg>
    );
  }

  if (id === "jupiter") {
    const clip = `j-clip-${uid}`;
    return (
      <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
        <CosmicDisc uid={uid} />
        <defs>
          <radialGradient id={`j-halo-${uid}`} cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stopColor="#e6b66e" stopOpacity="0.55" />
            <stop offset="0.55" stopColor="#7a4a18" stopOpacity="0.18" />
            <stop offset="1" stopColor="#7a4a18" stopOpacity="0" />
          </radialGradient>
          <radialGradient id={`j-body-${uid}`} cx="0.36" cy="0.32" r="0.78">
            <stop offset="0" stopColor="#fff5d4" />
            <stop offset="0.32" stopColor="#f0c98a" />
            <stop offset="0.65" stopColor="#a07238" />
            <stop offset="0.92" stopColor="#3d2208" />
            <stop offset="1" stopColor="#1a0e02" />
          </radialGradient>
          <clipPath id={clip}>
            <circle cx="50" cy="50" r="26" />
          </clipPath>
        </defs>
        <circle cx="50" cy="50" r="42" fill={`url(#j-halo-${uid})`} />
        <circle cx="50" cy="50" r="26" fill={`url(#j-body-${uid})`} />
        <g clipPath={`url(#${clip})`}>
          <rect
            x="22"
            y="34"
            width="56"
            height="2.2"
            fill="rgba(120,70,20,0.5)"
          />
          <rect
            x="22"
            y="40"
            width="56"
            height="2.6"
            fill="rgba(255,224,160,0.22)"
          />
          <rect
            x="22"
            y="46"
            width="56"
            height="2.0"
            fill="rgba(120,70,20,0.55)"
          />
          <rect
            x="22"
            y="52"
            width="56"
            height="2.6"
            fill="rgba(255,224,160,0.25)"
          />
          <rect
            x="22"
            y="58"
            width="56"
            height="2.0"
            fill="rgba(120,70,20,0.5)"
          />
          <rect
            x="22"
            y="64"
            width="56"
            height="1.6"
            fill="rgba(255,224,160,0.18)"
          />
          <ellipse cx="56" cy="54" rx="3.6" ry="1.8" fill="#a83a18" />
          <ellipse
            cx="56"
            cy="54"
            rx="2.2"
            ry="1.0"
            fill="#ec5c2a"
            opacity="0.85"
          />
        </g>
        <ellipse
          cx="40"
          cy="38"
          rx="5"
          ry="8"
          fill="#fff"
          opacity="0.3"
          transform="rotate(-25 40 38)"
        />
        <ellipse
          cx="40"
          cy="38"
          rx="1.5"
          ry="2.6"
          fill="#fff"
          opacity="0.9"
          transform="rotate(-25 40 38)"
        />
        {showGlyph && (
          <text
            x="50"
            y="58"
            fontFamily="Cormorant, Georgia, serif"
            fontSize="22"
            fontWeight="500"
            fill="rgba(255,255,255,0.92)"
            textAnchor="middle"
            style={{ filter: "drop-shadow(0 0 8px rgba(230,182,110,0.95))" }}
          >
            ♃
          </text>
        )}
        {ring}
      </svg>
    );
  }

  if (id === "saturn") {
    return (
      <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
        <CosmicDisc uid={uid} />
        <defs>
          <radialGradient id={`sa-halo-${uid}`} cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stopColor="#a086e6" stopOpacity="0.5" />
            <stop offset="0.55" stopColor="#3d2a78" stopOpacity="0.18" />
            <stop offset="1" stopColor="#3d2a78" stopOpacity="0" />
          </radialGradient>
          <radialGradient id={`sa-body-${uid}`} cx="0.36" cy="0.32" r="0.78">
            <stop offset="0" stopColor="#ece2ff" />
            <stop offset="0.32" stopColor="#b6a4f5" />
            <stop offset="0.65" stopColor="#553d9e" />
            <stop offset="0.92" stopColor="#1f1244" />
            <stop offset="1" stopColor="#0a0426" />
          </radialGradient>
          <linearGradient id={`sa-ring-${uid}`} x1="0" y1="0.5" x2="1" y2="0.5">
            <stop offset="0" stopColor="rgba(220,210,255,0.05)" />
            <stop offset="0.2" stopColor="rgba(240,212,138,0.6)" />
            <stop offset="0.5" stopColor="rgba(255,235,180,0.95)" />
            <stop offset="0.8" stopColor="rgba(240,212,138,0.6)" />
            <stop offset="1" stopColor="rgba(220,210,255,0.05)" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="42" fill={`url(#sa-halo-${uid})`} />
        <g transform="rotate(-22 50 50)">
          <path
            d="M 50 50 m -42 0 a 42 9 0 0 1 84 0"
            fill="none"
            stroke={`url(#sa-ring-${uid})`}
            strokeWidth="2.2"
            opacity="0.9"
          />
          <path
            d="M 50 50 m -36 0 a 36 7 0 0 1 72 0"
            fill="none"
            stroke="rgba(255,235,180,0.45)"
            strokeWidth="0.8"
          />
        </g>
        <circle cx="50" cy="50" r="22" fill={`url(#sa-body-${uid})`} />
        <g stroke="rgba(255,255,255,0.18)" strokeWidth="0.5" fill="none">
          <path d="M30 46 Q 50 42 70 46" />
          <path d="M30 54 Q 50 58 70 54" opacity="0.7" />
        </g>
        <g transform="rotate(-22 50 50)">
          <path
            d="M 50 50 m -42 0 a 42 9 0 0 0 84 0"
            fill="none"
            stroke={`url(#sa-ring-${uid})`}
            strokeWidth="2.6"
            opacity="0.95"
          />
          <path
            d="M 50 50 m -36 0 a 36 7 0 0 0 72 0"
            fill="none"
            stroke="rgba(255,235,180,0.55)"
            strokeWidth="0.8"
          />
        </g>
        <ellipse
          cx="42"
          cy="40"
          rx="3.5"
          ry="5.5"
          fill="#fff"
          opacity="0.25"
          transform="rotate(-25 42 40)"
        />
        <ellipse
          cx="42"
          cy="40"
          rx="1.2"
          ry="1.8"
          fill="#fff"
          opacity="0.85"
          transform="rotate(-25 42 40)"
        />
        {showGlyph && (
          <text
            x="50"
            y="55"
            fontFamily="Cormorant, Georgia, serif"
            fontSize="18"
            fontWeight="500"
            fill="rgba(255,255,255,0.92)"
            textAnchor="middle"
            style={{ filter: "drop-shadow(0 0 8px rgba(160,134,230,0.95))" }}
          >
            ♄
          </text>
        )}
        {ring}
      </svg>
    );
  }

  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
      <CosmicDisc uid={uid} />
      <circle cx="50" cy="50" r="22" fill="rgba(212,178,84,0.32)" />
      {ring}
    </svg>
  );
}
