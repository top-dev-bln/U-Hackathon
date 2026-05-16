import { useState } from "react";
import TacticalReport from "./TacticalReport";
import DecisionQualityReport from "./DecisionQualityReport";
import CoachChat from "./CoachChat";

const TABS = [
  { id: "tactical", label: "Tactical Intelligence" },
  { id: "decision", label: "Decision Quality" },
  { id: "chat",     label: "AI Coach Chat" },
];

const MOCK_MATCHES = [
  { id: 1, home: "U Cluj",       away: "CFR Cluj",       date: "2025-04-20", score: "1-0", competition: "Superliga" },
  { id: 2, home: "U Cluj",       away: "Hermannstadt",   date: "2025-04-13", score: "2-1", competition: "Superliga" },
  { id: 3, home: "Farul",        away: "U Cluj",         date: "2025-04-06", score: "0-2", competition: "Superliga" },
  { id: 4, home: "U Cluj",       away: "Rapid",          date: "2025-03-30", score: "1-1", competition: "Superliga" },
  { id: 5, home: "FCSB",         away: "U Cluj",         date: "2025-03-23", score: "2-0", competition: "Superliga" },
  { id: 6, home: "U Cluj",       away: "Petrolul",       date: "2025-03-16", score: "3-1", competition: "Superliga" },
];

export default function AnalysisMode({ liveState }) {
  const [tab, setTab]           = useState("tactical");
  const [matchId, setMatchId]   = useState(1);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const selectedMatch = MOCK_MATCHES.find((m) => m.id === matchId) || MOCK_MATCHES[0];

  return (
    <div style={{ display: "flex", height: "calc(100vh - 64px)", background: "#f5f5f5", overflow: "hidden" }}>

      {/* ── SIDEBAR — match list ── */}
      <div style={{
        width: sidebarOpen ? 260 : 0,
        minWidth: sidebarOpen ? 260 : 0,
        overflow: "hidden",
        background: "#0a0a0a",
        borderRight: "1px solid rgba(255,255,255,0.06)",
        display: "flex",
        flexDirection: "column",
        transition: "width 0.25s ease, min-width 0.25s ease",
        flexShrink: 0,
      }}>
        <div style={{ padding: "20px 16px 12px", borderBottom: "1px solid rgba(255,255,255,0.06)", whiteSpace: "nowrap" }}>
          <div className="label" style={{ color: "rgba(255,255,255,0.4)", fontSize: 10 }}>Select Match</div>
        </div>
        <div style={{ flex: 1, overflowY: "auto", overflowX: "hidden" }}>
          {MOCK_MATCHES.map((m) => {
            const isSelected = m.id === matchId;
            return (
              <div
                key={m.id}
                onClick={() => setMatchId(m.id)}
                style={{
                  padding: "12px 16px",
                  cursor: "pointer",
                  borderLeft: isSelected ? "3px solid var(--uc-red)" : "3px solid transparent",
                  background: isSelected ? "rgba(227,6,19,0.08)" : "transparent",
                  borderBottom: "1px solid rgba(255,255,255,0.04)",
                  transition: "background 0.15s",
                  whiteSpace: "nowrap",
                }}
              >
                <div className="font-display" style={{
                  fontWeight: 700, fontSize: 13, textTransform: "uppercase",
                  color: isSelected ? "#fff" : "rgba(255,255,255,0.7)",
                  letterSpacing: "0.02em",
                }}>
                  {m.home} <span style={{ color: "var(--uc-red)" }}>{m.score}</span> {m.away}
                </div>
                <div className="font-mono" style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", marginTop: 3 }}>
                  {m.date} · {m.competition}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── MAIN CONTENT ── */}
      <div style={{ flex: 1, padding: "32px 40px", overflow: "auto", minWidth: 0 }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {/* Toggle sidebar button */}
            <button
              onClick={() => setSidebarOpen((o) => !o)}
              style={{
                background: "none", border: "1px solid rgba(0,0,0,0.15)",
                cursor: "pointer", padding: "6px 10px", fontSize: 14,
                color: "rgba(0,0,0,0.5)",
              }}
              title={sidebarOpen ? "Hide match list" : "Show match list"}
            >
              {sidebarOpen ? "◀" : "▶"}
            </button>
            <div>
              <h1 className="font-display" style={{ fontWeight: 900, fontSize: 40, textTransform: "uppercase", margin: 0, letterSpacing: "-1px" }}>
                Post-Match Analysis
              </h1>
              <p className="font-mono" style={{ fontSize: 11, opacity: 0.5, marginTop: 4 }}>
                {selectedMatch.home} {selectedMatch.score} {selectedMatch.away} · {selectedMatch.date} · {selectedMatch.competition}
              </p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 2, marginBottom: 24, borderBottom: "1px solid rgba(0,0,0,0.1)" }}>
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                padding: "12px 16px",
                fontFamily: "Barlow Condensed, sans-serif",
                fontWeight: 700,
                fontSize: 13,
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                border: "none",
                borderBottom: tab === t.id ? "2px solid var(--uc-red)" : "2px solid transparent",
                background: "none",
                color: tab === t.id ? "#0a0a0a" : "rgba(0,0,0,0.4)",
                cursor: "pointer",
                transition: "all 0.2s",
                marginBottom: -1,
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="fade-up">
          {tab === "tactical" && <TacticalReport dark={false} matchId={matchId} />}
          {tab === "decision" && <DecisionQualityReport events={liveState?.decision_events?.length ? liveState.decision_events : undefined} />}
          {tab === "chat"     && <CoachChat matchId={matchId} match={selectedMatch} />}
        </div>
      </div>

    </div>
  );
}
