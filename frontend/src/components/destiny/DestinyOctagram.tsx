import type { DestinyMatrixPositions } from "@/services/api";

/**
 * Destiny Matrix octagram — every node is tap-able.
 *
 * Layout follows the canonical Ладини cheat sheet:
 *
 *   • Outer ring  — age scale 0–80 years with 5-year markers
 *   • Big diamond — 5 base positions (day / month / year / bottom / center)
 *   • Small square — 4 ancestral corners (TL / TR / BR / BL)
 *   • Axis channels — each side of the diamond carries 2 inner points:
 *       top  axis: talents          (M+C, M+(M+C))
 *       right    : material karma   (mk_center, mk_point)
 *       bottom   : karmic tail      (B+C, B+(B+C))
 *       left     : parental         (D+C, D+(D+C))
 *   • Diagonal channels — each square corner carries 2 outer points:
 *       TL: father talents          BR: mother karma
 *       TR: mother talents          BL: father karma
 *   • Decorative ♥ / $ icons near the center
 *
 * Every node opens the bottom-sheet on tap. The parent screen picks the
 * right arcana context for each nodeId.
 *
 * Geometry: viewBox 0 0 460 460, center (230,230).
 */

export type DestinyNodeId =
  // Big diamond (free)
  | "day" | "month" | "year" | "bottom" | "center"
  // Small ancestral square (premium)
  | "top_left" | "top_right" | "bottom_right" | "bottom_left"
  // Axis channels — 3 points per cardinal axis, from corner toward center.
  // "_near" = inner_near_corner (corner + middle, sum)
  // "_mid"  = middle (corner + center, sum)
  // "_close" = inner_near_center (middle + center, sum)
  | "month_near" | "month_mid" | "month_close"   // top axis — talents
  | "year_near"  | "year_mid"  | "year_close"    // right axis — material karma
  | "bottom_near" | "bottom_mid" | "bottom_close" // bottom axis — karmic tail
  | "day_near"   | "day_mid"   | "day_close"     // left axis — parental
  // Diagonal ancestral channels (premium)
  | "aft_in" | "aft_out"     // father talents — TL diagonal
  | "amt_in" | "amt_out"     // mother talents — TR diagonal
  | "amk_in" | "amk_out"     // mother karma   — BR diagonal
  | "afk_in" | "afk_out";    // father karma   — BL diagonal

export interface NodeMeta {
  nodeId: DestinyNodeId;
  num: number;
  tier: "free" | "premium";
  x: number;
  y: number;
}

// ── Geometry ───────────────────────────────────────────────────────────
const VIEW = 460;
const CX = VIEW / 2;
const CY = VIEW / 2;

const R_AGE_RING   = 218;       // age scale circle
const R_AGE_TICK   = 224;       // outward tick for age markers
const R_AGE_LABEL  = 234;       // age number labels
// Diamond is the OUTER figure; square sits INSIDE it (smaller) — matches
// the canonical cheat-sheet layout where 4/8/15/3 corners sit beyond the
// 7/12/5/18 ancestral square.
const R_DIAMOND    = 185;
const R_SQUARE     = 125;
// Axis channels — 3 radii per cardinal direction (toward center).
// Per Ладини cheat sheet: each axis carries [corner, near, mid, close, center]
// where near = corner+middle, mid = corner+center, close = middle+center.
const R_AXIS_NEAR  = 115;       // close to the corner side
const R_AXIS_MID   = 80;        // halfway between corner and center
const R_AXIS_CLOSE = 45;        // close to the center side
// Diagonal channels: both points sit BETWEEN the square corner (R_SQUARE)
// and the center, grouped on the inner side of the corner — matches the
// canonical chart where the small companion numbers cluster next to each
// square corner inward.
const R_DIAG_NEAR  = 95;        // just inside the corner (corner-side)
const R_DIAG_CLOSE = 60;        // closer to center
// Decorative ♥ and $ icons clustered around center
const R_ICON       = 38;

function polar(angleDeg: number, radius: number): [number, number] {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return [CX + radius * Math.cos(rad), CY + radius * Math.sin(rad)];
}

// Diamond corners
const [MX, MY] = polar(0,   R_DIAMOND);   // top — month
const [YX, YY] = polar(90,  R_DIAMOND);   // right — year
const [BX, BY] = polar(180, R_DIAMOND);   // bottom
const [DX, DY] = polar(270, R_DIAMOND);   // left — day
// Square corners — inner, smaller than the diamond
const [TLX, TLY] = polar(315, R_SQUARE);
const [TRX, TRY] = polar(45,  R_SQUARE);
const [BRX, BRY] = polar(135, R_SQUARE);
const [BLX, BLY] = polar(225, R_SQUARE);
// Axis channel coordinates — 3 points per cardinal direction (near / mid / close)
const [TOP_NX, TOP_NY] = polar(0, R_AXIS_NEAR);
const [TOP_MX, TOP_MY] = polar(0, R_AXIS_MID);
const [TOP_CX, TOP_CY] = polar(0, R_AXIS_CLOSE);
const [RIGHT_NX, RIGHT_NY] = polar(90, R_AXIS_NEAR);
const [RIGHT_MX, RIGHT_MY] = polar(90, R_AXIS_MID);
const [RIGHT_CX, RIGHT_CY] = polar(90, R_AXIS_CLOSE);
const [BOT_NX, BOT_NY] = polar(180, R_AXIS_NEAR);
const [BOT_MX, BOT_MY] = polar(180, R_AXIS_MID);
const [BOT_CX, BOT_CY] = polar(180, R_AXIS_CLOSE);
const [LEFT_NX, LEFT_NY] = polar(270, R_AXIS_NEAR);
const [LEFT_MX, LEFT_MY] = polar(270, R_AXIS_MID);
const [LEFT_CX, LEFT_CY] = polar(270, R_AXIS_CLOSE);
// Diagonal channel coordinates — both points sit INSIDE, between the
// square corner and the center, grouped near the corner.
const [TL_NX, TL_NY] = polar(315, R_DIAG_NEAR);
const [TL_CX, TL_CY] = polar(315, R_DIAG_CLOSE);
const [TR_NX, TR_NY] = polar(45,  R_DIAG_NEAR);
const [TR_CX, TR_CY] = polar(45,  R_DIAG_CLOSE);
const [BR_NX, BR_NY] = polar(135, R_DIAG_NEAR);
const [BR_CX, BR_CY] = polar(135, R_DIAG_CLOSE);
const [BL_NX, BL_NY] = polar(225, R_DIAG_NEAR);
const [BL_CX, BL_CY] = polar(225, R_DIAG_CLOSE);

type Variant =
  | "base-lg"      // diamond + center
  | "base-md"      // square corners
  | "axis-near"    // axis point near the corner
  | "axis-mid"     // axis point at middle (corner+center)
  | "axis-close"   // axis point near the center
  | "diag-near"    // diagonal point near the square corner
  | "diag-close";  // diagonal point closer to center

interface NodeDef {
  nodeId: DestinyNodeId;
  num: number;
  tier: "free" | "premium";
  x: number;
  y: number;
  variant: Variant;
  color?: string;
}

// Palette per the canonical chart:
//   spiritual axis (top + left) = purple
//   material axis (right + bottom) = red
//   center = gold
const C_SPIRITUAL  = "#a87bd6";  // purple — top + left
const C_FINANCE    = "#e07b6a";  // warm red — right + bottom
const C_TALENTS    = "#e0c66a";  // yellow-gold — talents accent
const C_LOVE       = "#e07ba8";  // soft pink — relationships
const C_MONEY      = "#8cd6a0";  // mint green — money

// Helper: reduce a sum to a 1..22 arcana number (matches backend formula).
function toArcana(n: number): number {
  while (n > 22) {
    n = String(n).split("").reduce((s, d) => s + Number(d), 0);
  }
  return n || 22;
}

function buildNodes(positions: DestinyMatrixPositions): NodeDef[] {
  const p = positions.personality;
  const s = positions.ancestral_square;
  const ch = positions.channels;

  // Each cardinal axis has 3 inner points between corner and center,
  // derived by recursive sum-and-reduce per the cheat sheet:
  //   near  = corner + mid   (close to the corner)
  //   mid   = corner + center
  //   close = mid    + center (close to the center)
  // Already computed on the backend as channel[1] (mid) and channel[2] (near);
  // "close" is derived here from mid and center.
  const tal = ch.talents ?? [p.month, 0, 0];
  const mk  = ch.material_karma ?? [p.year, 0, 0];
  const kt  = ch.karmic_tail ?? [p.bottom, 0, 0];
  const par = ch.parental ?? [p.day, 0, 0];

  const monthMid  = tal[1] ?? 0;     // M+C
  const monthNear = tal[2] ?? 0;     // M+(M+C)
  const monthClose = toArcana(monthMid + p.center);

  const yearMid  = mk[2] ?? 0;       // Y+C  (mk_point)
  const yearNear = mk[1] ?? 0;       // Y+(Y+C) (mk_center) — closer to corner
  const yearClose = toArcana(yearMid + p.center);

  const bottomMid  = kt[1] ?? 0;     // B+C
  const bottomNear = kt[2] ?? 0;     // B+(B+C)
  const bottomClose = toArcana(bottomMid + p.center);

  const dayMid  = par[1] ?? 0;       // D+C
  const dayNear = par[2] ?? 0;       // D+(D+C)
  const dayClose = toArcana(dayMid + p.center);

  return [
    // ── Diamond + center (free) ──
    // Spiritual axis (top + left) = purple; material axis (right + bottom) = red.
    { nodeId: "day",    num: p.day,    tier: "free", x: DX, y: DY, variant: "base-lg", color: C_SPIRITUAL },
    { nodeId: "month",  num: p.month,  tier: "free", x: MX, y: MY, variant: "base-lg", color: C_SPIRITUAL },
    { nodeId: "year",   num: p.year,   tier: "free", x: YX, y: YY, variant: "base-lg", color: C_FINANCE },
    { nodeId: "bottom", num: p.bottom, tier: "free", x: BX, y: BY, variant: "base-lg", color: C_FINANCE },
    { nodeId: "center", num: p.center, tier: "free", x: CX, y: CY, variant: "base-lg" },

    // ── Small ancestral square (premium) ──
    { nodeId: "top_left",     num: s.top_left,     tier: "premium", x: TLX, y: TLY, variant: "base-md" },
    { nodeId: "top_right",    num: s.top_right,    tier: "premium", x: TRX, y: TRY, variant: "base-md" },
    { nodeId: "bottom_right", num: s.bottom_right, tier: "premium", x: BRX, y: BRY, variant: "base-md" },
    { nodeId: "bottom_left",  num: s.bottom_left,  tier: "premium", x: BLX, y: BLY, variant: "base-md" },

    // ── Axis channels (premium) — 3 points per cardinal direction ──
    { nodeId: "month_near",  num: monthNear,  tier: "premium", x: TOP_NX, y: TOP_NY, variant: "axis-near",  color: C_SPIRITUAL },
    { nodeId: "month_mid",   num: monthMid,   tier: "premium", x: TOP_MX, y: TOP_MY, variant: "axis-mid",   color: C_TALENTS },
    { nodeId: "month_close", num: monthClose, tier: "premium", x: TOP_CX, y: TOP_CY, variant: "axis-close", color: C_TALENTS },
    { nodeId: "year_near",   num: yearNear,   tier: "premium", x: RIGHT_NX, y: RIGHT_NY, variant: "axis-near",  color: C_FINANCE },
    { nodeId: "year_mid",    num: yearMid,    tier: "premium", x: RIGHT_MX, y: RIGHT_MY, variant: "axis-mid",   color: C_MONEY },
    { nodeId: "year_close",  num: yearClose,  tier: "premium", x: RIGHT_CX, y: RIGHT_CY, variant: "axis-close", color: C_MONEY },
    { nodeId: "bottom_near",  num: bottomNear,  tier: "free", x: BOT_NX, y: BOT_NY, variant: "axis-near",  color: C_FINANCE },
    { nodeId: "bottom_mid",   num: bottomMid,   tier: "free", x: BOT_MX, y: BOT_MY, variant: "axis-mid",   color: C_FINANCE },
    { nodeId: "bottom_close", num: bottomClose, tier: "free", x: BOT_CX, y: BOT_CY, variant: "axis-close", color: C_FINANCE },
    { nodeId: "day_near",   num: dayNear,   tier: "premium", x: LEFT_NX, y: LEFT_NY, variant: "axis-near",  color: C_SPIRITUAL },
    { nodeId: "day_mid",    num: dayMid,    tier: "premium", x: LEFT_MX, y: LEFT_MY, variant: "axis-mid",   color: C_LOVE },
    { nodeId: "day_close",  num: dayClose,  tier: "premium", x: LEFT_CX, y: LEFT_CY, variant: "axis-close", color: C_LOVE },

    // ── Diagonal ancestral channels (premium) — both points INSIDE,
    //    grouped near each square corner toward the center.
    { nodeId: "aft_in",  num: ch.ancestral_father_talents[1] ?? 0, tier: "premium", x: TL_NX, y: TL_NY, variant: "diag-near" },
    { nodeId: "aft_out", num: ch.ancestral_father_talents[2] ?? 0, tier: "premium", x: TL_CX, y: TL_CY, variant: "diag-close" },
    { nodeId: "amt_in",  num: ch.ancestral_mother_talents[1] ?? 0, tier: "premium", x: TR_NX, y: TR_NY, variant: "diag-near" },
    { nodeId: "amt_out", num: ch.ancestral_mother_talents[2] ?? 0, tier: "premium", x: TR_CX, y: TR_CY, variant: "diag-close" },
    { nodeId: "amk_in",  num: ch.ancestral_mother_karma[1] ?? 0,   tier: "premium", x: BR_NX, y: BR_NY, variant: "diag-near" },
    { nodeId: "amk_out", num: ch.ancestral_mother_karma[2] ?? 0,   tier: "premium", x: BR_CX, y: BR_CY, variant: "diag-close" },
    { nodeId: "afk_in",  num: ch.ancestral_father_karma[1] ?? 0,   tier: "premium", x: BL_NX, y: BL_NY, variant: "diag-near" },
    { nodeId: "afk_out", num: ch.ancestral_father_karma[2] ?? 0,   tier: "premium", x: BL_CX, y: BL_CY, variant: "diag-close" },
  ];
}

function nodeRadius(variant: Variant): number {
  switch (variant) {
    case "base-lg":    return 24;
    case "base-md":    return 21;
    case "axis-near":  return 13;
    case "axis-mid":   return 13;
    case "axis-close": return 12;
    case "diag-near":  return 12;
    case "diag-close": return 11;
  }
}

interface RenderedNodeProps {
  node: NodeDef;
  locked: boolean;
  active: boolean;
  faded: boolean;
  onTap: (n: NodeDef) => void;
}

function RenderedNode({ node, locked, active, faded, onTap }: RenderedNodeProps) {
  const r = nodeRadius(node.variant);
  const tapR = Math.max(r + 6, 18);
  const isCenter = node.nodeId === "center";

  const fontSize =
    isCenter ? 26 :
    node.variant === "base-lg" ? 19 :
    node.variant === "base-md" ? 16 :
    13;

  const goldDefault = "rgba(232,200,98,0.85)";
  const goldDim     = "rgba(232,200,98,0.55)";
  const baseStroke = node.color
    ? node.color
    : (node.variant.startsWith("base") || isCenter ? goldDefault : goldDim);
  const stroke = active ? "#e8c862" : baseStroke;
  const strokeWidth = active ? 2.4 : (node.variant.startsWith("base") ? 1.7 : 1.1);
  const tint = node.color ? `${node.color}26` : "#0e0b20";
  const numberFill = node.color ?? "#e8c862";

  return (
    <g
      className={
        "destiny-octagram__node" +
        (active ? " is-active" : "") +
        (faded ? " is-faded" : "") +
        (locked ? " is-locked" : "")
      }
      onClick={() => onTap(node)}
      style={{ cursor: "pointer" }}
    >
      <circle cx={node.x} cy={node.y} r={r}
        fill={tint} stroke={stroke} strokeWidth={strokeWidth} />
      {locked ? (
        <text x={node.x} y={node.y} textAnchor="middle" dominantBaseline="central"
          fontSize="16" fill="rgba(232,200,98,0.55)" style={{ fontFamily: "serif" }}>
          ?
        </text>
      ) : (
        <text x={node.x} y={node.y} textAnchor="middle" dominantBaseline="central"
          fontSize={fontSize} fill={numberFill} fontWeight={600}
          style={{ fontFamily: "Playfair Display, serif" }}>
          {node.num}
        </text>
      )}
      <circle cx={node.x} cy={node.y} r={tapR}
        fill="transparent" pointerEvents="all" />
    </g>
  );
}

// ── Age scale ───────────────────────────────────────────────────────────
// Per Ладини cheat sheet: 8 cardinal age nodes every 10 years (0, 10, 20,
// …, 70), positioned on the octagram's 8 outer vertices. 80 years brings
// us back to the starting day position.
const AGE_NODE_YEARS = [0, 10, 20, 30, 40, 50, 60, 70];
const AGE_MINOR_YEARS = [
  1, 2, 3, 4, 5, 6, 7, 8, 9,
  11, 12, 13, 14, 15, 16, 17, 18, 19,
  21, 22, 23, 24, 25, 26, 27, 28, 29,
  31, 32, 33, 34, 35, 36, 37, 38, 39,
  41, 42, 43, 44, 45, 46, 47, 48, 49,
  51, 52, 53, 54, 55, 56, 57, 58, 59,
  61, 62, 63, 64, 65, 66, 67, 68, 69,
  71, 72, 73, 74, 75, 76, 77, 78, 79,
];

function ageAngle(years: number): number {
  // 0 years = left (D, 270°), 10 = TL (315°), 20 = top (M, 0°),
  // 30 = TR (45°), 40 = right (Y, 90°), 50 = BR (135°), 60 = bottom
  // (B, 180°), 70 = BL (225°), 80 = back to 270°. Each year = 4.5°.
  return (270 + years * 4.5) % 360;
}

function AgeRing() {
  return (
    <g data-part="age-ring">
      {/* The outer ring itself */}
      <circle cx={CX} cy={CY} r={R_AGE_RING}
        fill="none" stroke="rgba(232,200,98,0.35)" strokeWidth="0.9" />

      {/* Minor 1-year ticks (faint) */}
      {AGE_MINOR_YEARS.map((y) => {
        const ang = ageAngle(y);
        const inner = polar(ang, R_AGE_RING);
        const outer = polar(ang, R_AGE_TICK - 2);
        return (
          <line key={`min-${y}`}
            x1={inner[0]} y1={inner[1]} x2={outer[0]} y2={outer[1]}
            stroke="rgba(232,200,98,0.28)" strokeWidth="0.45" />
        );
      })}

      {/* Major 10-year nodes — these are the 8 octagram vertices */}
      {AGE_NODE_YEARS.map((y) => {
        const ang = ageAngle(y);
        const inner = polar(ang, R_AGE_RING - 3);
        const outer = polar(ang, R_AGE_TICK + 3);
        const labelPos = polar(ang, R_AGE_LABEL);
        return (
          <g key={`node-${y}`}>
            <line x1={inner[0]} y1={inner[1]} x2={outer[0]} y2={outer[1]}
              stroke="rgba(232,200,98,0.85)" strokeWidth="1.4" />
            <circle cx={polar(ang, R_AGE_RING)[0]} cy={polar(ang, R_AGE_RING)[1]}
              r="3" fill="#0e0b20" stroke="rgba(232,200,98,0.9)" strokeWidth="1" />
            <text x={labelPos[0]} y={labelPos[1]}
              textAnchor="middle" dominantBaseline="central"
              fontSize="11" fill="rgba(232,200,98,0.95)" fontWeight={600}
              style={{ fontFamily: "Inter, system-ui, sans-serif" }}>
              {y}
            </text>
          </g>
        );
      })}
    </g>
  );
}

interface Props {
  positions: DestinyMatrixPositions;
  hasFullAccess: boolean;
  activeNodeId: DestinyNodeId | null;
  onNodeTap: (node: NodeMeta) => void;
}

export function DestinyOctagram({
  positions, hasFullAccess, activeNodeId, onNodeTap,
}: Props) {
  const nodes = buildNodes(positions);

  return (
    <svg
      viewBox={`0 0 ${VIEW} ${VIEW}`}
      className="destiny-octagram"
      role="img"
      aria-label="Октаграмма матрицы судьбы"
    >
      {/* Age ring on the outside */}
      <AgeRing />

      {/* Diagonal guide rays from center to each square corner */}
      <line x1={CX} y1={CY} x2={TLX} y2={TLY} stroke="rgba(232,200,98,0.18)" strokeWidth="0.6" strokeDasharray="2 4" />
      <line x1={CX} y1={CY} x2={TRX} y2={TRY} stroke="rgba(232,200,98,0.18)" strokeWidth="0.6" strokeDasharray="2 4" />
      <line x1={CX} y1={CY} x2={BRX} y2={BRY} stroke="rgba(232,200,98,0.18)" strokeWidth="0.6" strokeDasharray="2 4" />
      <line x1={CX} y1={CY} x2={BLX} y2={BLY} stroke="rgba(232,200,98,0.18)" strokeWidth="0.6" strokeDasharray="2 4" />

      {/* Cardinal axes through center — these are the channel axes */}
      <line x1={DX} y1={DY} x2={YX} y2={YY}
        stroke="rgba(232,200,98,0.30)" strokeWidth="0.9" />
      <line x1={MX} y1={MY} x2={BX} y2={BY}
        stroke="rgba(232,200,98,0.30)" strokeWidth="0.9" />

      {/* Big diamond outline */}
      <path d={`M ${DX} ${DY} L ${MX} ${MY} L ${YX} ${YY} L ${BX} ${BY} Z`}
        fill="none" stroke="rgba(232,200,98,0.55)" strokeWidth="1.2" />
      {/* Small ancestral square outline (rotated 45°) */}
      <path d={`M ${TLX} ${TLY} L ${TRX} ${TRY} L ${BRX} ${BRY} L ${BLX} ${BLY} Z`}
        fill="none" stroke="rgba(232,200,98,0.45)" strokeWidth="1.0" strokeDasharray="3 3" />

      {/* Decorative icons near center (visual flair, non-interactive) */}
      <text x={CX + R_ICON * Math.cos((45 - 90) * Math.PI / 180)}
            y={CY + R_ICON * Math.sin((45 - 90) * Math.PI / 180)}
            textAnchor="middle" dominantBaseline="central" fontSize="14"
            opacity="0.7">💰</text>
      <text x={CX + R_ICON * Math.cos((135 - 90) * Math.PI / 180)}
            y={CY + R_ICON * Math.sin((135 - 90) * Math.PI / 180)}
            textAnchor="middle" dominantBaseline="central" fontSize="14"
            opacity="0.7">♥</text>

      {/* All tap-able nodes */}
      {nodes.map((node) => {
        const locked = node.tier === "premium" && !hasFullAccess;
        const active = activeNodeId === node.nodeId;
        const faded = activeNodeId !== null && !active;
        return (
          <RenderedNode
            key={node.nodeId}
            node={node}
            locked={locked}
            active={active}
            faded={faded}
            onTap={(n) => onNodeTap({
              nodeId: n.nodeId, num: n.num, tier: n.tier, x: n.x, y: n.y,
            })}
          />
        );
      })}
    </svg>
  );
}

export type { NodeMeta as DestinyNodeMeta };
