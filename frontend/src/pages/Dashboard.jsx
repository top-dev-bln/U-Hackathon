import { useState } from "react";
import LiveMode from "../components/LiveMode";
import AnalysisMode from "../components/AnalysisMode";
import MatchHeader from "../components/MatchHeader";
import PlayerRoster from "../components/PlayerRoster";

const MOCK_STATE = {
  home: "U Cluj",
  away: "FC Hermannstadt",
  score: { home: 1, away: 0 },
  minute: 67,
  second: 23,
  fatigue_alerts: [
    { id: 1, minute: 67, text: "Bic arată semne de oboseală — considerați substituție", load_index: 88 },
  ],
  pressing: 49,
  pressing_history: [
    { value: 55 }, { value: 50 }, { value: 47 }, { value: 52 }, { value: 49 },
  ],
  xg_home: 1.8,
  xg_away: 0.4,
  xg_history: [
    { minute: 0, home: 0, away: 0 },
    { minute: 10, home: 0.2, away: 0 },
    { minute: 20, home: 0.2, away: 0.1 },
    { minute: 30, home: 0.57, away: 0.1 },
    { minute: 40, home: 0.8, away: 0.3 },
    { minute: 50, home: 1.1, away: 0.3 },
    { minute: 60, home: 1.5, away: 0.4 },
    { minute: 67, home: 1.8, away: 0.4 },
  ],
  events: [
    { id: 1, minute: 67, type: "pressing_breakdown", severity: "warning", text: "Pressing breakdown — Bic pierde al 3-lea duel consecutiv" },
    { id: 2, minute: 63, type: "shot", severity: "success", text: "Șut pe poartă — Thiam, xG 0.34" },
    { id: 3, minute: 58, type: "goal", severity: "success", text: "GOL! Stoica marchează din pasă lui Nistor" },
    { id: 4, minute: 45, type: "decision", severity: "critical", text: "Decizie slabă — Popa ar fi trebuit să șuteze (gain +0.28 xG)" },
    { id: 5, minute: 32, type: "shot", severity: "info", text: "Șut blocat — Oancea din marginea careului" },
  ],
  attacking_patterns: {
    totalAttacks: 172,
    flankBreakdown: { left: 29, center: 93, right: 50 },
    mostDangerousFlank: "center",
    avgXgPerAttack: 0.016,
    insight: "Attack built through central channel, most danger from positional attacks (xG 2.69).",
  },
  line_breaking: {
    totalLineBreakingActions: 103,
    intoFinalThird: 52,
    intoBox: 14,
    led_to_shot: 10,
    topRunner: "D. Popa",
    insight: "Dangerous line-breaking threat — 14 runs reached the box, 10 directly created a shot.",
  },
  ball_losses: {
    totalLosses: 28,
    dangerousLosses: 9,
    inOwnHalf: 12,
    insight: "Too many losses in own half — pressing triggers needed.",
  },
};

export default function Dashboard() {
  const [mode, setMode] = useState("live");
  const state = MOCK_STATE;

  return (
    <div className={mode === "live" ? "live-mode" : "analysis-mode"}>
<MatchHeader state={state} mode={mode} setMode={setMode} />
      {mode === "live"     && <LiveMode state={state} />}
      {mode === "analysis" && <AnalysisMode liveState={state} />}
      {mode === "squad"    && <PlayerRoster />}
    </div>
  );
}
