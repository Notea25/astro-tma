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
  // Axis channels — inside the diamond, on each cardinal axis (premium)
  | "month_mid" | "month_in"     // talents (top axis)
  | "year_mid" | "year_in"       // material karma (right axis)
  | "bottom_mid" | "bottom_in"   // karmic tail (bottom axis, INSIDE diamond)
  | "day_mid" | "day_in"         // parental (left axis)
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
const R_BASE       = 150;       // diamond corners + square corners
// Axis channels (4 cardinal directions × 2 radii inside the diamond)
const R_AXIS_MID   = 95;        // middle position between corner and center
const R_AXIS_IN    = 50;        // closer to center
// Diagonal channels (4 square corners × 2 radii — _in inside, _out outside)
const R_DIAG_IN    = 88;
const R_DIAG_OUT   = 200;
// Decorative ♥ and $ icons clustered around center
const R_ICON       = 38;

function polar(angleDeg: number, radius: number): [number, number] {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return [CX + radius * Math.cos(rad), CY + radius * Math.sin(rad)];
}

// Diamond corners
const [MX, MY] = polar(0,   R_BASE);   // top — month
const [YX, YY] = polar(90,  R_BASE);   // right — year
const [BX, BY] = polar(180, R_BASE);   // bottom
const [DX, DY] = polar(270, R_BASE);   // left — day
// Square corners
const [TLX, TLY] = polar(315, R_BASE);
const [TRX, TRY] = polar(45,  R_BASE);
const [BRX, BRY] = polar(135, R_BASE);
const [BLX, BLY] = polar(225, R_BASE);
// Axis channel coordinates
const [TOP_MX,   TOP_MY]   = polar(0,   R_AXIS_MID);
const [TOP_IX,   TOP_IY]   = polar(0,   R_AXIS_IN);
const [RIGHT_MX, RIGHT_MY] = polar(90,  R_AXIS_MID);
const [RIGHT_IX, RIGHT_IY] = polar(90,  R_AXIS_IN);
const [BOT_MX,   BOT_MY]   = polar(180, R_AXIS_MID);
const [BOT_IX,   BOT_IY]   = polar(180, R_AXIS_IN);
const [LEFT_MX,  LEFT_MY]  = polar(270, R_AXIS_MID);
const [LEFT_IX,  LEFT_IY]  = polar(270, R_AXIS_IN);
// Diagonal channel coordinates
const [TL_IX, TL_IY] = polar(315, R_DIAG_IN);
const [TL_OX, TL_OY] = polar(315, R_DIAG_OUT);
const [TR_IX, TR_IY] = polar(45,  R_DIAG_IN);
const [TR_OX, TR_OY] = polar(45,  R_DIAG_OUT);
const [BR_IX, BR_IY] = polar(135, R_DIAG_IN);
const [BR_OX, BR_OY] = polar(135, R_DIAG_OUT);
const [BL_IX, BL_IY] = polar(225, R_DIAG_IN);
const [BL_OX, BL_OY] = polar(225, R_DIAG_OUT);

type Variant =
  | "base-lg"    // diamond + center
  | "base-md"    // square corners
  | "axis-mid"   // channel middle on a diamond axis
  | "axis-in"    // channel inner-near-center
  | "diag-in"    // diagonal channel inner
  | "diag-out";  // diagonal channel outer

interface NodeDef {
  nodeId: DestinyNodeId;
  num: number;
  tier: "free" | "premium";
  x: number;
  y: number;
  variant: Variant;
  color?: string;
}

// ── Cheat-sheet aligned color palette ──────────────────────────────────
const C_SPIRITUAL  = "#a87bd6";  // purple — top axis (intellect / spirit)
const C_FINANCE    = "#e07b6a";  // warm red — right axis (money / material)
const C_KARMA      = "#e0a06a";  // orange — bottom axis (karmic lesson)
const C_PORTRAIT   = "#d9d6c8";  // off-white — left axis (your portrait)
const C_TALENTS    = "#e0c66a";  // yellow-gold — axis-in for talents
const C_LOVE       = "#e07ba8";  // soft pink — relationships flavor
const C_MONEY      = "#8cd6a0";  // mint green — money flavor

function buildNodes(positions: DestinyMatrixPositions): NodeDef[] {
  const p = positions.personality;
  const s = positions.ancestral_square;
  const ch = positions.channels;

  const tal = ch.talents ?? [0, 0, 0];
  const mk  = ch.material_karma ?? [0, 0, 0];
  const kt  = ch.karmic_tail ?? [0, 0, 0];
  const par = ch.parental ?? [0, 0, 0];

  return [
    // ── Diamond + center (free) ──
    { nodeId: "day",    num: p.day,    tier: "free", x: DX, y: DY, variant: "base-lg", color: C_PORTRAIT },
    { nodeId: "month",  num: p.month,  tier: "free", x: MX, y: MY, variant: "base-lg", color: C_SPIRITUAL },
    { nodeId: "year",   num: p.year,   tier: "free", x: YX, y: YY, variant: "base-lg", color: C_FINANCE },
    { nodeId: "bottom", num: p.bottom, tier: "free", x: BX, y: BY, variant: "base-lg", color: C_KARMA },
    { nodeId: "center", num: p.center, tier: "free", x: CX, y: CY, variant: "base-lg" },

    // ── Small ancestral square (premium) ──
    { nodeId: "top_left",     num: s.top_left,     tier: "premium", x: TLX, y: TLY, variant: "base-md" },
    { nodeId: "top_right",    num: s.top_right,    tier: "premium", x: TRX, y: TRY, variant: "base-md" },
    { nodeId: "bottom_right", num: s.bottom_right, tier: "premium", x: BRX, y: BRY, variant: "base-md" },
    { nodeId: "bottom_left",  num: s.bottom_left,  tier: "premium", x: BLX, y: BLY, variant: "base-md" },

    // ── Axis channels (premium) — inside the diamond ──
    // Top axis: talents [M, M+C, M+(M+C)]
    { nodeId: "month_mid", num: tal[1] ?? 0, tier: "premium", x: TOP_MX, y: TOP_MY, variant: "axis-mid", color: C_SPIRITUAL },
    { nodeId: "month_in",  num: tal[2] ?? 0, tier: "premium", x: TOP_IX, y: TOP_IY, variant: "axis-in",  color: C_TALENTS },
    // Right axis: material karma [Y, mk_center, mk_point]
    { nodeId: "year_mid",  num: mk[1] ?? 0,  tier: "premium", x: RIGHT_MX, y: RIGHT_MY, variant: "axis-mid", color: C_FINANCE },
    { nodeId: "year_in",   num: mk[2] ?? 0,  tier: "premium", x: RIGHT_IX, y: RIGHT_IY, variant: "axis-in",  color: C_MONEY },
    // Bottom axis: karmic tail [B, B+C, B+(B+C)] — now INSIDE the diamond
    { nodeId: "bottom_mid", num: kt[1] ?? 0, tier: "free", x: BOT_MX, y: BOT_MY, variant: "axis-mid", color: C_KARMA },
    { nodeId: "bottom_in",  num: kt[2] ?? 0, tier: "free", x: BOT_IX, y: BOT_IY, variant: "axis-in",  color: C_KARMA },
    // Left axis: parental [D, D+C, D+(D+C)]
    { nodeId: "day_mid",   num: par[1] ?? 0, tier: "premium", x: LEFT_MX, y: LEFT_MY, variant: "axis-mid", color: C_PORTRAIT },
    { nodeId: "day_in",    num: par[2] ?? 0, tier: "premium", x: LEFT_IX, y: LEFT_IY, variant: "axis-in",  color: C_LOVE },

    // ── Diagonal ancestral channels (premium) ──
    { nodeId: "aft_in",  num: ch.ancestral_father_talents[1] ?? 0, tier: "premium", x: TL_IX, y: TL_IY, variant: "diag-in" },
    { nodeId: "aft_out", num: ch.ancestral_father_talents[2] ?? 0, tier: "premium", x: TL_OX, y: TL_OY, variant: "diag-out" },
    { nodeId: "amt_in",  num: ch.ancestral_mother_talents[1] ?? 0, tier: "premium", x: TR_IX, y: TR_IY, variant: "diag-in" },
    { nodeId: "amt_out", num: ch.ancestral_mother_talents[2] ?? 0, tier: "premium", x: TR_OX, y: TR_OY, variant: "diag-out" },
    { nodeId: "amk_in",  num: ch.ancestral_mother_karma[1] ?? 0,   tier: "premium", x: BR_IX, y: BR_IY, variant: "diag-in" },
    { nodeId: "amk_out", num: ch.ancestral_mother_karma[2] ?? 0,   tier: "premium", x: BR_OX, y: BR_OY, variant: "diag-out" },
    { nodeId: "afk_in",  num: ch.ancestral_father_karma[1] ?? 0,   tier: "premium", x: BL_IX, y: BL_IY, variant: "diag-in" },
    { nodeId: "afk_out", num: ch.ancestral_father_karma[2] ?? 0,   tier: "premium", x: BL_OX, y: BL_OY, variant: "diag-out" },
  ];
}

function nodeRadius(variant: Variant): number {
  switch (variant) {
    case "base-lg":  return 24;
    case "base-md":  return 21;
    case "axis-mid": return 14;
    case "axis-in":  return 12;
    case "diag-in":  return 12;
    case "diag-out": return 12;
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
  const numberFill = node.color && node.color !== C_PORTRAIT ? node.color : "#e8c862";

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
// Major year labels (every 5 years: 0, 5, 10, ..., 75). Cardinal points
// (0/20/40/60) fall right at the diamond corners.
const AGE_MAJOR_YEARS = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75];

function ageAngle(years: number): number {
  // 0 years = left (D, 270°), 20 = top (M, 0°), 40 = right (Y, 90°),
  // 60 = bottom (B, 180°), 80 = back to 270° (full loop).
  // Each year = 360/80 = 4.5° clockwise from 270°.
  return (270 + years * 4.5) % 360;
}

function AgeRing() {
  const minorYears: number[] = [];
  for (let y = 0; y <= 80; y += 1) minorYears.push(y);

  return (
    <g data-part="age-ring">
      {/* The outer ring itself */}
      <circle cx={CX} cy={CY} r={R_AGE_RING}
        fill="none" stroke="rgba(232,200,98,0.32)" strokeWidth="0.9" />

      {/* Minor ticks (every 1 year) */}
      {minorYears.map((y) => {
        const isMajor = y % 5 === 0;
        const ang = ageAngle(y);
        const inner = polar(ang, R_AGE_RING);
        const outer = polar(ang, isMajor ? R_AGE_TICK + 2 : R_AGE_TICK - 2);
        return (
          <line key={y}
            x1={inner[0]} y1={inner[1]} x2={outer[0]} y2={outer[1]}
            stroke="rgba(232,200,98,0.4)"
            strokeWidth={isMajor ? 0.9 : 0.45} />
        );
      })}

      {/* Major year labels */}
      {AGE_MAJOR_YEARS.map((y) => {
        const ang = ageAngle(y);
        const pos = polar(ang, R_AGE_LABEL);
        const isCardinal = y === 0 || y === 20 || y === 40 || y === 60;
        return (
          <text key={`lbl-${y}`} x={pos[0]} y={pos[1]}
            textAnchor="middle" dominantBaseline="central"
            fontSize={isCardinal ? 10 : 8.5}
            fill={isCardinal ? "rgba(232,200,98,0.95)" : "rgba(232,200,98,0.6)"}
            fontWeight={isCardinal ? 600 : 500}
            style={{ fontFamily: "Inter, system-ui, sans-serif" }}>
            {y}
          </text>
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

      {/* Diagonal guide rays (subtle) */}
      <line x1={CX} y1={CY} x2={TL_OX} y2={TL_OY} stroke="rgba(232,200,98,0.12)" strokeWidth="0.6" strokeDasharray="2 4" />
      <line x1={CX} y1={CY} x2={TR_OX} y2={TR_OY} stroke="rgba(232,200,98,0.12)" strokeWidth="0.6" strokeDasharray="2 4" />
      <line x1={CX} y1={CY} x2={BR_OX} y2={BR_OY} stroke="rgba(232,200,98,0.12)" strokeWidth="0.6" strokeDasharray="2 4" />
      <line x1={CX} y1={CY} x2={BL_OX} y2={BL_OY} stroke="rgba(232,200,98,0.12)" strokeWidth="0.6" strokeDasharray="2 4" />

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
