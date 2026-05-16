import { useEffect, useState } from "react";
import { fetchTacticalReport, fetchInsight } from "../lib/api";
import { Sparkles, Loader2 } from "lucide-react";

const MOCK_REPORT = {
  summary: {
    formation: "4-2-3-1",
    score: { home: 1, away: 0 },
    xg_home: 1.8,
    xg_away: 0.4,
    avg_pressing: 49,
    passes: 312,
    pass_accuracy: 84,
    shots: 8,
    shots_on_target: 4,
  },
  phases: [
    { label: "0-15'",  pressing: 52, tempo: "High"   },
    { label: "15-45'", pressing: 45, tempo: "Medium"  },
    { label: "45-60'", pressing: 55, tempo: "High"    },
    { label: "60-90'", pressing: 48, tempo: "Medium"  },
  ],
  recommendations: [
    "Press higher in the first 15 minutes to force errors",
    "Bic needs rest — consider substitution after 70'",
    "Exploit right flank more — Oancea has space to advance",
    "Thiam should look for the shot earlier in the box",
  ],
  key_moments: [
    { minute: 58, text: "GOAL — Stoica finishes from Nistor's through ball (xG 0.62)" },
    { minute: 45, text: "Popa missed high-value shot opportunity (xG 0.48)" },
    { minute: 32, text: "Pressing breakdown in midfield — Hermannstadt counter" },
    { minute: 67, text: "Bic intensity drop detected — fatigue alert triggered" },
  ],
};

export default function TacticalReport({ dark = false }) {
  const [report, setReport] = useState(MOCK_REPORT);
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTacticalReport().then(setReport).catch(() => {});
  }, []);

  const askInsight = async (topic) => {
    setLoading(true);
    try {
      const r = await fetchInsight(topic);
      setInsight(r);
    } finally {
      setLoading(false);
    }
  };

  if (!report) {
    return (
      <div style={{ padding: 24, fontSize: 13, opacity: 0.5, fontFamily: "JetBrains Mono, monospace" }}>
        Loading tactical report…
      </div>
    );
  }

  const s = report.summary;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 16, alignItems: "start" }}>

      {/* LEFT — Recommendations + AI Insight */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

        {/* Recommendations */}
        <div style={{ padding: 24, background: "#fff", border: "1px solid rgba(0,0,0,0.1)" }}>
          <div className="label" style={{ opacity: 0.6, marginBottom: 16 }}>Recommendations · Coach View</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {(report.recommendations || []).map((r, i) => (
              <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 12, padding: "10px 14px", borderLeft: "3px solid var(--uc-red)", background: "rgba(0,0,0,0.015)" }}>
                <span className="font-mono" style={{ fontSize: 11, opacity: 0.4, flexShrink: 0, marginTop: 2 }}>{String(i + 1).padStart(2, "0")}</span>
                <span style={{ fontSize: 13, lineHeight: 1.5 }}>{r}</span>
              </div>
            ))}
          </div>
        </div>

        {/* AI Insight */}
        <div style={{ padding: 24, background: "#fff", border: "1px solid rgba(0,0,0,0.1)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div className="label" style={{ opacity: 0.6, display: "flex", alignItems: "center", gap: 6 }}>
              <Sparkles size={12} /> AI Tactical Insight
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              {["pressing", "fatigue", "general"].map((t) => (
                <button
                  key={t}
                  onClick={() => askInsight(t)}
                  style={{
                    padding: "4px 12px",
                    fontSize: 11,
                    fontFamily: "JetBrains Mono, monospace",
                    textTransform: "uppercase",
                    letterSpacing: "0.1em",
                    border: "1px solid rgba(0,0,0,0.15)",
                    background: "none",
                    cursor: "pointer",
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          {loading && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, opacity: 0.7 }}>
              <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> Analyzing…
            </div>
          )}
          {insight && (
            <div style={{ fontSize: 13, lineHeight: 1.6, borderLeft: "2px solid var(--uc-red)", paddingLeft: 16, paddingTop: 8, paddingBottom: 8 }}>
              {insight.insight}
            </div>
          )}
          {!insight && !loading && (
            <div style={{ fontSize: 13, opacity: 0.5 }}>Pick a topic to generate analyst commentary.</div>
          )}
        </div>
      </div>

      {/* RIGHT — Phase Breakdown */}
      <div style={{ padding: 24, background: "#fff", border: "1px solid rgba(0,0,0,0.1)" }}>
        <div className="label" style={{ opacity: 0.6, marginBottom: 16 }}>Phase Breakdown · {s.formation}</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {(report.phases || []).map((ph, i) => (
            <div key={i} style={{ border: "1px solid rgba(0,0,0,0.08)", padding: "14px 16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
                <div className="font-mono" style={{ fontSize: 11, opacity: 0.6 }}>{ph.label}</div>
                <div className="label" style={{ opacity: 0.5, fontSize: 10 }}>{ph.tempo}</div>
              </div>
              <div className="font-display" style={{ fontWeight: 900, fontSize: 36, lineHeight: 1 }}>
                {ph.pressing}<span style={{ fontSize: 16, opacity: 0.5 }}>%</span>
              </div>
              <div style={{ marginTop: 8, height: 4, background: "rgba(0,0,0,0.06)" }}>
                <div style={{ height: "100%", width: `${ph.pressing}%`, background: ph.pressing >= 50 ? "var(--uc-red)" : "#f59e0b", transition: "width 0.5s" }} />
              </div>
            </div>
          ))}
        </div>

        {/* Key moments */}
        <div style={{ marginTop: 20 }}>
          <div className="label" style={{ opacity: 0.6, marginBottom: 12 }}>Key Moments</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {(report.key_moments || []).map((km, i) => (
              <div key={i} style={{ display: "flex", gap: 10, fontSize: 12, alignItems: "flex-start" }}>
                <span className="font-mono" style={{ opacity: 0.4, flexShrink: 0 }}>{String(km.minute).padStart(2,"0")}'</span>
                <span style={{ opacity: 0.75, lineHeight: 1.4 }}>{km.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

    </div>
  );
}

function BigStat({ label, value, sub, color = "#0a0a0a" }) {
  return (
    <div style={{ border: "1px solid rgba(0,0,0,0.1)", padding: 12 }}>
      <div className="label" style={{ opacity: 0.6 }}>{label}</div>
      <div className="font-display" style={{ fontWeight: 900, fontSize: 28, color }}>{value}</div>
      {sub && <div className="font-mono" style={{ fontSize: 10, opacity: 0.6 }}>{sub}</div>}
    </div>
  );
}
