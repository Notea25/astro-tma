import type { DestinyMatrixPositions } from "@/services/api";

/**
 * Destiny Matrix octagram — 8 corners + 1 center.
 *
 * Geometry (viewBox 0 0 360 360, center at 180,180, radius 150):
 * - Big diamond corners at 0°/90°/180°/270°
 *   (day=left, month=top, year=right, bottom=bottom)
 * - Small ancestral square corners at 45°/135°/225°/315°
 *   (top_left, top_right, bottom_right, bottom_left)
 * - Center = "center"
 *
 * Tap a node → parent opens a bottom-sheet with the per-context arcana
 * description. nodeId is what the parent uses to look up the Russian title
 * and pick the right context for the meaning lookup.
 */

/** Tap-id used to look up the Russian title and arcana context. */
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

const R = 150;
const CX = 180;
const CY = 180;

function polar(angleDeg: number, radius: number): [number, number] {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return [CX + radius * Math.cos(rad), CY + radius * Math.sin(rad)];
}

const [MX, MY] = polar(0, R);     // top  — month
const [YX, YY] = polar(90, R);    // right — year
const [BX, BY] = polar(180, R);   // bottom — bottom
const [DX, DY] = polar(270, R);   // left  — day

const [TRX, TRY] = polar(45, R);  // top-right ancestral
const [BRX, BRY] = polar(135, R); // bottom-right
const [BLX, BLY] = polar(225, R); // bottom-left
const [TLX, TLY] = polar(315, R); // top-left

const NODE_LAYOUT: ReadonlyArray<Omit<NodeMeta, "num">> = [
  // Big diamond — free
  { nodeId: "day",          tier: "free",    x: DX,  y: DY  },
  { nodeId: "month",        tier: "free",    x: MX,  y: MY  },
  { nodeId: "year",         tier: "free",    x: YX,  y: YY  },
  { nodeId: "bottom",       tier: "free",    x: BX,  y: BY  },
  { nodeId: "center",       tier: "free",    x: CX,  y: CY  },
  // Small ancestral square — premium
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

interface Props {
  positions: DestinyMatrixPositions;
  hasFullAccess: boolean;
  activeNodeId: DestinyNodeId | null;
  onNodeTap: (node: NodeMeta) => void;
}

export function DestinyOctagram({
  positions, hasFullAccess, activeNodeId, onNodeTap,
}: Props) {
  return (
    <svg
      viewBox="0 0 360 360"
      className="destiny-octagram"
      role="img"
      aria-label="Октаграмма матрицы судьбы"
    >
      {/* Big diamond (rhombus): day → month → year → bottom */}
      <path
        d={`M ${DX} ${DY} L ${MX} ${MY} L ${YX} ${YY} L ${BX} ${BY} Z`}
        fill="none"
        stroke="rgba(232,200,98,0.55)"
        strokeWidth="1.2"
      />
      {/* Small ancestral square (rotated 45°): TL → TR → BR → BL */}
      <path
        d={`M ${TLX} ${TLY} L ${TRX} ${TRY} L ${BRX} ${BRY} L ${BLX} ${BLY} Z`}
        fill="none"
        stroke="rgba(232,200,98,0.45)"
        strokeWidth="1.0"
        strokeDasharray="3 3"
      />
      {/* Cross-axes through center */}
      <line x1={DX} y1={DY} x2={YX} y2={YY} stroke="rgba(232,200,98,0.25)" strokeWidth="0.8" />
      <line x1={MX} y1={MY} x2={BX} y2={BY} stroke="rgba(232,200,98,0.25)" strokeWidth="0.8" />

      {/* Nodes */}
      {NODE_LAYOUT.map((meta) => {
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
              stroke={isActive ? "#e8c862" : "rgba(232,200,98,0.7)"}
              strokeWidth={isActive ? 2.2 : 1.3}
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
                fontSize={isCenter ? 24 : 18}
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
