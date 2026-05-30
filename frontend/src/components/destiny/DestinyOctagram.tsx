import type { DestinyMatrixPositions } from "@/services/api";

/**
 * Destiny Matrix octagram — every node is tap-able.
 *
 * Layers (from outer in):
 * 1. Ancestral channels — 4 directions × 3 nodes (corner + middle + outer)
 *    on a radial through each square corner. Father talents (TL), mother
 *    talents (TR), mother karma (BR), father karma (BL).
 * 2. Karmic tail — bottom diamond corner + 2 extension nodes below it.
 *    The deepest (outer) point is rimmed in red — main karmic lesson.
 * 3. Big diamond (5 personality positions) + small ancestral square.
 * 4. Inner energy icons — talents (✦), relationships (♥), finance (₽),
 *    material karma (⚖) clustered around the center showing each
 *    channel's "работа" (middle) number.
 *
 * Every node opens the bottom-sheet on tap. The parent screen picks the
 * right arcana context for each nodeId.
 *
 * Geometry: viewBox 0 0 420 420, center (210,210).
 */

export type DestinyNodeId =
  // Big diamond (free)
  | "day" | "month" | "year" | "bottom" | "center"
  // Small ancestral square (premium)
  | "top_left" | "top_right" | "bottom_right" | "bottom_left"
  // Ancestral channels (premium). "_in" sits between square corner and
  // center (closer to E); "_out" sits outside the square.
  | "aft_in" | "aft_out"     // father talents — TL line
  | "amt_in" | "amt_out"     // mother talents — TR line
  | "amk_in" | "amk_out"     // mother karma   — BR line
  | "afk_in" | "afk_out"     // father karma   — BL line
  // Karmic tail extension (free — important hook for paywall)
  | "kt_mid" | "kt_out"
  // Inner energy icons (premium): talents, relationships, finance
  | "talents_mid" | "relationships_mid" | "finance_mid";

export interface NodeMeta {
  nodeId: DestinyNodeId;
  num: number;
  tier: "free" | "premium";
  x: number;
  y: number;
}

const CX = 210;
const CY = 210;
const R_BASE = 130;
// Channel middle sits INSIDE the octagram (between center and the
// square corner). Outer sits outside the square along the same ray.
const R_CH_IN = 78;
const R_CH_OUT = 182;
const R_KT_MID = 168;
const R_KT_OUT = 203;
const R_ICON = 44;

function polar(angleDeg: number, radius: number): [number, number] {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return [CX + radius * Math.cos(rad), CY + radius * Math.sin(rad)];
}

// Coordinates -- computed once
const [MX, MY] = polar(0, R_BASE);
const [YX, YY] = polar(90, R_BASE);
const [BX, BY] = polar(180, R_BASE);
const [DX, DY] = polar(270, R_BASE);
const [TLX, TLY] = polar(315, R_BASE);
const [TRX, TRY] = polar(45, R_BASE);
const [BRX, BRY] = polar(135, R_BASE);
const [BLX, BLY] = polar(225, R_BASE);
const [TL_IX, TL_IY] = polar(315, R_CH_IN);
const [TL_OX, TL_OY] = polar(315, R_CH_OUT);
const [TR_IX, TR_IY] = polar(45, R_CH_IN);
const [TR_OX, TR_OY] = polar(45, R_CH_OUT);
const [BR_IX, BR_IY] = polar(135, R_CH_IN);
const [BR_OX, BR_OY] = polar(135, R_CH_OUT);
const [BL_IX, BL_IY] = polar(225, R_CH_IN);
const [BL_OX, BL_OY] = polar(225, R_CH_OUT);
const [KT_MX, KT_MY] = polar(180, R_KT_MID);
const [KT_OX, KT_OY] = polar(180, R_KT_OUT);
// Three inner energy icons clustered above center
const [TAL_X, TAL_Y] = polar(0, R_ICON);
const [REL_X, REL_Y] = polar(120, R_ICON);
const [FIN_X, FIN_Y] = polar(240, R_ICON);

type Variant = "base-lg" | "base-md" | "channel-in" | "channel-out" | "kt-mid" | "kt-out" | "icon";

interface NodeDef {
  nodeId: DestinyNodeId;
  num: number;
  tier: "free" | "premium";
  x: number;
  y: number;
  variant: Variant;
  icon?: string;
}

function buildNodes(positions: DestinyMatrixPositions): NodeDef[] {
  const p = positions.personality;
  const s = positions.ancestral_square;
  const ch = positions.channels;

  return [
    // ── Big diamond + center (free) ─────────────────────────────────
    { nodeId: "day",    num: p.day,    tier: "free", x: DX, y: DY, variant: "base-lg" },
    { nodeId: "month",  num: p.month,  tier: "free", x: MX, y: MY, variant: "base-lg" },
    { nodeId: "year",   num: p.year,   tier: "free", x: YX, y: YY, variant: "base-lg" },
    { nodeId: "bottom", num: p.bottom, tier: "free", x: BX, y: BY, variant: "base-lg" },
    { nodeId: "center", num: p.center, tier: "free", x: CX, y: CY, variant: "base-lg" },

    // ── Small ancestral square (premium) ────────────────────────────
    { nodeId: "top_left",     num: s.top_left,     tier: "premium", x: TLX, y: TLY, variant: "base-md" },
    { nodeId: "top_right",    num: s.top_right,    tier: "premium", x: TRX, y: TRY, variant: "base-md" },
    { nodeId: "bottom_right", num: s.bottom_right, tier: "premium", x: BRX, y: BRY, variant: "base-md" },
    { nodeId: "bottom_left",  num: s.bottom_left,  tier: "premium", x: BLX, y: BLY, variant: "base-md" },

    // ── Ancestral channels (premium): _in (between center and square
    //     corner), _out (outside square). Corner itself is the base-md
    //     node above. ──────────────────────────────────────────────
    { nodeId: "aft_in",  num: ch.ancestral_father_talents[1] ?? 0, tier: "premium", x: TL_IX, y: TL_IY, variant: "channel-in" },
    { nodeId: "aft_out", num: ch.ancestral_father_talents[2] ?? 0, tier: "premium", x: TL_OX, y: TL_OY, variant: "channel-out" },
    { nodeId: "amt_in",  num: ch.ancestral_mother_talents[1] ?? 0, tier: "premium", x: TR_IX, y: TR_IY, variant: "channel-in" },
    { nodeId: "amt_out", num: ch.ancestral_mother_talents[2] ?? 0, tier: "premium", x: TR_OX, y: TR_OY, variant: "channel-out" },
    { nodeId: "amk_in",  num: ch.ancestral_mother_karma[1] ?? 0,   tier: "premium", x: BR_IX, y: BR_IY, variant: "channel-in" },
    { nodeId: "amk_out", num: ch.ancestral_mother_karma[2] ?? 0,   tier: "premium", x: BR_OX, y: BR_OY, variant: "channel-out" },
    { nodeId: "afk_in",  num: ch.ancestral_father_karma[1] ?? 0,   tier: "premium", x: BL_IX, y: BL_IY, variant: "channel-in" },
    { nodeId: "afk_out", num: ch.ancestral_father_karma[2] ?? 0,   tier: "premium", x: BL_OX, y: BL_OY, variant: "channel-out" },

    // ── Karmic tail (free — main hook) ──────────────────────────────
    { nodeId: "kt_mid", num: ch.karmic_tail[1] ?? 0, tier: "free", x: KT_MX, y: KT_MY, variant: "kt-mid" },
    { nodeId: "kt_out", num: ch.karmic_tail[2] ?? 0, tier: "free", x: KT_OX, y: KT_OY, variant: "kt-out" },

    // ── Inner energy icons (premium): talents / relationships / finance
    { nodeId: "talents_mid",       num: ch.talents[1] ?? 0,       tier: "premium", x: TAL_X, y: TAL_Y, variant: "icon", icon: "✦" },
    { nodeId: "relationships_mid", num: ch.relationships[1] ?? 0, tier: "premium", x: REL_X, y: REL_Y, variant: "icon", icon: "♥" },
    { nodeId: "finance_mid",       num: ch.finance[1] ?? 0,       tier: "premium", x: FIN_X, y: FIN_Y, variant: "icon", icon: "₽" },
  ];
}

function nodeRadius(variant: Variant): number {
  switch (variant) {
    case "base-lg":    return 24;     // diamond + center
    case "base-md":    return 21;     // square corners
    case "channel-in": return 14;     // channel inner (between corner & center)
    case "channel-out": return 12;    // channel outer (outside square)
    case "kt-mid":     return 14;
    case "kt-out":     return 15;
    case "icon":       return 12;
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
  const tapR = Math.max(r + 6, 18);  // enlarged invisible hit area for touch
  const isCenter = node.nodeId === "center";
  const isKtOut = node.variant === "kt-out";

  const fontSize =
    isCenter ? 26 :
    node.variant === "base-lg" ? 19 :
    node.variant === "base-md" ? 16 :
    node.variant === "kt-out" ? 14 :
    node.variant === "icon" ? 11 :
    node.variant === "channel-out" ? 12 :
    13;

  const stroke = active
    ? "#e8c862"
    : isKtOut
      ? "#d44a4a"
      : node.variant.startsWith("base") || isCenter
        ? "rgba(232,200,98,0.85)"
        : "rgba(232,200,98,0.55)";

  const strokeWidth = active ? 2.4 : (isKtOut ? 1.4 : node.variant.startsWith("base") ? 1.5 : 1);

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
      {/* Visible circle */}
      <circle
        cx={node.x}
        cy={node.y}
        r={r}
        fill="#0e0b20"
        stroke={stroke}
        strokeWidth={strokeWidth}
      />
      {/* Number / lock glyph */}
      {locked ? (
        <text
          x={node.x}
          y={node.y}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize="16"
          fill="rgba(232,200,98,0.55)"
          style={{ fontFamily: "serif" }}
        >
          ?
        </text>
      ) : (
        <text
          x={node.x}
          y={node.y - (node.variant === "icon" ? 1 : 0)}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={fontSize}
          fill="#e8c862"
          fontWeight={node.variant === "channel-out" ? 500 : 600}
          style={{ fontFamily: "Playfair Display, serif" }}
        >
          {node.num}
        </text>
      )}
      {/* Icon glyph next to inner nodes */}
      {!locked && node.variant === "icon" && node.icon && (
        <text
          x={node.x + 14}
          y={node.y - 10}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={10}
          fill="rgba(232,200,98,0.95)"
        >
          {node.icon}
        </text>
      )}
      {/* Invisible touch target — guarantees mobile-friendly tap area */}
      <circle
        cx={node.x}
        cy={node.y}
        r={tapR}
        fill="transparent"
        pointerEvents="all"
      />
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
      viewBox="0 0 420 420"
      className="destiny-octagram"
      role="img"
      aria-label="Октаграмма матрицы судьбы"
    >
      {/* Guide rays through square corners (subtle, decoration only) */}
      <line x1={CX} y1={CY} x2={TL_OX} y2={TL_OY} stroke="rgba(232,200,98,0.12)" strokeWidth="0.6" strokeDasharray="2 4" />
      <line x1={CX} y1={CY} x2={TR_OX} y2={TR_OY} stroke="rgba(232,200,98,0.12)" strokeWidth="0.6" strokeDasharray="2 4" />
      <line x1={CX} y1={CY} x2={BR_OX} y2={BR_OY} stroke="rgba(232,200,98,0.12)" strokeWidth="0.6" strokeDasharray="2 4" />
      <line x1={CX} y1={CY} x2={BL_OX} y2={BL_OY} stroke="rgba(232,200,98,0.12)" strokeWidth="0.6" strokeDasharray="2 4" />

      {/* Cross-axes through center */}
      <line x1={DX} y1={DY} x2={YX} y2={YY} stroke="rgba(232,200,98,0.22)" strokeWidth="0.8" />
      <line x1={MX} y1={MY} x2={KT_OX} y2={KT_OY} stroke="rgba(232,200,98,0.22)" strokeWidth="0.8" />

      {/* Big diamond outline */}
      <path
        d={`M ${DX} ${DY} L ${MX} ${MY} L ${YX} ${YY} L ${BX} ${BY} Z`}
        fill="none"
        stroke="rgba(232,200,98,0.55)"
        strokeWidth="1.2"
      />
      {/* Small ancestral square outline */}
      <path
        d={`M ${TLX} ${TLY} L ${TRX} ${TRY} L ${BRX} ${BRY} L ${BLX} ${BLY} Z`}
        fill="none"
        stroke="rgba(232,200,98,0.45)"
        strokeWidth="1.0"
        strokeDasharray="3 3"
      />

      {/* All nodes — render in a single loop */}
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
              nodeId: n.nodeId,
              num: n.num,
              tier: n.tier,
              x: n.x,
              y: n.y,
            })}
          />
        );
      })}
    </svg>
  );
}

export type { NodeMeta as DestinyNodeMeta };
