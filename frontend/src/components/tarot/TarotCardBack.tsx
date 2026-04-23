type Props = { width?: number | string; height?: number | string }

/**
 * Tarot card back — "Eye of Providence" (indigo + gold).
 * Source: natal-chart-app CardBackVariants.tsx (V1).
 */
export function TarotCardBack({ width = '100%', height = '100%' }: Props) {
  return (
    <svg
      viewBox="0 0 88 150"
      width={width}
      height={height}
      preserveAspectRatio="xMidYMid slice"
      xmlns="http://www.w3.org/2000/svg"
      style={{ display: 'block' }}
    >
      <defs>
        <radialGradient id="v1bg" cx="50%" cy="42%" r="65%">
          <stop offset="0%" stopColor="#1e1260" />
          <stop offset="55%" stopColor="#0d0838" />
          <stop offset="100%" stopColor="#030210" />
        </radialGradient>
        <linearGradient id="v1g" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#e8c862" />
          <stop offset="40%" stopColor="#c9a84c" />
          <stop offset="100%" stopColor="#a07830" />
        </linearGradient>
        <radialGradient id="v1eye" cx="50%" cy="38%" r="55%">
          <stop offset="0%" stopColor="#6b3fc0" />
          <stop offset="60%" stopColor="#2e1460" />
          <stop offset="100%" stopColor="#0e0430" />
        </radialGradient>
      </defs>
      <rect width="88" height="150" rx="5" fill="url(#v1bg)" />
      <rect x="2" y="2" width="84" height="146" rx="4" fill="none" stroke="url(#v1g)" strokeWidth="1.2" />
      <rect x="5.5" y="5.5" width="77" height="139" rx="2.5" fill="none" stroke="url(#v1g)" strokeWidth="0.45" strokeOpacity="0.55" />
      {/* Corner flourishes */}
      <g stroke="url(#v1g)" strokeWidth="0.8" fill="url(#v1g)" opacity="0.85">
        {(
          [
            [5.5, 5.5, 14, 5.5, 5.5, 18],
            [82.5, 5.5, 74, 5.5, 82.5, 18],
            [5.5, 144.5, 14, 144.5, 5.5, 132],
            [82.5, 144.5, 74, 144.5, 82.5, 132],
          ] as number[][]
        ).map(([cx, cy, x1, y1, x2, y2], i) => (
          <g key={i}>
            <line x1={cx} y1={cy} x2={x1} y2={y1} />
            <line x1={cx} y1={cy} x2={x2} y2={y2} />
            <circle cx={cx} cy={cy} r="1.5" />
          </g>
        ))}
      </g>
      <g stroke="url(#v1g)" strokeWidth="0.5" opacity="0.5">
        <line x1="18" y1="19" x2="70" y2="19" />
        <line x1="18" y1="131" x2="70" y2="131" />
      </g>
      {/* Mandala ring */}
      <circle cx="44" cy="75" r="28" fill="none" stroke="url(#v1g)" strokeWidth="0.4" strokeDasharray="3 5" opacity="0.45" />
      <circle cx="44" cy="75" r="22" fill="none" stroke="url(#v1g)" strokeWidth="0.3" strokeDasharray="1 3" opacity="0.3" />
      {/* Eye of Providence triangle */}
      <polygon points="44,36 20,90 68,90" fill="none" stroke="url(#v1g)" strokeWidth="1" opacity="0.9" />
      {/* Rays */}
      <g stroke="url(#v1g)" strokeWidth="0.5" opacity="0.4">
        <line x1="44" y1="34" x2="44" y2="24" />
        <line x1="44" y1="34" x2="36" y2="25" />
        <line x1="44" y1="34" x2="52" y2="25" />
        <line x1="20" y1="90" x2="10" y2="98" />
        <line x1="68" y1="90" x2="78" y2="98" />
        <line x1="44" y1="90" x2="44" y2="100" />
      </g>
      {/* Eye */}
      <ellipse cx="44" cy="73" rx="10" ry="7" fill="url(#v1eye)" stroke="url(#v1g)" strokeWidth="0.8" />
      <circle cx="44" cy="73" r="4.5" fill="#0a041e" />
      <circle cx="44" cy="73" r="2.5" fill="#6b3fc0" opacity="0.8" />
      <circle cx="41.5" cy="71.2" r="1" fill="white" opacity="0.7" />
      {/* Stars */}
      <g fill="url(#v1g)">
        <circle cx="18" cy="30" r="0.9" opacity="0.6" />
        <circle cx="70" cy="27" r="0.9" opacity="0.6" />
        <circle cx="12" cy="108" r="0.7" opacity="0.5" />
        <circle cx="76" cy="115" r="0.7" opacity="0.5" />
        <circle cx="44" cy="24" r="1.2" opacity="0.75" />
        <circle cx="44" cy="126" r="1.2" opacity="0.75" />
        <circle cx="9" cy="75" r="0.9" opacity="0.5" />
        <circle cx="79" cy="75" r="0.9" opacity="0.5" />
      </g>
    </svg>
  )
}
