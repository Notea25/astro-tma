import type { DestinyMatrixPositions } from "@/services/api";

/**
 * Destiny Matrix octagram — 8 corners + 1 center.
 *
 * Geometry (viewBox 0 0 360 360, center at 180,180, radius 150):
 * - Big diamond corners at 0°/90°/180°/270° (A left, B top, C right, D bottom)
 * - Small square corners at 45°/135°/225°/315° (F top-left, G top-right,
 *   H bottom-right, I bottom-left)
 * - Center E
 *
 * Layout matches the canonical Russian Destiny Matrix diagrams:
 *   A on the left, B on the top, C on the right, D on the bottom.
 */

export interface NodeMeta {
  /** Which positions key in DestinyMatrixPositions to read (A/B/C/.../I/E). */
  posKey: keyof DestinyMatrixPositions;
  /** Arcana number to render — derived from positions[posKey]. */
  num: number;
  /** Tag for tap callback — used to look up Russian title in the parent. */
  nodeId: string;
  /** Free or Premium tier — premium nodes show a lock when no full access. */
  tier: "free" | "premium";
  /** Cartesian (svg-space) coordinates of the node. */
  x: number;
  y: number;
}

const R = 150;
const CX = 180;
const CY = 180;

// Polar helper — angle is measured clockwise from the 12 o'clock position
// (standard astrology convention) so positions match Russian diagrams.
function polar(angleDeg: number, radius: number): [number, number] {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return [CX + radius * Math.cos(rad), CY + radius * Math.sin(rad)];
}

const [BX, BY] = polar(0, R);     // top — month
const [CX_, CY_] = polar(90, R);  // right — year/ancestry
const [DX, DY] = polar(180, R);   // bottom — personality
const [AX, AY] = polar(270, R);   // left — day

const [GX, GY] = polar(45, R);    // top-right small square
const [HX, HY] = polar(135, R);   // bottom-right
const [IX, IY] = polar(225, R);   // bottom-left
const [FX, FY] = polar(315, R);   // top-left

export const OCTAGRAM_NODES: Omit<NodeMeta, "num">[] = [
  // Big diamond (free tier — main 4 corners)
  { posKey: "A", nodeId: "A", tier: "free",    x: AX, y: AY },
  { posKey: "B", nodeId: "B", tier: "free",    x: BX, y: BY },
  { posKey: "C", nodeId: "C", tier: "free",    x: CX_, y: CY_ },
  { posKey: "D", nodeId: "D", tier: "free",    x: DX, y: DY },
  // Center (free — main mission)
  { posKey: "E", nodeId: "E", tier: "free",    x: CX, y: CY },
  // Small ancestral square (premium)
  { posKey: "F", nodeId: "F", tier: "premium", x: FX, y: FY },
  { posKey: "G", nodeId: "G", tier: "premium", x: GX, y: GY },
  { posKey: "H", nodeId: "H", tier: "premium", x: HX, y: HY },
  { posKey: "I", nodeId: "I", tier: "premium", x: IX, y: IY },
];

interface Props {
  positions: DestinyMatrixPositions;
  hasFullAccess: boolean;
  activeNodeId: string | null;
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
      {/* Big diamond (rhombus): A → B → C → D */}
      <path
        d={`M ${AX} ${AY} L ${BX} ${BY} L ${CX_} ${CY_} L ${DX} ${DY} Z`}
        fill="none"
        stroke="rgba(232,200,98,0.55)"
        strokeWidth="1.2"
      />
      {/* Small square (rotated 45°): F → G → H → I */}
      <path
        d={`M ${FX} ${FY} L ${GX} ${GY} L ${HX} ${HY} L ${IX} ${IY} Z`}
        fill="none"
        stroke="rgba(232,200,98,0.45)"
        strokeWidth="1.0"
        strokeDasharray="3 3"
      />
      {/* Cross-axes through center */}
      <line x1={AX} y1={AY} x2={CX_} y2={CY_} stroke="rgba(232,200,98,0.25)" strokeWidth="0.8" />
      <line x1={BX} y1={BY} x2={DX} y2={DY} stroke="rgba(232,200,98,0.25)" strokeWidth="0.8" />

      {/* Nodes */}
      {OCTAGRAM_NODES.map((meta) => {
        const num = positions[meta.posKey] as number;
        const isLocked = meta.tier === "premium" && !hasFullAccess;
        const isActive = activeNodeId === meta.nodeId;
        const isCenter = meta.nodeId === "E";
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
