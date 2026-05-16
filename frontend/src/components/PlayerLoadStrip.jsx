export default function PlayerLoadStrip({ players = [], dark = true }) {
  const border = dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.1)";
  const cellBorder = dark ? "1px solid rgba(255,255,255,0.1)" : "1px solid rgba(0,0,0,0.1)";

  return (
    <div style={{ padding: 20, background: dark ? "rgba(20,20,20,0.6)" : "#fff", border, backdropFilter: "blur(6px)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div className="label" style={{ opacity: 0.6 }}>Squad GPS Load · Live</div>
        <div style={{ display: "flex", gap: 12, fontSize: 10, fontFamily: "JetBrains Mono, monospace", opacity: 0.7 }}>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 8, height: 8, background: "#22c55e", display: "inline-block" }} /> &lt;75
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 8, height: 8, background: "#f59e0b", display: "inline-block" }} /> 75-85
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 8, height: 8, background: "var(--uc-red)", display: "inline-block" }} /> 85+
          </span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))", gap: 8 }}>
        {players.map((p) => {
          const barColor = p.load >= 85 ? "var(--uc-red)" : p.load >= 75 ? "#f59e0b" : "#22c55e";
          return (
            <div key={p.num} style={{ border: cellBorder, padding: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span className="font-mono" style={{ fontSize: 11, opacity: 0.7 }}>#{p.num}</span>
                <span className="label" style={{ opacity: 0.6 }}>{p.pos}</span>
              </div>
              <div className="font-display" style={{ fontWeight: 700, textTransform: "uppercase", fontSize: 13, marginTop: 2 }}>
                {p.name}
              </div>
              <div style={{ marginTop: 8, height: 4, background: dark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)", position: "relative", overflow: "hidden" }}>
                <div style={{ position: "absolute", inset: "0 auto 0 0", width: `${Math.min(100, p.load)}%`, background: barColor }} />
              </div>
              <div className="font-mono" style={{ fontSize: 10, opacity: 0.7, marginTop: 4 }}>load {p.load}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
