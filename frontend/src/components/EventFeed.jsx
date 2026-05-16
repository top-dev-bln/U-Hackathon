import { Zap, Target, AlertTriangle, Activity } from "lucide-react";

const ICONS = {
  goal: Target,
  shot: Target,
  decision: Activity,
  pressing_breakdown: AlertTriangle,
  fatigue: AlertTriangle,
  goal_against: AlertTriangle,
};

export default function EventFeed({ events = [], dark = true, title = "Live Event Feed" }) {
  const border = dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.1)";

  return (
    <div style={{ padding: 20, background: dark ? "rgba(20,20,20,0.6)" : "#fff", border, backdropFilter: "blur(6px)", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div className="label" style={{ opacity: 0.6 }}>{title}</div>
        <span className="chip-mono" style={{ color: dark ? "rgba(255,255,255,0.6)" : "rgba(0,0,0,0.6)" }}>
          {events.length}
        </span>
      </div>

      <div className="scroll-thin" style={{ overflowY: "auto", maxHeight: 420 }}>
        {events.length === 0 && (
          <div style={{ fontSize: 13, textAlign: "center", padding: "32px 0", opacity: 0.4 }}>
            Waiting for first event…
          </div>
        )}
        {events.map((e) => {
          const Icon = ICONS[e.type] || Zap;
          const sev = e.severity;
          const borderLeft =
            sev === "critical" ? "2px solid var(--uc-red)" :
            sev === "warning"  ? "2px solid #f59e0b" :
            sev === "success"  ? "2px solid #22c55e" :
            "2px solid transparent";
          const color =
            sev === "critical" ? "var(--uc-red)" :
            sev === "warning"  ? "#f59e0b" :
            sev === "success"  ? "#22c55e" :
            dark ? "rgba(255,255,255,0.9)" : "rgba(0,0,0,0.85)";

          return (
            <div
              key={e.id}
              className="fade-up"
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 12,
                padding: "8px 12px",
                borderLeft,
              }}
            >
              <span className="chip-mono" style={{ flexShrink: 0, marginTop: 2, opacity: 0.6 }}>
                {String(e.minute).padStart(2, "0")}'
              </span>
              <Icon size={14} style={{ marginTop: 3, color, flexShrink: 0 }} />
              <div style={{ fontSize: 13, lineHeight: 1.4, color }}>{e.text}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
