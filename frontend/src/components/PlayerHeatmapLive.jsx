import { useEffect, useState } from "react";
import Pitch from "./Pitch";
import { fetchHeatmaps } from "../lib/api";

const MOCK_HEATMAPS = [
  { num: 10, name: "I. Stoica",  pos: "LAMF", totalActions: 34, blobs: [
    { x: 60, y: 51, intensity: 0.9 }, { x: 65, y: 54, intensity: 0.7 },
    { x: 70, y: 48, intensity: 0.8 }, { x: 55, y: 53, intensity: 0.5 },
    { x: 75, y: 56, intensity: 0.6 }, { x: 80, y: 51, intensity: 0.4 },
  ]},
  { num: 11, name: "M. Thiam",   pos: "CF",   totalActions: 28, blobs: [
    { x: 80, y: 34, intensity: 0.9 }, { x: 85, y: 30, intensity: 0.7 },
    { x: 78, y: 38, intensity: 0.8 }, { x: 88, y: 34, intensity: 0.6 },
    { x: 82, y: 28, intensity: 0.5 },
  ]},
  { num: 6,  name: "O. Bic",     pos: "DMF",  totalActions: 52, blobs: [
    { x: 40, y: 33, intensity: 0.9 }, { x: 45, y: 35, intensity: 0.8 },
    { x: 38, y: 37, intensity: 0.7 }, { x: 42, y: 30, intensity: 0.6 },
    { x: 50, y: 34, intensity: 0.5 }, { x: 35, y: 34, intensity: 0.4 },
  ]},
  { num: 9,  name: "D. Popa",    pos: "AMF",  totalActions: 41, blobs: [
    { x: 62, y: 34, intensity: 0.9 }, { x: 68, y: 32, intensity: 0.8 },
    { x: 58, y: 35, intensity: 0.7 }, { x: 72, y: 34, intensity: 0.6 },
  ]},
];

export default function PlayerHeatmapLive({ dark = true, pollMs = 5000, pitchH = 240 }) {
  const [data, setData] = useState(MOCK_HEATMAPS);
  const [selected, setSelected] = useState(10);
  const border = dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.1)";

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const d = await fetchHeatmaps();
        if (active) {
          setData(d);
          if (!selected && d.length > 0) setSelected(d[0].num);
        }
      } catch {}
    };
    load();
    const t = setInterval(load, pollMs);
    return () => { active = false; clearInterval(t); };
  }, [pollMs]);

  const player = data.find((p) => p.num === selected);

  return (
    <div style={{ background: dark ? "rgba(20,20,20,0.6)" : "#fff", border, backdropFilter: "blur(6px)" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div className="label" style={{ opacity: 0.6 }}>Player Profile · Live</div>
        <select
          value={selected ?? ""}
          onChange={(e) => setSelected(Number(e.target.value))}
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 10,
            padding: "3px 6px",
            background: dark ? "#0a0a0a" : "#fff",
            border: dark ? "1px solid rgba(255,255,255,0.15)" : "1px solid rgba(0,0,0,0.15)",
            color: dark ? "white" : "black",
          }}
        >
          {data.map((p) => (
            <option key={p.num} value={p.num}>#{p.num} {p.name}</option>
          ))}
        </select>
      </div>
      {/* Pitch — fixed height */}
      <div style={{ height: pitchH }}>
        <Pitch dark={dark}>
          <defs>
            <radialGradient id="heatLive">
              <stop offset="0%"   stopColor="#E30613" stopOpacity="0.9" />
              <stop offset="50%"  stopColor="#E30613" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#E30613" stopOpacity="0" />
            </radialGradient>
          </defs>
          {player?.blobs?.map((b, i) => (
            <circle key={i} cx={b.x} cy={b.y} r={4 + b.intensity * 4} fill="url(#heatLive)" />
          ))}
        </Pitch>
      </div>
    </div>
  );
}
