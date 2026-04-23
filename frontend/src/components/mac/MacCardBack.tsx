type Props = { width?: number; height?: number };

export function MacCardBack({ width = 220, height = 340 }: Props) {
  return (
    <svg viewBox="0 0 220 340" width={width} height={height} xmlns="http://www.w3.org/2000/svg" style={{ display: 'block' }}>
      <defs>
        <radialGradient id="mbg" cx="50%" cy="42%" r="72%">
          <stop offset="0%" stopColor="#261250" />
          <stop offset="55%" stopColor="#0d0830" />
          <stop offset="100%" stopColor="#02010c" />
        </radialGradient>
        <linearGradient id="mg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#e8c862" />
          <stop offset="45%" stopColor="#c9a84c" />
          <stop offset="100%" stopColor="#906030" />
        </linearGradient>
        <radialGradient id="mglass" cx="42%" cy="32%" r="70%">
          <stop offset="0%" stopColor="#d4b5ff" stopOpacity="0.55" />
          <stop offset="30%" stopColor="#6a48c0" stopOpacity="0.32" />
          <stop offset="65%" stopColor="#2a1260" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#04010e" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="mcore" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#fff6d4" stopOpacity="0.95" />
          <stop offset="40%" stopColor="#e8c862" stopOpacity="0.7" />
          <stop offset="100%" stopColor="#c9a84c" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* background */}
      <rect width="220" height="340" rx="10" fill="url(#mbg)" />

      {/* double border */}
      <rect x="5" y="5" width="210" height="330" rx="7" fill="none" stroke="url(#mg)" strokeWidth="1.4" />
      <rect x="10" y="10" width="200" height="320" rx="5" fill="none" stroke="url(#mg)" strokeWidth="0.45" strokeOpacity="0.55" />
      <rect x="13" y="13" width="194" height="314" rx="3.5" fill="none" stroke="url(#mg)" strokeWidth="0.3" strokeOpacity="0.3" />

      {/* corner ornaments */}
      <g stroke="url(#mg)" strokeWidth="0.9" fill="url(#mg)" opacity="0.9">
        {([[10,10,26,10,10,26],[210,10,194,10,210,26],[10,330,26,330,10,314],[210,330,194,330,210,314]] as number[][])
          .map(([cx, cy, x1, y1, x2, y2], i) => (
            <g key={i}>
              <line x1={cx} y1={cy} x2={x1} y2={y1} />
              <line x1={cx} y1={cy} x2={x2} y2={y2} />
              <circle cx={cx} cy={cy} r="1.8" />
              <circle cx={(cx + x1) / 2} cy={y1} r="0.6" />
              <circle cx={x2} cy={(cy + y2) / 2} r="0.6" />
            </g>
          ))}
      </g>

      {/* top flourish */}
      <g stroke="url(#mg)" strokeWidth="0.7" fill="none" opacity="0.8">
        <path d="M 50 36 Q 110 22, 170 36" />
        <path d="M 65 42 Q 110 32, 155 42" />
      </g>
      <g fill="url(#mg)" opacity="0.85">
        <circle cx="110" cy="28" r="2.5" />
        <circle cx="96" cy="34" r="1.2" />
        <circle cx="124" cy="34" r="1.2" />
        <circle cx="82" cy="40" r="0.9" />
        <circle cx="138" cy="40" r="0.9" />
      </g>

      {/* mirror frame — outer ornate oval */}
      <g>
        <ellipse cx="110" cy="160" rx="62" ry="92" fill="none" stroke="url(#mg)" strokeWidth="1.6" />
        <ellipse cx="110" cy="160" rx="58" ry="88" fill="none" stroke="url(#mg)" strokeWidth="0.45" strokeOpacity="0.6" />
      </g>

      {/* 12 decorative dots around the mirror */}
      <g fill="url(#mg)" opacity="0.75">
        {Array.from({ length: 12 }).map((_, i) => {
          const a = (i * Math.PI * 2) / 12 - Math.PI / 2;
          const x = 110 + 62 * Math.cos(a);
          const y = 160 + 92 * Math.sin(a);
          return <circle key={i} cx={x} cy={y} r={i % 3 === 0 ? 1.8 : 1} />;
        })}
      </g>

      {/* mirror glass */}
      <ellipse cx="110" cy="160" rx="54" ry="84" fill="url(#mglass)" />

      {/* glass highlight — soft crescent */}
      <ellipse cx="90" cy="118" rx="14" ry="26" fill="white" opacity="0.09" />
      <ellipse cx="84" cy="108" rx="4" ry="12" fill="white" opacity="0.22" />

      {/* reflection rays radiating from core */}
      <g stroke="url(#mg)" strokeWidth="0.4" opacity="0.4">
        {Array.from({ length: 16 }).map((_, i) => {
          const a = (i * Math.PI * 2) / 16 - Math.PI / 2;
          const r1 = 14;
          const r2 = i % 2 === 0 ? 36 : 28;
          return (
            <line key={i}
              x1={110 + r1 * Math.cos(a)} y1={160 + r1 * Math.sin(a)}
              x2={110 + r2 * Math.cos(a)} y2={160 + r2 * Math.sin(a)}
            />
          );
        })}
      </g>

      {/* concentric dashed ring inside mirror */}
      <ellipse cx="110" cy="160" rx="42" ry="66" fill="none" stroke="url(#mg)" strokeWidth="0.3" strokeDasharray="2 4" opacity="0.45" />
      <ellipse cx="110" cy="160" rx="26" ry="42" fill="none" stroke="url(#mg)" strokeWidth="0.3" strokeDasharray="1 3" opacity="0.35" />

      {/* central glow — soul light */}
      <circle cx="110" cy="160" r="18" fill="url(#mcore)" />
      <circle cx="110" cy="160" r="4" fill="#fff5d6" opacity="0.95" />
      <circle cx="110" cy="160" r="1.8" fill="#fff" />

      {/* bottom flourish mirror */}
      <g stroke="url(#mg)" strokeWidth="0.7" fill="none" opacity="0.8">
        <path d="M 50 286 Q 110 300, 170 286" />
        <path d="M 65 280 Q 110 290, 155 280" />
      </g>
      <g fill="url(#mg)" opacity="0.85">
        <circle cx="110" cy="294" r="2.5" />
        <circle cx="96" cy="288" r="1.2" />
        <circle cx="124" cy="288" r="1.2" />
        <circle cx="82" cy="282" r="0.9" />
        <circle cx="138" cy="282" r="0.9" />
      </g>

      {/* bottom title */}
      <g opacity="0.9">
        <line x1="40" y1="314" x2="88" y2="314" stroke="url(#mg)" strokeWidth="0.4" opacity="0.6" />
        <line x1="132" y1="314" x2="180" y2="314" stroke="url(#mg)" strokeWidth="0.4" opacity="0.6" />
        <circle cx="110" cy="314" r="1.3" fill="url(#mg)" />
        <text x="110" y="318" textAnchor="middle" fontFamily="Cinzel, serif" fontSize="8" letterSpacing="2.5" fill="url(#mg)">ЗЕРКАЛО&#160;ДУШИ</text>
      </g>

      {/* scattered micro stars */}
      <g fill="url(#mg)">
        <circle cx="30" cy="70" r="0.9" opacity="0.55" />
        <circle cx="190" cy="75" r="0.9" opacity="0.55" />
        <circle cx="22" cy="160" r="0.7" opacity="0.45" />
        <circle cx="198" cy="170" r="0.7" opacity="0.45" />
        <circle cx="28" cy="250" r="0.9" opacity="0.5" />
        <circle cx="192" cy="245" r="0.9" opacity="0.5" />
        <circle cx="40" cy="105" r="0.5" opacity="0.4" />
        <circle cx="180" cy="110" r="0.5" opacity="0.4" />
        <circle cx="36" cy="220" r="0.5" opacity="0.4" />
        <circle cx="184" cy="220" r="0.5" opacity="0.4" />
      </g>
    </svg>
  );
}
