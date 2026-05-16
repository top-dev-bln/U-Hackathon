import { useEffect, useState } from "react";
import Pitch from "./Pitch";
import { fetchHeatmaps } from "../lib/api";

export default function Heatmap({ dark = false }) {
  const [data, setData] = useState([]);
  const [selected, setSelected] = useState(null);
  const border = dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.1)";

  useEffect(() => {
    fetchHeatmaps()
      .then((d) => { setData(d); setSelected(d[0]?.num ?? null); })
      .catch(() => {});
  }, []);

  const player = data.find((p) => p.num === selected);

  return (
    <div style={{ padding: 20, background: dark ? "rgba(20,20,20,0.6)" : "#fff", border }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div className="label" style={{ opacity: 0.6 }}>Player Heatmaps</div>
        <select
          value={selected ?? ""}
          onChange={(e) => setSelected(Number(e.target.value))}
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 11,
            padding: "4px 8px",
            background: dark ? "#0a0a0a" : "#fff",
            border: dark ? "1px solid rgba(255,255,255,0.15)" : "1px solid rgba(0,0,0,0.15)",
            color: dark ? "white" : "black",
          }}
        >
          {data.map((p) => (
            <option key={p.num} value={p.num}>#{p.num} {p.name} ({p.pos})</option>
          ))}
        </select>
      </div>

      <div style={{ height: 420 }}>
        <Pitch dark={dark}>
          <defs>
            <radialGradient id="heat">
              <stop offset="0%" stopColor="#E30613" stopOpacity="0.85" />
              <stop offset="50%" stopColor="#E30613" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#E30613" stopOpacity="0" />
            </radialGradient>
          </defs>
          {player?.blobs?.map((b, i) => (
            <circle key={i} cx={b.x} cy={b.y} r={5 + b.intensity * 5} fill="url(#heat)" />
          ))}
        </Pitch>
      </div>
    </div>
  );
}
