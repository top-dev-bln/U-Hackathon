import { useState } from "react";
import PressingGauge from "./PressingGauge";
import PassingNetwork from "./PassingNetwork";
import AttackingPatternsCard from "./AttackingPatternsCard";
import LineBreakingCard from "./LineBreakingCard";
import PlayerHeatmapLive from "./PlayerHeatmapLive";

export default function LiveMode({ state }) {
  if (!state) {
    return (
      <div
        style={{
          padding: "48px 32px",
          color: "rgba(255,255,255,0.4)",
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 13,
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: "var(--uc-red)",
            display: "inline-block",
            animation: "pulse-red 1.6s infinite",
          }}
        />
        Connecting to live match feed…
      </div>
    );
  }

  const PITCH_H = 220;
  const [expanded, setExpanded] = useState(null); // "passing" | "linebreaking" | "heatmap"

  const pitchCards = {
    passing: {
      legend: [
        { color: "#ffffff", label: "Passing lane", opacity: 0.6 },
        { color: "#E30613", label: "Goalkeeper" },
        { color: "#ffffff", label: "Outfield player" },
      ],
      note: "Line thickness = number of passes between players. Thicker = stronger connection.",
      component: (h) => <PassingNetwork dark pollMs={4000} pitchH={h} />,
    },
    linebreaking: {
      legend: [
        { color: "#22c55e", label: "Led to shot" },
        { color: "#f59e0b", label: "Into box" },
        { color: "rgba(255,255,255,0.6)", label: "Final third" },
      ],
      note: "Arrows show progressive runs that broke the opponent's defensive line.",
      component: (h) => <LineBreakingCard data={state.line_breaking} dark pitchH={h} />,
    },
    heatmap: {
      legend: [
        { color: "#E30613", label: "High activity zone", opacity: 0.9 },
        { color: "#E30613", label: "Medium activity", opacity: 0.45 },
      ],
      note: "Heatmap shows where the selected player was most active during the match.",
      component: (h) => <PlayerHeatmapLive dark pollMs={5000} pitchH={h} />,
    },
  };

  return (
    <div style={{ padding: "20px 28px", display: "flex", flexDirection: "column", gap: 16 }}>

      {/* MODAL OVERLAY */}
      {expanded && (
        <div
          onClick={() => setExpanded(null)}
          style={{
            position: "fixed", inset: 0, zIndex: 1000,
            background: "rgba(0,0,0,0.82)",
            display: "flex", alignItems: "center", justifyContent: "center",
            backdropFilter: "blur(4px)",
            animation: "fadeIn 0.18s ease",
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: "min(90vw, 900px)",
              display: "flex", flexDirection: "column",
              animation: "scaleIn 0.18s ease",
            }}
          >
            {pitchCards[expanded].component("560px")}
            <PitchLegend items={pitchCards[expanded].legend} note={pitchCards[expanded].note} />
            <div style={{ textAlign: "center", marginTop: 10, fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: "rgba(255,255,255,0.3)" }}>
              click outside to close
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fadeIn  { from { opacity: 0 } to { opacity: 1 } }
        @keyframes scaleIn { from { transform: scale(0.93) } to { transform: scale(1) } }
      `}</style>

      {/* ROW 1 — Pressing + Attacking Patterns + Ball Losses */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        <PressingGauge data={state.pressing_data} dark />
        <AttackingPatternsCard data={state.attacking_patterns} dark />
        <BallLossesCard data={state.ball_losses} dark />
      </div>

      {/* ROW 2 — 3 pitch cards equal width */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, alignItems: "start" }}>

        {/* Passing Network */}
        <div style={{ display: "flex", flexDirection: "column", cursor: "zoom-in" }} onClick={() => setExpanded("passing")}>
          <PassingNetwork dark pollMs={4000} pitchH={PITCH_H} />
          <PitchLegend items={pitchCards.passing.legend} note={pitchCards.passing.note} />
        </div>

        {/* Line Breaking */}
        <div style={{ display: "flex", flexDirection: "column", cursor: "zoom-in" }} onClick={() => setExpanded("linebreaking")}>
          <LineBreakingCard data={state.line_breaking} dark pitchH={PITCH_H} />
          <PitchLegend items={pitchCards.linebreaking.legend} note={pitchCards.linebreaking.note} />
        </div>

        {/* Player Heatmap */}
        <div style={{ display: "flex", flexDirection: "column", cursor: "zoom-in" }} onClick={() => setExpanded("heatmap")}>
          <PlayerHeatmapLive dark pollMs={5000} pitchH={PITCH_H} />
          <PitchLegend items={pitchCards.heatmap.legend} note={pitchCards.heatmap.note} />
        </div>

      </div>

    </div>
  );
}

function PitchLegend({ items = [], note = "" }) {
  return (
    <div style={{
      padding: "10px 14px 14px",
      background: "rgba(10,10,10,0.75)",
      borderTop: "1px solid rgba(255,255,255,0.06)",
      borderLeft: "1px solid rgba(255,255,255,0.08)",
      borderRight: "1px solid rgba(255,255,255,0.08)",
      borderBottom: "1px solid rgba(255,255,255,0.08)",
      minHeight: 72,
      boxSizing: "border-box",
    }}>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 8 }}>
        {items.map((it, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{
              width: 20,
              height: 3,
              background: it.color,
              opacity: it.opacity ?? 1,
              display: "inline-block",
              flexShrink: 0,
            }} />
            <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: "rgba(255,255,255,0.6)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              {it.label}
            </span>
          </div>
        ))}
      </div>
      {note && (
        <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: "rgba(255,255,255,0.35)", lineHeight: 1.6 }}>
          {note}
        </div>
      )}
    </div>
  );
}

function BallLossesCard({ data = null, dark = true }) {
  const border = dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.1)";
  const total = data?.totalLosses || 0;
  const dangerous = data?.dangerousLosses || 0;
  const ownHalf = data?.inOwnHalf || 0;
  const pct = total > 0 ? Math.round((dangerous / total) * 100) : 0;

  return (
    <div style={{ padding: 20, background: dark ? "rgba(20,20,20,0.6)" : "#fff", border, backdropFilter: "blur(6px)", height: "100%", boxSizing: "border-box" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div className="label" style={{ opacity: 0.6 }}>Ball Losses · Live</div>
        <span className="chip-mono" style={{ color: total > 15 ? "var(--uc-red)" : "rgba(255,255,255,0.5)" }}>
          {total} total
        </span>
      </div>

      <div style={{ textAlign: "center", marginBottom: 16 }}>
        <div className="font-display" style={{ fontWeight: 900, fontSize: 64, lineHeight: 1, color: pct > 40 ? "var(--uc-red)" : "#f59e0b" }}>
          {pct}<span style={{ fontSize: 24, opacity: 0.5 }}>%</span>
        </div>
        <div className="label" style={{ opacity: 0.5, marginTop: 4 }}>Dangerous Loss Rate</div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {[
          { label: "Total Losses", value: total, color: "rgba(255,255,255,0.7)" },
          { label: "Dangerous", value: dangerous, color: "var(--uc-red)" },
          { label: "In Own Half", value: ownHalf, color: "#f59e0b" },
        ].map((m) => (
          <div key={m.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span className="label" style={{ opacity: 0.5, fontSize: 9 }}>{m.label}</span>
            <span className="font-mono" style={{ fontSize: 13, fontWeight: 700, color: m.color }}>{m.value}</span>
          </div>
        ))}
      </div>

      {data?.insight && (
        <div style={{ marginTop: 12, fontSize: 11, opacity: 0.6, fontFamily: "JetBrains Mono, monospace", lineHeight: 1.5, borderLeft: "2px solid var(--uc-red)", paddingLeft: 8 }}>
          {data.insight}
        </div>
      )}
    </div>
  );
}
