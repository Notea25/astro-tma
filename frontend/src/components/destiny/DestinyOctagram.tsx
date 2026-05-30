import type { DestinyMatrixPositions } from "@/services/api";

/**
 * Destiny Matrix octagram — extended diagram showing the full energy map.
 *
 * Layers (from outer in):
 * 1. Ancestral channels — 4 directions × 3 nodes outward from each square
 *    corner. The corner itself is the "входная" point; middle + outer
 *    sit on the same radial outside the octagram.
 * 2. Karmic tail — 3 nodes extending below the bottom diamond corner.
 * 3. Big diamond + small square (the canonical 9-node octagram).
 * 4. Inner energy icons — talents (✦), relationships (♥), finance (💰),
 *    material karma (⚖) cluster around the center showing each channel's
 *    middle ("работа") number.
 *
 * Only the 9 base nodes are tap-able. Outer/inner numbers are visual
 * orientation — their per-channel meaning is detailed in DestinyChannels
 * underneath.
 *
 * Geometry: viewBox 0 0 420 420, center (210,210).
 */

export type DestinyNodeId =
  | "day" | "month" | "year" | "bottom" | "center"
  | "top_left" | "top_right" | "bottom_right" | "bottom_left";

export interface NodeMeta {
  nodeId: DestinyNodeId;
  num: number;
  tier: "free" | "premium";
  x: number;
  y: number;
}

const CX = 210;
const CY = 210;
const R_BASE = 130;       // big diamond + small square corners
const R_CH_MID = 168;     // ancestral channel middle node
const R_CH_OUT = 202;     // ancestral channel outer node
const R_KT_MID = 168;     // karmic tail middle (under bottom)
const R_KT_OUT = 203;     // karmic tail outer (deepest karma point)

function polar(angleDeg: number, radius: number): [number, number] {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return [CX + radius * Math.cos(rad), CY + radius * Math.sin(rad)];
}

// Big diamond corners (R_BASE)
const [MX, MY] = polar(0, R_BASE);    // top    — month
const [YX, YY] = polar(90, R_BASE);   // right  — year
const [BX, BY] = polar(180, R_BASE);  // bottom — bottom
const [DX, DY] = polar(270, R_BASE);  // left   — day

// Small ancestral square corners
const [TLX, TLY] = polar(315, R_BASE);
const [TRX, TRY] = polar(45, R_BASE);
const [BRX, BRY] = polar(135, R_BASE);
const [BLX, BLY] = polar(225, R_BASE);

// Ancestral channels — middle & outer per square corner
const [TL_MX, TL_MY] = polar(315, R_CH_MID);
const [TL_OX, TL_OY] = polar(315, R_CH_OUT);
const [TR_MX, TR_MY] = polar(45, R_CH_MID);
const [TR_OX, TR_OY] = polar(45, R_CH_OUT);
const [BR_MX, BR_MY] = polar(135, R_CH_MID);
const [BR_OX, BR_OY] = polar(135, R_CH_OUT);
const [BL_MX, BL_MY] = polar(225, R_CH_MID);
const [BL_OX, BL_OY] = polar(225, R_CH_OUT);

// Karmic tail extension under bottom
const [KT_MX, KT_MY] = polar(180, R_KT_MID);
const [KT_OX, KT_OY] = polar(180, R_KT_OUT);

// Inner energy icons around the center
const ICON_R = 42;
const [TAL_X, TAL_Y] = polar(0, ICON_R);    // talents up
const [REL_X, REL_Y] = polar(45, ICON_R);   // relationships top-right
const [FIN_X, FIN_Y] = polar(135, ICON_R);  // finance bottom-right
const [MK_X, MK_Y] = polar(225, ICON_R);    // material karma bottom-left

const TAP_NODES: ReadonlyArray<Omit<NodeMeta, "num">> = [
  { nodeId: "day",          tier: "free",    x: DX,  y: DY  },
  { nodeId: "month",        tier: "free",    x: MX,  y: MY  },
  { nodeId: "year",         tier: "free",    x: YX,  y: YY  },
  { nodeId: "bottom",       tier: "free",    x: BX,  y: BY  },
  { nodeId: "center",       tier: "free",    x: CX,  y: CY  },
  { nodeId: "top_left",     tier: "premium", x: TLX, y: TLY },
  { nodeId: "top_right",    tier: "premium", x: TRX, y: TRY },
  { nodeId: "bottom_right", tier: "premium", x: BRX, y: BRY },
  { nodeId: "bottom_left",  tier: "premium", x: BLX, y: BLY },
];

function nodeNumber(positions: DestinyMatrixPositions, id: DestinyNodeId): number {
  switch (id) {
    case "day":          return positions.personality.day;
    case "month":        return positions.personality.month;
    case "year":         return positions.personality.year;
    case "bottom":       return positions.personality.bottom;
    case "center":       return positions.personality.center;
    case "top_left":     return positions.ancestral_square.top_left;
    case "top_right":    return positions.ancestral_square.top_right;
    case "bottom_right": return positions.ancestral_square.bottom_right;
    case "bottom_left":  return positions.ancestral_square.bottom_left;
  }
}

interface SmallNodeProps {
  x: number;
  y: number;
  num: number;
  size?: "sm" | "xs";
  hidden?: boolean;
}

function ChannelNode({ x, y, num, size = "sm", hidden }: SmallNodeProps) {
  const r = size === "xs" ? 11 : 14;
  return (
    <g className="destiny-octagram__chnode" opacity={hidden ? 0.25 : 1}>
      <circle
        cx={x}
        cy={y}
        r={r}
        fill="#0e0b20"
        stroke="rgba(232,200,98,0.55)"
        strokeWidth="1"
      />
      <text
        x={x}
        y={y}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={size === "xs" ? 11 : 13}
        fill="#e8c862"
        fontWeight="500"
      >
        {num}
      </text>
    </g>
  );
}

interface IconNodeProps {
  x: number;
  y: number;
  num: number;
  icon: string;
  hidden?: boolean;
}

function IconNode({ x, y, num, icon, hidden }: IconNodeProps) {
  return (
    <g opacity={hidden ? 0.3 : 1}>
      <circle
        cx={x}
        cy={y}
        r={12}
        fill="rgba(14,11,32,0.95)"
        stroke="rgba(232,200,98,0.8)"
        strokeWidth="0.9"
      />
      <text
        x={x}
        y={y - 1}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={11}
        fill="#e8c862"
        fontWeight="600"
      >
        {num}
      </text>
      <text
        x={x + 12}
        y={y - 10}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={9}
        fill="rgba(232,200,98,0.85)"
      >
        {icon}
      </text>
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
  const ch = positions.channels;
  const hideAncestral = !hasFullAccess;

  return (
    <svg
      viewBox="0 0 420 420"
      className="destiny-octagram"
      role="img"
      aria-label="Октаграмма матрицы судьбы"
    >
      {/* Radial guide rays from center through each square corner — subtle */}
      <line x1={CX} y1={CY} x2={TL_OX} y2={TL_OY} stroke="rgba(232,200,98,0.12)" strokeWidth="0.6" strokeDasharray="2 4" />
      <line x1={CX} y1={CY} x2={TR_OX} y2={TR_OY} stroke="rgba(232,200,98,0.12)" strokeWidth="0.6" strokeDasharray="2 4" />
      <line x1={CX} y1={CY} x2={BR_OX} y2={BR_OY} stroke="rgba(232,200,98,0.12)" strokeWidth="0.6" strokeDasharray="2 4" />
      <line x1={CX} y1={CY} x2={BL_OX} y2={BL_OY} stroke="rgba(232,200,98,0.12)" strokeWidth="0.6" strokeDasharray="2 4" />

      {/* Cross-axes through center */}
      <line x1={DX} y1={DY} x2={YX} y2={YY} stroke="rgba(232,200,98,0.22)" strokeWidth="0.8" />
      <line x1={MX} y1={MY} x2={KT_OX} y2={KT_OY} stroke="rgba(232,200,98,0.22)" strokeWidth="0.8" />

      {/* Big diamond (rhombus): day → month → year → bottom */}
      <path
        d={`M ${DX} ${DY} L ${MX} ${MY} L ${YX} ${YY} L ${BX} ${BY} Z`}
        fill="none"
        stroke="rgba(232,200,98,0.55)"
        strokeWidth="1.2"
      />
      {/* Small ancestral square (rotated 45°) */}
      <path
        d={`M ${TLX} ${TLY} L ${TRX} ${TRY} L ${BRX} ${BRY} L ${BLX} ${BLY} Z`}
        fill="none"
        stroke="rgba(232,200,98,0.45)"
        strokeWidth="1.0"
        strokeDasharray="3 3"
      />

      {/* Ancestral channel nodes — 4 directions × 2 each */}
      {ch.ancestral_father_talents?.length >= 3 && (
        <>
          <ChannelNode x={TL_MX} y={TL_MY} num={ch.ancestral_father_talents[1]} hidden={hideAncestral} />
          <ChannelNode x={TL_OX} y={TL_OY} num={ch.ancestral_father_talents[2]} size="xs" hidden={hideAncestral} />
        </>
      )}
      {ch.ancestral_mother_talents?.length >= 3 && (
        <>
          <ChannelNode x={TR_MX} y={TR_MY} num={ch.ancestral_mother_talents[1]} hidden={hideAncestral} />
          <ChannelNode x={TR_OX} y={TR_OY} num={ch.ancestral_mother_talents[2]} size="xs" hidden={hideAncestral} />
        </>
      )}
      {ch.ancestral_mother_karma?.length >= 3 && (
        <>
          <ChannelNode x={BR_MX} y={BR_MY} num={ch.ancestral_mother_karma[1]} hidden={hideAncestral} />
          <ChannelNode x={BR_OX} y={BR_OY} num={ch.ancestral_mother_karma[2]} size="xs" hidden={hideAncestral} />
        </>
      )}
      {ch.ancestral_father_karma?.length >= 3 && (
        <>
          <ChannelNode x={BL_MX} y={BL_MY} num={ch.ancestral_father_karma[1]} hidden={hideAncestral} />
          <ChannelNode x={BL_OX} y={BL_OY} num={ch.ancestral_father_karma[2]} size="xs" hidden={hideAncestral} />
        </>
      )}

      {/* Karmic tail — bottom + 2 extension nodes (highlighted) */}
      {ch.karmic_tail?.length >= 3 && (
        <>
          <ChannelNode x={KT_MX} y={KT_MY} num={ch.karmic_tail[1]} />
          <g>
            <circle
              cx={KT_OX}
              cy={KT_OY}
              r={15}
              fill="#0e0b20"
              stroke="#d44a4a"
              strokeWidth="1.4"
            />
            <text
              x={KT_OX}
              y={KT_OY}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={13}
              fill="#e8c862"
              fontWeight="600"
            >
              {ch.karmic_tail[2]}
            </text>
          </g>
        </>
      )}

      {/* Inner energy icons around the center (talents/love/money/karma) */}
      {hasFullAccess && (
        <>
          {ch.talents?.length >= 2 && (
            <IconNode x={TAL_X} y={TAL_Y} num={ch.talents[1]} icon="✦" />
          )}
          {ch.relationships?.length >= 2 && (
            <IconNode x={REL_X} y={REL_Y} num={ch.relationships[1]} icon="♥" />
          )}
          {ch.finance?.length >= 2 && (
            <IconNode x={FIN_X} y={FIN_Y} num={ch.finance[1]} icon="₽" />
          )}
          {ch.material_karma?.length >= 2 && (
            <IconNode x={MK_X} y={MK_Y} num={ch.material_karma[1]} icon="⚖" />
          )}
        </>
      )}

      {/* Base 9 tap-able nodes */}
      {TAP_NODES.map((meta) => {
        const num = nodeNumber(positions, meta.nodeId);
        const isLocked = meta.tier === "premium" && !hasFullAccess;
        const isActive = activeNodeId === meta.nodeId;
        const isCenter = meta.nodeId === "center";
        const r = isCenter ? 30 : 24;
        const otherActive = activeNodeId !== null && !isActive;

        return (
          <g
            key={meta.nodeId}
            className={
              `destiny-octagram__node` +
              (isActive ? " is-active" : "") +
              (otherActive ? " is-faded" : "") +
              (isLocked ? " is-locked" : "")
            }
            onClick={() => onNodeTap({ ...meta, num })}
            style={{ cursor: "pointer" }}
          >
            <circle
              cx={meta.x}
              cy={meta.y}
              r={r}
              fill="#0e0b20"
              stroke={isActive ? "#e8c862" : "rgba(232,200,98,0.85)"}
              strokeWidth={isActive ? 2.4 : 1.5}
            />
            {isLocked ? (
              <text
                x={meta.x}
                y={meta.y}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize="20"
                fill="rgba(232,200,98,0.55)"
                style={{ fontFamily: "serif" }}
              >
                ?
              </text>
            ) : (
              <text
                x={meta.x}
                y={meta.y}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={isCenter ? 26 : 19}
                fill="#e8c862"
                fontWeight="600"
              >
                {num}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

export type { NodeMeta as DestinyNodeMeta };
