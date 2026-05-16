import { TrendingUp, TrendingDown, Minus } from "lucide-react";

const MOCK_PRESSING = {
  teamPressingEfficiency: 0.49,
  firstHalfEfficiency: 0.47,
  secondHalfEfficiency: 0.52,
  intensityDrop: 0.05,
  insight: "Pressing was largely ineffective, slight improvement in the second half.",
  topPresser: "D. Oancea",
  players: [
    { id: 1002, name: "D. Oancea",  position: "RB",   pressingDuels: 6,  won: 4, efficiency: 0.67, inOpponentHalf: 0,  intensityDrop: -0.25 },
    { id: 1010, name: "I. Stoica",  position: "LAMF", pressingDuels: 8,  won: 5, efficiency: 0.62, inOpponentHalf: 8,  intensityDrop: 0.17  },
    { id: 1011, name: "M. Thiam",   position: "CF",   pressingDuels: 5,  won: 3, efficiency: 0.60, inOpponentHalf: 5,  intensityDrop: 0.75  },
    { id: 1006, name: "O. Bic",     position: "DMF",  pressingDuels: 10, won: 5, efficiency: 0.50, inOpponentHalf: 3,  intensityDrop: 0.24  },
    { id: 1005, name: "A. Chipciu", position: "LB",   pressingDuels: 4,  won: 2, efficiency: 0.50, inOpponentHalf: 0,  intensityDrop: 1.00  },
    { id: 1003, name: "L. Cristea", position: "RCB",  pressingDuels: 9,  won: 4, efficiency: 0.44, inOpponentHalf: 0,  intensityDrop: -0.50 },
    { id: 1007, name: "D. Nistor",  position: "CMF",  pressingDuels: 5,  won: 2, efficiency: 0.40, inOpponentHalf: 3,  intensityDrop: -0.50 },
    { id: 1004, name: "A. Miron",   position: "LCB",  pressingDuels: 4,  won: 1, efficiency: 0.25, inOpponentHalf: 0,  intensityDrop: -0.50 },
  ],
};

function effColor(eff) {
  if (eff >= 0.60) return "#22c55e";
  if (eff >= 0.45) return "#f59e0b";
  return "#E30613";
}

function DropIcon({ drop }) {
  if (drop > 0.05)  return <TrendingUp  size={13} color="#22c55e" />;
  if (drop < -0.05) return <TrendingDown size={13} color="#E30613" />;
  return <Minus size={13} color="#a3a3a3" />;
}

export default function PressingGauge({ data = MOCK_PRESSING, dark = true }) {
  const border = dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.1)";
  const dimText = dark ? "rgba(255,255,255,0.45)" : "rgba(0,0,0,0.45)";
  const bg = dark ? "rgba(20,20,20,0.6)" : "#fff";
  const rowHover = dark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)";

  const teamEff = Math.round((data.teamPressingEfficiency ?? 0) * 100);
  const teamColor = effColor(data.teamPressingEfficiency ?? 0);

  return (
    <div style={{ background: bg, border, backdropFilter: "blur(6px)", display: "flex", flexDirection: "column" }}>

      {/* ── Team summary bar ── */}
      <div style={{ padding: "14px 18px", borderBottom: border, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <div>
          <div className="label" style={{ opacity: 0.5, marginBottom: 2 }}>Pressing Efficiency · Live</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
            <span className="font-display" style={{ fontWeight: 900, fontSize: 40, lineHeight: 1, color: teamColor }}>
              {teamEff}<span style={{ fontSize: 18, opacity: 0.6 }}>%</span>
            </span>
            <span style={{ fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: dimText }}>
              First {Math.round((data.firstHalfEfficiency ?? 0) * 100)}% → Second {Math.round((data.secondHalfEfficiency ?? 0) * 100)}%
            </span>
          </div>
        </div>

        {/* Mini half bars */}
        <div style={{ display: "flex", flexDirection: "column", gap: 5, minWidth: 100 }}>
          {[
            { label: "1st Half", val: data.firstHalfEfficiency ?? 0 },
            { label: "2nd Half", val: data.secondHalfEfficiency ?? 0 },
          ].map((h) => (
            <div key={h.label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span className="label" style={{ opacity: 0.5, width: 70 }}>{h.label}</span>
              <div style={{ flex: 1, height: 5, background: dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)", position: "relative" }}>
                <div style={{ position: "absolute", inset: "0 auto 0 0", width: `${Math.round(h.val * 100)}%`, background: effColor(h.val), transition: "width 0.5s" }} />
              </div>
              <span className="font-mono" style={{ fontSize: 10, opacity: 0.7, width: 28 }}>{Math.round(h.val * 100)}%</span>
            </div>
          ))}
        </div>

        <div style={{ textAlign: "right" }}>
          <div className="label" style={{ opacity: 0.4 }}>Top Presser</div>
          <div className="font-display" style={{ fontWeight: 700, fontSize: 14, textTransform: "uppercase" }}>{data.topPresser}</div>
        </div>
      </div>

      {/* ── AI Insight ── */}
      <div style={{ padding: "10px 18px", borderBottom: border, borderLeft: "3px solid var(--uc-red)", marginLeft: 0 }}>
        <span className="font-mono" style={{ fontSize: 11, color: dimText, lineHeight: 1.5 }}>{data.insight}</span>
      </div>

      {/* ── Player table ── */}
      <div style={{ overflowY: "auto", maxHeight: 280 }} className="scroll-thin">
        {/* Header */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 60px 60px 70px 32px", gap: 8, padding: "8px 18px", borderBottom: border }}>
          {["Player", "Duels", "Won", "Effic.", "Trend"].map((h) => (
            <div key={h} className="label" style={{ opacity: 0.4, fontSize: 9 }}>{h}</div>
          ))}
        </div>

        {/* Rows */}
        {(data.players || []).map((p) => {
          const color = effColor(p.efficiency);
          return (
            <div
              key={p.id}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 60px 60px 70px 32px",
                gap: 8,
                padding: "9px 18px",
                borderBottom: dark ? "1px solid rgba(255,255,255,0.04)" : "1px solid rgba(0,0,0,0.05)",
                alignItems: "center",
              }}
            >
              {/* Name + position */}
              <div>
                <div className="font-display" style={{ fontWeight: 700, fontSize: 13, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  {p.name}
                </div>
                <div className="label" style={{ opacity: 0.4, fontSize: 9 }}>{p.position}{p.inOpponentHalf > 0 ? ` · ${p.inOpponentHalf} high` : ""}</div>
              </div>

              {/* Duels */}
              <div className="font-mono" style={{ fontSize: 13 }}>{p.pressingDuels}</div>

              {/* Won */}
              <div className="font-mono" style={{ fontSize: 13 }}>{p.won}</div>

              {/* Efficiency bar + % */}
              <div>
                <div style={{ height: 3, background: dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)", marginBottom: 3, position: "relative" }}>
                  <div style={{ position: "absolute", inset: "0 auto 0 0", width: `${Math.round(p.efficiency * 100)}%`, background: color }} />
                </div>
                <span className="font-mono" style={{ fontSize: 11, color }}>{Math.round(p.efficiency * 100)}%</span>
              </div>

              {/* Intensity drop icon */}
              <div style={{ display: "flex", justifyContent: "center" }}>
                <DropIcon drop={p.intensityDrop} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
