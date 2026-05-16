import Pitch from "./Pitch";

const MOCK_RUNS = [
  { x1: 38, y1: 24, x2: 72, y2: 20, type: "into_box",    led_to_shot: true  },
  { x1: 42, y1: 44, x2: 68, y2: 48, type: "into_box",    led_to_shot: false },
  { x1: 30, y1: 34, x2: 70, y2: 34, type: "final_third", led_to_shot: true  },
  { x1: 35, y1: 18, x2: 65, y2: 16, type: "final_third", led_to_shot: false },
  { x1: 40, y1: 52, x2: 75, y2: 54, type: "into_box",    led_to_shot: true  },
  { x1: 28, y1: 30, x2: 62, y2: 28, type: "final_third", led_to_shot: false },
  { x1: 45, y1: 40, x2: 80, y2: 38, type: "into_box",    led_to_shot: false },
  { x1: 32, y1: 44, x2: 66, y2: 46, type: "final_third", led_to_shot: true  },
];

function ArrowHead({ x1, y1, x2, y2, color }) {
  const angle = Math.atan2(y2 - y1, x2 - x1);
  const size = 2.2;
  const tip = { x: x2, y: y2 };
  const left  = { x: x2 - size * Math.cos(angle - Math.PI / 6), y: y2 - size * Math.sin(angle - Math.PI / 6) };
  const right = { x: x2 - size * Math.cos(angle + Math.PI / 6), y: y2 - size * Math.sin(angle + Math.PI / 6) };
  return <polygon points={`${tip.x},${tip.y} ${left.x},${left.y} ${right.x},${right.y}`} fill={color} opacity={0.9} />;
}

export default function LineBreakingCard({ data = null, dark = true, runs = MOCK_RUNS, pitchH = 240 }) {
  const border = dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.1)";
  const topRunner = data?.topRunner || "D. Popa";

  return (
    <div style={{ background: dark ? "rgba(20,20,20,0.6)" : "#fff", border, backdropFilter: "blur(6px)" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div className="label" style={{ opacity: 0.6 }}>Line Breaking Runs · Live</div>
        <span className="chip-mono" style={{ color: "var(--uc-red)" }}>{topRunner}</span>
      </div>
      {/* Pitch — fixed height */}
      <div style={{ height: pitchH }}>
        <Pitch dark={dark}>
          {runs.map((r, i) => {
            const color = r.led_to_shot ? "#22c55e" : r.type === "into_box" ? "#f59e0b" : "rgba(255,255,255,0.6)";
            const dx = r.x2 - r.x1, dy = r.y2 - r.y1;
            const len = Math.sqrt(dx * dx + dy * dy);
            const ux = dx / len, uy = dy / len;
            const ex = r.x2 - ux * 2, ey = r.y2 - uy * 2;
            return (
              <g key={i}>
                <line x1={r.x1} y1={r.y1} x2={ex} y2={ey}
                  stroke={color} strokeWidth={0.8} strokeOpacity={0.85}
                  strokeDasharray={r.led_to_shot ? "none" : "2,1"} />
                <ArrowHead x1={r.x1} y1={r.y1} x2={r.x2} y2={r.y2} color={color} />
              </g>
            );
          })}
        </Pitch>
      </div>
      {/* Insight if present */}
      {data?.insight && (
        <div style={{ padding: "8px 14px", fontSize: 11, opacity: 0.6, fontFamily: "JetBrains Mono, monospace", lineHeight: 1.5, borderTop: "1px solid rgba(255,255,255,0.06)", borderLeft: "2px solid var(--uc-red)", paddingLeft: 12 }}>
          {data.insight}
        </div>
      )}
    </div>
  );
}
