# NatalChart

A themed, responsive, accessible SVG natal-chart component. Receives
pre-calculated planetary positions and renders a modern-mystical editorial
chart with zodiac, houses, planets, and aspect lines.

The component **does not calculate positions**. Pass in an already-computed
`NatalChartData` object from an ephemeris service (Swiss Ephemeris, etc.).

## Quick start

```tsx
import { NatalChart, sampleData } from './components/NatalChart';

<NatalChart data={sampleData} theme="midnight-gold" size={800} />
```

## API

| Prop              | Type                          | Default          | Notes |
| ----------------- | ----------------------------- | ---------------- | ----- |
| `data`            | `NatalChartData`              | required         | Pre-calculated positions. |
| `theme`           | `'midnight-gold'` · `'purple-silver'` · `'forest-gold'` | `'midnight-gold'` | Switches CSS custom properties. |
| `size`            | `number`                      | `800`            | Rendered width in px; height is derived from the 1000×1400 viewBox. |
| `title`           | `string`                      | `'NATAL'`        | Header title (display serif). |
| `showDecorative`  | `boolean`                     | `true`           | Toggle top/bottom arch frames. |
| `showSideFigures` | `boolean`                     | `true`           | Toggle left/right zodiac figures. Auto-disables below ~400px container width. |
| `className`       | `string`                      | —                | Passed to the root `<svg>`. |
| `onPlanetClick`   | `(planet: PlanetName) => void`| —                | When set, planet glyphs become focusable buttons. |
| `onHouseClick`    | `(house: number) => void`     | —                | When set, house wedges become focusable buttons. |

Full type definitions live in [`types.ts`](./types.ts). Sample data shaped to
those types lives in [`sampleData.ts`](./sampleData.ts).

## Theming

Each theme is a block of CSS custom properties in
[`NatalChart.module.css`](./NatalChart.module.css):

```css
.root[data-theme="midnight-gold"] {
  --natal-bg:        #0A0E27;
  --natal-primary:   #F5E6C8;   /* main line color */
  --natal-accent:    #C9A961;   /* highlights, title */
  --natal-secondary: #4A7C7E;   /* alternating sector fill, square aspects */
  --natal-dim:       rgba(245, 230, 200, 0.35);  /* ticks, dashed aspects */
}
```

### Adding a new theme

1. Extend the `ThemeName` union in [`types.ts`](./types.ts).
2. Add a `.root[data-theme="your-theme"]` block in
   [`NatalChart.module.css`](./NatalChart.module.css) with the five custom
   properties above.
3. (Optional) document the new palette in this README.

The component never hard-codes hex values — every color comes from these
tokens, so a new theme is a one-file addition.

## Typography

Fonts are referenced by name only (no external imports). Cinzel and Cormorant
Garamond are assumed to be loaded by the host app (e.g. via Google Fonts or a
local webfont stack); missing fonts fall back through Georgia → serif.

```css
--natal-font-display:  "Cinzel", "Della Respira", Georgia, serif;
--natal-font-subtitle: "Cormorant Garamond", "Playfair Display", Georgia, serif;
--natal-font-body:     "Inter", "Helvetica Neue", Arial, sans-serif;
```

## The 12 zodiac figures

The left and right side figures are an MVP **Tier 1** rendition: an oversized
Unicode glyph with minimal ornamental flourishes. Upgrade tiers:

- **Tier 2 — line-art symbolic figures** (ram, bull, twins, crab, lion…). See
  the brief for the full list. Drop each figure as a React component into
  [`assets/zodiac/`](./assets/zodiac/) and switch on `sign` inside
  [`parts/SideFigure.tsx`](./parts/SideFigure.tsx). Match the existing
  consistent-line-weight aesthetic (1px strokes, no fills).
- **Tier 3 — bespoke illustrator assets**. Same drop-in as Tier 2, higher
  fidelity. Import as inline SVG components (not `<img>` tags) so they inherit
  theme colors via `var(--natal-primary)`.

The architecture makes these upgrades local to `SideFigure.tsx` — no other
file needs to change.

## Responsive behavior

The component observes its rendered width via `ResizeObserver`. Below ~400px
it auto-hides side figures; it always scales to its container while
preserving the 5:7 aspect ratio. At 400px wide the wheel + corner metadata
remain fully legible.

## Accessibility

- Root `<svg>` carries `role="img"`, `<title>`, and `<desc>` describing the
  subject.
- When `onPlanetClick` is set, each planet becomes a keyboard-focusable
  button with a `<title>` description of its sign / degree / house.
- Same pattern for houses when `onHouseClick` is set — the whole house wedge
  is the hit target.
- Focus ring uses `--natal-accent` via `:focus-visible`.
- Primary text on background meets WCAG AA in all three themes.

## Expected data format

See [`types.ts`](./types.ts) for the full shape. The key pieces:

- `ascendant.sign/degree/minute` — determines wheel rotation (ascendant sits
  at 9 o'clock / west).
- `planets` — a `Record<PlanetName, PlanetPosition>` for all 12 tracked
  bodies (10 planets + north node + chiron).
- `houses` — 12 cusps with **absolute** ecliptic degree (0 = 0° Aries), in
  `number` order 1–12.
- `aspects` — enumerated; the component doesn't compute aspects from
  positions, it just renders what's in the array.

## File structure

```
NatalChart/
├── NatalChart.tsx           main component (props, ResizeObserver, ARIA)
├── NatalChart.module.css    theme tokens + text classes
├── types.ts
├── constants.ts             glyphs, labels, layout constants (WHEEL)
├── sampleData.ts            realistic fixture for dev / tests
├── utils/
│   ├── geometry.ts          polar/sectorPath/zodiacToSvgAngle
│   ├── aspects.ts           per-aspect visual style
│   ├── formatting.ts        "6°25'", "28 AUGUST 1982"
│   └── planetLayout.ts      collision-aware radial stacking
└── parts/
    ├── TopFrame.tsx / BottomFrame.tsx
    ├── Header.tsx
    ├── CornerMetadata.tsx
    ├── SideFigure.tsx
    ├── ChartWheel.tsx       orchestrator for everything inside the wheel
    ├── ZodiacRing.tsx
    ├── HouseRing.tsx
    ├── PlanetLayer.tsx
    ├── DegreeLabels.tsx
    ├── AspectLines.tsx
    ├── TickMarks.tsx
    └── CenterGlyph.tsx
```

## Not included (future phases)

- Position calculation (ephemeris).
- PDF export (the inline `<svg>` can be extracted from the DOM).
- Storybook — the dev-page in [`src/App.tsx`](../../App.tsx) serves the same
  purpose for now; add Storybook when the component stabilizes.
