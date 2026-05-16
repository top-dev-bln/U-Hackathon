import { useEffect, useState } from "react";
import Pitch from "./Pitch";
import { fetchPassingNetwork } from "../lib/api";

const MOCK_NETWORK = {
  nodes: [
    { num: 1,  name: "Fernandez",  pos: "GK",  x: 5,  y: 34 },
    { num: 2,  name: "Oancea",     pos: "RB",  x: 25, y: 14 },
    { num: 3,  name: "Cristea",    pos: "RCB", x: 20, y: 24 },
    { num: 4,  name: "Miron",      pos: "LCB", x: 20, y: 44 },
    { num: 5,  name: "Chipciu",    pos: "LB",  x: 25, y: 54 },
    { num: 6,  name: "Bic",        pos: "DMF", x: 40, y: 34 },
    { num: 7,  name: "Nistor",     pos: "CMF", x: 50, y: 24 },
    { num: 8,  name: "Gheorghe",   pos: "RAMF",x: 62, y: 14 },
    { num: 9,  name: "Popa",       pos: "AMF", x: 62, y: 34 },
    { num: 10, name: "Stoica",     pos: "LAMF",x: 62, y: 54 },
    { num: 11, name: "Thiam",      pos: "CF",  x: 80, y: 34 },
  ],
  edges: [
    { a: 1, b: 3, count: 12 }, { a: 1, b: 4, count: 10 },
    { a: 3, b: 6, count: 18 }, { a: 4, b: 6, count: 15 },
    { a: 2, b: 7, count: 8  }, { a: 5, b: 10, count: 9 },
    { a: 6, b: 7, count: 22 }, { a: 6, b: 9, count: 14 },
    { a: 7, b: 8, count: 11 }, { a: 7, b: 9, count: 16 },
    { a: 9, b: 11, count: 13 }, { a: 10, b: 11, count: 7 },
    { a: 8, b: 11, count: 6  },
  ],
};

export default function PassingNetwork({ dark = true, pollMs = 4000, pitchH = 240 }) {
  const [data, setData] = useState(MOCK_NETWORK);
  const [hovered, setHovered] = useState(null);
  const border = dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.1)";

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const d = await fetchPassingNetwork();
        if (active) setData(d);
      } catch {}
    };
    load();
    const t = setInterval(load, pollMs);
    return () => { active = false; clearInterval(t); };
  }, [pollMs]);

  const maxEdge = Math.max(1, ...data.edges.map((e) => e.count));
  const nodeMap = Object.fromEntries(data.nodes.map((n) => [n.num, n]));
  const totalPasses = data.edges.reduce((a, b) => a + b.count, 0);

  return (
    <div style={{ background: dark ? "rgba(20,20,20,0.6)" : "#fff", border, backdropFilter: "blur(6px)" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div className="label" style={{ opacity: 0.6 }}>Passing Network · Live</div>
        <span className="chip-mono" style={{ color: dark ? "rgba(255,255,255,0.6)" : "rgba(0,0,0,0.6)" }}>
          {totalPasses} passes
        </span>
      </div>
      {/* Pitch — fixed height */}
      <div style={{ height: pitchH }}>
        <Pitch dark={dark}>
          {data.edges.map((e, i) => {
            const a = nodeMap[e.a], b = nodeMap[e.b];
            if (!a || !b) return null;
            const w = 0.15 + 1.0 * (e.count / maxEdge);
            return (
              <line
                key={i}
                x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke={dark ? "#ffffff" : "#0a0a0a"}
                strokeOpacity={0.15 + 0.55 * (e.count / maxEdge)}
                strokeWidth={w}
              />
            );
          })}
          {data.nodes.map((n) => {
            const isHovered = hovered === n.num;
            const labelName = n.name?.split(" ").pop() ?? "";
            const fontSize = isHovered ? 3.2 : 2.3;
            const bgW = isHovered ? labelName.length * 1.9 + 2 : 9;
            const bgH = isHovered ? 3.8 : 2.8;
            const bgY = isHovered ? n.y - 6.8 : n.y - 5.2;
            const textY = isHovered ? n.y - 3.8 : n.y - 3;
            return (
              <g key={n.num}
                style={{ cursor: "pointer" }}
                onMouseEnter={() => setHovered(n.num)}
                onMouseLeave={() => setHovered(null)}
              >
                <circle
                  cx={n.x} cy={n.y} r={isHovered ? 2 : 1.4}
                  fill={n.pos === "GK" ? "#E30613" : dark ? "#ffffff" : "#0a0a0a"}
                  stroke={dark ? "#0a0a0a" : "#ffffff"}
                  strokeWidth="0.25"
                  style={{ transition: "r 0.15s" }}
                />
                <rect
                  x={n.x - bgW / 2} y={bgY}
                  width={bgW} height={bgH}
                  fill={isHovered ? "rgba(0,0,0,0.85)" : "rgba(0,0,0,0.55)"}
                  rx="0.4"
                />
                <text x={n.x} y={textY} textAnchor="middle" fontSize={fontSize} fontFamily="JetBrains Mono"
                  fill="#ffffff" fontWeight="bold" opacity="1">
                  {labelName}
                </text>
              </g>
            );
          })}
        </Pitch>
      </div>
    </div>
  );
}
