/**
 * Parametric minimal moon — a gold-lit disc with a translated shadow
 * carving out the phase. Replaces Unicode 🌑–🌘 emojis whose rendering
 * is unreliable across iOS/Android system fonts and Telegram's WebView.
 *
 * Inputs:
 *   - size: rendered diameter in px.
 *   - illumination: 0..1 — fraction of the disc that is lit.
 *   - waning: shadow side. When omitted we infer from the legacy emoji.
 *
 * Algorithm (matches the design hand-off):
 *   shift = (waning ? 1 : -1) * illumination * 100   // % translateX
 * shifts the dark shadow disc so the visible lit area equals
 * `illumination` and sits on the correct side.
 */
const WANING_EMOJI = new Set(["🌖", "🌗", "🌘"]);

export function MoonGlyph({
  size,
  illumination,
  emoji,
  waning,
}: {
  size: number;
  illumination: number;
  emoji?: string;
  waning?: boolean;
}) {
  const isWaning =
    waning ?? (emoji ? WANING_EMOJI.has(emoji) : false);
  const illum = Math.max(0, Math.min(1, illumination));
  const shift = (isWaning ? 1 : -1) * illum * 100;
  const blur = Math.max(0.5, size * 0.02);
  const rimW = Math.max(1, size * 0.014);

  return (
    <span
      className="gx-moon"
      aria-hidden="true"
      style={{
        width: size,
        height: size,
        background:
          "radial-gradient(circle at 42% 38%, rgba(240,212,138,0.96), rgba(212,178,84,0.6))",
        boxShadow: `0 0 ${size * 0.3}px rgba(212,178,84,0.22)`,
      }}
    >
      <span
        className="gx-moon__sh"
        style={{
          transform: `translateX(${shift}%)`,
          filter: `blur(${blur}px)`,
        }}
      />
      <span
        className="gx-moon__rim"
        style={{
          boxShadow: `inset 0 0 0 ${rimW}px rgba(212,178,84,0.42)`,
        }}
      />
    </span>
  );
}
