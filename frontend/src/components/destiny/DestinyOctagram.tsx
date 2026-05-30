import type { DestinyMatrixPositions } from "@/services/api";

/**
 * Destiny Matrix octagram — classic 8-point star.
 *
 * Geometry per spec: viewBox 600×600, center (300,300). Two overlapping
 * squares with the same circumscribed radius (~230):
 *   • DIAMOND (diagonal square): vertices at top/right/bottom/left.
 *   • STRAIGHT square (ancestral): vertices at TL/TR/BR/BL.
 *
 * Numbers come dynamically from positions; nothing is hardcoded.
 */

export type DestinyNodeId =
  | "day" | "month" | "year" | "bottom" | "center"
  | "top_left" | "top_right" | "bottom_right" | "bottom_left"
  // 3 dots per cardinal axis (talents/material_karma/karmic_tail/parental)
  | "month_1" | "month_2" | "month_3"
  | "year_1"  | "year_2"  | "year_3"
  | "bottom_1" | "bottom_2" | "bottom_3"
  | "day_1"   | "day_2"   | "day_3"
  // 3 dots per diagonal
  | "aft_1" | "aft_2" | "aft_3"   // father talents — TL
  | "amt_1" | "amt_2" | "amt_3"   // mother talents — TR
  | "fin_1" | "fin_2" | "fin_3"   // finance — BR
  | "afk_1" | "afk_2" | "afk_3";  // father karma — BL

export interface NodeMeta {
  nodeId: DestinyNodeId;
  num: number;
  tier: "free" | "premium";
  x: number;
  y: number;
}

// ── Coordinates per spec ───────────────────────────────────────────────
const VIEW = 600;
const CX = 300;
const CY = 300;

// Diamond vertices
const TOP:    [number, number] = [300,  70];
const RIGHT:  [number, number] = [530, 300];
const BOTTOM: [number, number] = [300, 530];
const LEFT:   [number, number] = [ 70, 300];
// Straight square vertices
const TL: [number, number] = [140, 140];
const TR: [number, number] = [460, 140];
const BR: [number, number] = [460, 460];
const BL: [number, number] = [140, 460];

// Age ring sits outside the octagram
const R_AGE_RING  = 268;
const R_AGE_TICK  = 276;
const R_AGE_LABEL = 286;

/** Position a point on the segment from vertex v to center, at fraction t
 *  (t=0 at vertex, t=1 at center). */
function along(v: [number, number], t: number): [number, number] {
  return [v[0] + t * (CX - v[0]), v[1] + t * (CY - v[1])];
}

// Cardinal axis points at 1/4, 1/2, 3/4 from vertex to center
const TOP_1 = along(TOP, 0.25);
const TOP_2 = along(TOP, 0.50);
const TOP_3 = along(TOP, 0.75);
const RIGHT_1 = along(RIGHT, 0.25);
const RIGHT_2 = along(RIGHT, 0.50);
const RIGHT_3 = along(RIGHT, 0.75);
const BOT_1 = along(BOTTOM, 0.25);
const BOT_2 = along(BOTTOM, 0.50);
const BOT_3 = along(BOTTOM, 0.75);
const LEFT_1 = along(LEFT, 0.25);
const LEFT_2 = along(LEFT, 0.50);
const LEFT_3 = along(LEFT, 0.75);
// Diagonal axis points
const TL_1 = along(TL, 0.25);
const TL_2 = along(TL, 0.50);
const TL_3 = along(TL, 0.75);
const TR_1 = along(TR, 0.25);
const TR_2 = along(TR, 0.50);
const TR_3 = along(TR, 0.75);
const BR_1 = along(BR, 0.25);
const BR_2 = along(BR, 0.50);
const BR_3 = along(BR, 0.75);
const BL_1 = along(BL, 0.25);
const BL_2 = along(BL, 0.50);
const BL_3 = along(BL, 0.75);

// ── Palette ────────────────────────────────────────────────────────────
const COLOR_LINE      = "rgba(200, 195, 180, 0.6)";   // thin grey lines
const COLOR_LINE_ACC  = "rgba(232, 200, 98, 0.75)";   // accent for diamond outline
const COLOR_CENTER    = "#e8c862";                    // gold — center
const COLOR_BASE      = "#e8c862";                    // gold for base nodes
const COLOR_KARMA     = "#e07b6a";                    // red — bottom/karma
const COLOR_DOT       = "rgba(232, 200, 98, 0.95)";   // small dots default
const COLOR_DOT_RED   = "#e07b6a";                    // karmic dots
const COLOR_LABEL_DIM = "rgba(220, 215, 200, 0.55)";  // muted side labels
const COLOR_LABEL_INK = "rgba(232, 200, 98, 0.9)";    // accent labels

type NodeKind = "main-lg" | "main-md" | "dot";

interface NodeDef {
  nodeId: DestinyNodeId;
  num: number;
  tier: "free" | "premium";
  x: number;
  y: number;
  kind: NodeKind;
  color?: string;
}

function toArcana(n: number): number {
  while (n > 22) n = String(n).split("").reduce((s, d) => s + Number(d), 0);
  return n || 22;
}

function buildNodes(p: DestinyMatrixPositions): NodeDef[] {
  const per = p.personality;
  const sq  = p.ancestral_square;
  const ch  = p.channels;

  // Some channels are 3-tuples. Pad with center if backend returned fewer
  // (shouldn't happen but defensive).
  const triple = (arr: number[] | undefined): [number, number, number] => {
    const a = arr ?? [];
    return [a[0] ?? per.center, a[1] ?? per.center, a[2] ?? per.center];
  };
  const tal  = triple(ch.talents);
  const mk   = triple(ch.material_karma);
  const kt   = triple(ch.karmic_tail);
  const par  = triple(ch.parental);
  const aft  = triple(ch.ancestral_father_talents);
  const amt  = triple(ch.ancestral_mother_talents);
  const fin  = triple(ch.finance);
  const afk  = triple(ch.ancestral_father_karma);

  // Helper: a small dot
  const dot = (
    nodeId: DestinyNodeId,
    num: number,
    point: [number, number],
    color?: string,
  ): NodeDef => ({
    nodeId, num: toArcana(num), tier: "premium",
    x: point[0], y: point[1], kind: "dot", color,
  });

  return [
    // ── Main 9 nodes (large circles) ──
    { nodeId: "day",    num: per.day,    tier: "free", x: LEFT[0],   y: LEFT[1],   kind: "main-lg", color: COLOR_BASE },
    { nodeId: "month",  num: per.month,  tier: "free", x: TOP[0],    y: TOP[1],    kind: "main-lg", color: COLOR_BASE },
    { nodeId: "year",   num: per.year,   tier: "free", x: RIGHT[0],  y: RIGHT[1],  kind: "main-lg", color: COLOR_BASE },
    { nodeId: "bottom", num: per.bottom, tier: "free", x: BOTTOM[0], y: BOTTOM[1], kind: "main-lg", color: COLOR_KARMA },
    { nodeId: "center", num: per.center, tier: "free", x: CX,        y: CY,        kind: "main-md", color: COLOR_CENTER },
    { nodeId: "top_left",     num: sq.top_left,     tier: "premium", x: TL[0], y: TL[1], kind: "main-lg", color: COLOR_BASE },
    { nodeId: "top_right",    num: sq.top_right,    tier: "premium", x: TR[0], y: TR[1], kind: "main-lg", color: COLOR_BASE },
    { nodeId: "bottom_right", num: sq.bottom_right, tier: "premium", x: BR[0], y: BR[1], kind: "main-lg", color: COLOR_BASE },
    { nodeId: "bottom_left",  num: sq.bottom_left,  tier: "premium", x: BL[0], y: BL[1], kind: "main-lg", color: COLOR_BASE },

    // ── Cardinal axes (3 dots each, 1/4 → 3/4 toward center) ──
    dot("month_1", tal[0], TOP_1),
    dot("month_2", tal[1], TOP_2),
    dot("month_3", tal[2], TOP_3),
    dot("year_1",  mk[0],  RIGHT_1),
    dot("year_2",  mk[1],  RIGHT_2),
    dot("year_3",  mk[2],  RIGHT_3),
    dot("bottom_1", kt[0], BOT_1, COLOR_DOT_RED),
    dot("bottom_2", kt[1], BOT_2, COLOR_DOT_RED),
    dot("bottom_3", kt[2], BOT_3, COLOR_DOT_RED),
    dot("day_1",   par[0], LEFT_1),
    dot("day_2",   par[1], LEFT_2),
    dot("day_3",   par[2], LEFT_3),

    // ── Diagonal channels (3 dots each) ──
    dot("aft_1", aft[0], TL_1),
    dot("aft_2", aft[1], TL_2),
    dot("aft_3", aft[2], TL_3),
    dot("amt_1", amt[0], TR_1),
    dot("amt_2", amt[1], TR_2),
    dot("amt_3", amt[2], TR_3),
    dot("fin_1", fin[0], BR_1),
    dot("fin_2", fin[1], BR_2),
    dot("fin_3", fin[2], BR_3),
    dot("afk_1", afk[0], BL_1),
    dot("afk_2", afk[1], BL_2),
    dot("afk_3", afk[2], BL_3),
  ];
}

// ── Age ring (0..80, 10-year nodes) ────────────────────────────────────
const AGE_NODE_YEARS = [0, 10, 20, 30, 40, 50, 60, 70];
const AGE_MINOR_YEARS = Array.from({ length: 80 }, (_, i) => i + 1)
  .filter((y) => y % 10 !== 0);

function polarFromCenter(angleDeg: number, radius: number): [number, number] {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return [CX + radius * Math.cos(rad), CY + radius * Math.sin(rad)];
}

function ageAngle(years: number): number {
  return (270 + years * 4.5) % 360;
}

function AgeRing() {
  return (
    <g data-part="age-ring">
      <circle cx={CX} cy={CY} r={R_AGE_RING}
        fill="none" stroke="rgba(232,200,98,0.35)" strokeWidth="0.9" />
      {AGE_MINOR_YEARS.map((y) => {
        const ang = ageAngle(y);
        const inner = polarFromCenter(ang, R_AGE_RING);
        const outer = polarFromCenter(ang, R_AGE_TICK - 2);
        return (
          <line key={`min-${y}`}
            x1={inner[0]} y1={inner[1]} x2={outer[0]} y2={outer[1]}
            stroke="rgba(232,200,98,0.3)" strokeWidth="0.45" />
        );
      })}
      {AGE_NODE_YEARS.map((y) => {
        const ang = ageAngle(y);
        const inner = polarFromCenter(ang, R_AGE_RING - 3);
        const outer = polarFromCenter(ang, R_AGE_TICK + 3);
        const labelPos = polarFromCenter(ang, R_AGE_LABEL);
        const ringPos = polarFromCenter(ang, R_AGE_RING);
        return (
          <g key={`node-${y}`}>
            <line x1={inner[0]} y1={inner[1]} x2={outer[0]} y2={outer[1]}
              stroke="rgba(232,200,98,0.85)" strokeWidth="1.4" />
            <circle cx={ringPos[0]} cy={ringPos[1]} r="3.2"
              fill="#0e0b20" stroke="rgba(232,200,98,0.9)" strokeWidth="1" />
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

// ── Rendered node ──────────────────────────────────────────────────────
interface RenderedNodeProps {
  node: NodeDef;
  locked: boolean;
  active: boolean;
  faded: boolean;
  onTap: (n: NodeDef) => void;
}

function RenderedNode({ node, locked, active, faded, onTap }: RenderedNodeProps) {
  const isMain = node.kind === "main-lg" || node.kind === "main-md";
  const radius = node.kind === "main-lg" ? 26 : node.kind === "main-md" ? 22 : 4;
  const tapR = Math.max(radius + 6, 18);

  const baseStroke = node.color ?? COLOR_BASE;
  const stroke = active ? COLOR_CENTER : baseStroke;
  const strokeWidth = active ? 2.6 : (isMain ? 1.8 : 0);
  const fill = isMain ? "#0e0b20" : (node.color ?? COLOR_DOT);

  const className =
    "destiny-octagram__node" +
    (active ? " is-active" : "") +
    (faded ? " is-faded" : "") +
    (locked ? " is-locked" : "");

  // Small dots: show the number BESIDE the dot, not inside.
  if (!isMain) {
    // Offset the label outward from center, perpendicular to the radial.
    const dx = node.x - CX;
    const dy = node.y - CY;
    const len = Math.hypot(dx, dy) || 1;
    // perpendicular vector (rotate 90°): (-dy, dx) normalized
    const px = -dy / len;
    const py = dx / len;
    const labelX = node.x + px * 9;
    const labelY = node.y + py * 9;
    return (
      <g className={className} onClick={() => onTap(node)} style={{ cursor: "pointer" }}>
        <circle cx={node.x} cy={node.y} r={radius}
          fill={locked ? "#0e0b20" : fill}
          stroke={locked ? "rgba(232,200,98,0.45)" : "none"}
          strokeWidth={locked ? 1 : 0} />
        {!locked && (
          <text x={labelX} y={labelY}
            textAnchor="middle" dominantBaseline="central"
            fontSize="11" fill={node.color ?? "rgba(232,200,98,0.95)"}
            fontWeight={500}
            style={{ fontFamily: "Inter, system-ui, sans-serif" }}>
            {node.num}
          </text>
        )}
        <circle cx={node.x} cy={node.y} r={tapR}
          fill="transparent" pointerEvents="all" />
      </g>
    );
  }

  // Main nodes: number inside the circle.
  const fontSize = node.kind === "main-md" ? 26 : 22;
  return (
    <g className={className} onClick={() => onTap(node)} style={{ cursor: "pointer" }}>
      <circle cx={node.x} cy={node.y} r={radius}
        fill={fill} stroke={stroke} strokeWidth={strokeWidth} />
      {locked ? (
        <text x={node.x} y={node.y} textAnchor="middle" dominantBaseline="central"
          fontSize="16" fill="rgba(232,200,98,0.55)">?</text>
      ) : (
        <text x={node.x} y={node.y} textAnchor="middle" dominantBaseline="central"
          fontSize={fontSize} fill={node.color ?? COLOR_CENTER} fontWeight={600}
          style={{ fontFamily: "Playfair Display, serif" }}>
          {node.num}
        </text>
      )}
      <circle cx={node.x} cy={node.y} r={tapR}
        fill="transparent" pointerEvents="all" />
    </g>
  );
}

// ── Diagonal-line text label, rotated so it reads along the line ───────
interface DiagLabelProps {
  from: [number, number];
  to:   [number, number];
  text: string;
  t?: number;         // fraction along the line (default 0.55)
  offset?: number;    // perpendicular offset
  color?: string;
}

function DiagLabel({ from, to, text, t = 0.55, offset = 12, color }: DiagLabelProps) {
  const x = from[0] + t * (to[0] - from[0]);
  const y = from[1] + t * (to[1] - from[1]);
  const dx = to[0] - from[0];
  const dy = to[1] - from[1];
  // Keep text upright-ish: flip rotation if it would be upside-down.
  let angle = (Math.atan2(dy, dx) * 180) / Math.PI;
  if (angle > 90) angle -= 180;
  if (angle < -90) angle += 180;
  // Offset perpendicular to the line
  const len = Math.hypot(dx, dy) || 1;
  const ox = (-dy / len) * offset;
  const oy = (dx / len) * offset;
  return (
    <text
      x={x + ox} y={y + oy}
      transform={`rotate(${angle} ${x + ox} ${y + oy})`}
      textAnchor="middle" dominantBaseline="central"
      fontSize="10" fontStyle="italic"
      fill={color ?? COLOR_LABEL_DIM}
      style={{ fontFamily: "Inter, system-ui, sans-serif", letterSpacing: "0.02em" }}
    >
      {text}
    </text>
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
      <AgeRing />

      {/* ── Crossing axes through center ── */}
      <line x1={LEFT[0]} y1={LEFT[1]} x2={RIGHT[0]} y2={RIGHT[1]}
        stroke={COLOR_LINE} strokeWidth="1" />
      <line x1={TOP[0]} y1={TOP[1]} x2={BOTTOM[0]} y2={BOTTOM[1]}
        stroke={COLOR_LINE} strokeWidth="1" />
      <line x1={TL[0]} y1={TL[1]} x2={BR[0]} y2={BR[1]}
        stroke={COLOR_LINE} strokeWidth="1" />
      <line x1={TR[0]} y1={TR[1]} x2={BL[0]} y2={BL[1]}
        stroke={COLOR_LINE} strokeWidth="1" />

      {/* ── Diamond (diagonal square) outline ── */}
      <path
        d={`M ${LEFT[0]} ${LEFT[1]} L ${TOP[0]} ${TOP[1]} L ${RIGHT[0]} ${RIGHT[1]} L ${BOTTOM[0]} ${BOTTOM[1]} Z`}
        fill="none" stroke={COLOR_LINE_ACC} strokeWidth="1.3"
      />
      {/* ── Straight ancestral square outline ── */}
      <path
        d={`M ${TL[0]} ${TL[1]} L ${TR[0]} ${TR[1]} L ${BR[0]} ${BR[1]} L ${BL[0]} ${BL[1]} Z`}
        fill="none" stroke={COLOR_LINE_ACC} strokeWidth="1.3"
      />

      {/* ── Side-of-world labels (outside the figure) ── */}
      <text x={TOP[0]} y={TOP[1] - 32} textAnchor="middle"
        fontSize="14" fill={COLOR_LABEL_DIM}
        style={{ fontFamily: "Inter, system-ui, sans-serif", letterSpacing: "0.06em" }}>
        небо
      </text>
      <text x={BOTTOM[0]} y={BOTTOM[1] + 38} textAnchor="middle"
        fontSize="14" fill={COLOR_LABEL_DIM}
        style={{ fontFamily: "Inter, system-ui, sans-serif", letterSpacing: "0.06em" }}>
        небо
      </text>
      <text x={LEFT[0] - 30} y={LEFT[1]} textAnchor="end" dominantBaseline="central"
        fontSize="14" fill={COLOR_LABEL_DIM}
        style={{ fontFamily: "Inter, system-ui, sans-serif", letterSpacing: "0.06em" }}>
        земля
      </text>
      <text x={RIGHT[0] + 30} y={RIGHT[1]} textAnchor="start" dominantBaseline="central"
        fontSize="14" fill={COLOR_LABEL_DIM}
        style={{ fontFamily: "Inter, system-ui, sans-serif", letterSpacing: "0.06em" }}>
        земля
      </text>

      {/* ── Diagonal channel labels ── */}
      <DiagLabel from={TL} to={[CX, CY]} text="род отца" t={0.45} offset={-14} />
      <DiagLabel from={TR} to={[CX, CY]} text="род матери" t={0.45} offset={14} />
      <DiagLabel from={[CX, CY]} to={BR} text="вход денег" t={0.45} offset={-14}
        color={COLOR_LABEL_INK} />
      <DiagLabel from={[CX, CY]} to={BR} text="вход партнёров" t={0.75} offset={14}
        color={COLOR_LABEL_INK} />

      {/* ── All nodes ── */}
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
