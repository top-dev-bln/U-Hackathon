import { Activity, BarChart3, Users } from "lucide-react";

export default function MatchHeader({ state, mode, setMode }) {
  const isDark = mode === "live";
  const home = state?.home || "U CLUJ";
  const away = state?.away || "—";
  const score = state?.score || { home: 0, away: 0 };
  const minute = state?.minute ?? 0;
  const second = String(state?.second ?? 0).padStart(2, "0");

  const border = isDark ? "1px solid rgba(255,255,255,0.1)" : "1px solid rgba(0,0,0,0.1)";

  return (
    <header style={{ borderBottom: border, position: "relative" }}>
      <div
        style={{
          padding: "20px 32px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 24,
          flexWrap: "wrap",
        }}
      >
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <img
            src="/logo.png"
            alt="FC Universitatea Cluj"
            style={{
              width: 52,
              height: 52,
              objectFit: "contain",
              mixBlendMode: isDark ? "screen" : "normal",
            }}
          />
          <div>
            <div className="font-display" style={{ fontWeight: 900, fontSize: 22, textTransform: "uppercase" }}>
              {home}
            </div>
            <div className="label" style={{ opacity: 0.5, marginTop: 2 }}>
              Football Analytics
            </div>
          </div>
        </div>

        {/* Scoreboard */}
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <div style={{ textAlign: "right" }}>
            <div className="label" style={{ opacity: 0.5 }}>Home</div>
            <div className="font-display" style={{ fontWeight: 900, fontSize: 28, textTransform: "uppercase" }}>{home}</div>
          </div>
          <div
            style={{
              padding: "8px 24px",
              background: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)",
              border: border,
              textAlign: "center",
            }}
          >
            <div className="font-mono" style={{ fontSize: 10, letterSpacing: "0.3em", opacity: 0.6 }}>
              {minute}'{second !== "00" ? `:${second}` : ""}
            </div>
            <div className="font-display" style={{ fontWeight: 900, fontSize: 52, letterSpacing: "-2px", lineHeight: 1 }}>
              {score.home}
              <span style={{ opacity: 0.3, margin: "0 8px" }}>:</span>
              {score.away}
            </div>
          </div>
          <div style={{ textAlign: "left" }}>
            <div className="label" style={{ opacity: 0.5 }}>Away</div>
            <div className="font-display" style={{ fontWeight: 900, fontSize: 28, textTransform: "uppercase" }}>{away}</div>
          </div>
        </div>

        {/* Mode toggle */}
        <div style={{ display: "flex", border }}>
          <button
            onClick={() => setMode("live")}
            style={{
              padding: "8px 20px",
              fontFamily: "Barlow Condensed, sans-serif",
              fontWeight: 700,
              fontSize: 13,
              textTransform: "uppercase",
              letterSpacing: "0.15em",
              display: "flex",
              alignItems: "center",
              gap: 6,
              cursor: "pointer",
              border: "none",
              background: mode === "live" ? "var(--uc-red)" : "transparent",
              color: mode === "live" ? "white" : isDark ? "rgba(255,255,255,0.5)" : "rgba(0,0,0,0.5)",
              transition: "all 0.2s",
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: mode === "live" ? "white" : "currentColor",
                opacity: mode === "live" ? 1 : 0.4,
                animation: mode === "live" ? "pulse-red 1.6s infinite" : "none",
              }}
            />
            <Activity size={13} /> Live
          </button>
          <button
            onClick={() => setMode("analysis")}
            style={{
              padding: "8px 20px",
              fontFamily: "Barlow Condensed, sans-serif",
              fontWeight: 700,
              fontSize: 13,
              textTransform: "uppercase",
              letterSpacing: "0.15em",
              display: "flex",
              alignItems: "center",
              gap: 6,
              cursor: "pointer",
              border: "none",
              borderLeft: border,
              background: mode === "analysis" ? "#0a0a0a" : "transparent",
              color: mode === "analysis" ? "white" : isDark ? "rgba(255,255,255,0.5)" : "rgba(0,0,0,0.5)",
              transition: "all 0.2s",
            }}
          >
            <BarChart3 size={13} /> Analysis
          </button>
          <button
            onClick={() => setMode("squad")}
            style={{
              padding: "8px 20px",
              fontFamily: "Barlow Condensed, sans-serif",
              fontWeight: 700,
              fontSize: 13,
              textTransform: "uppercase",
              letterSpacing: "0.15em",
              display: "flex",
              alignItems: "center",
              gap: 6,
              cursor: "pointer",
              border: "none",
              borderLeft: border,
              background: mode === "squad" ? "#0a0a0a" : "transparent",
              color: mode === "squad" ? "white" : isDark ? "rgba(255,255,255,0.5)" : "rgba(0,0,0,0.5)",
              transition: "all 0.2s",
            }}
          >
            <Users size={13} /> Squad
          </button>
        </div>
      </div>
    </header>
  );
}
