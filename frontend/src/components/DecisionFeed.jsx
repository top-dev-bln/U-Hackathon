import { Brain, ChevronUp, ChevronDown, Minus } from "lucide-react";

export default function DecisionFeed({ events = [], dark = true }) {
  const border = dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.1)";

  return (
    <div style={{ padding: 20, background: dark ? "rgba(20,20,20,0.6)" : "#fff", border, backdropFilter: "blur(6px)", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div className="label" style={{ opacity: 0.6, display: "flex", alignItems: "center", gap: 6 }}>
          <Brain size={12} /> Decision Quality · Live
        </div>
        <span className="chip-mono" style={{ color: dark ? "rgba(255,255,255,0.6)" : "rgba(0,0,0,0.6)" }}>
          {events.length}
        </span>
      </div>

      <div className="scroll-thin" style={{ overflowY: "auto", maxHeight: 280 }}>
        {events.length === 0 && (
          <div style={{ fontSize: 13, textAlign: "center", padding: "24px 0", opacity: 0.4 }}>
            No decisions yet
          </div>
        )}
        {events.map((e) => {
          const q = e.extra?.quality;
          const Icon = q === "good" ? ChevronUp : q === "poor" ? ChevronDown : Minus;
          const color = q === "good" ? "#22c55e" : q === "poor" ? "var(--uc-red)" : dark ? "rgba(255,255,255,0.6)" : "rgba(0,0,0,0.6)";
          const borderLeft = q === "poor" ? "2px solid var(--uc-red)" : q === "good" ? "2px solid #22c55e" : "2px solid transparent";

          return (
            <div
              key={e.id}
              className="fade-up"
              style={{ display: "flex", alignItems: "flex-start", gap: 12, padding: "6px 8px", borderLeft }}
            >
              <span className="chip-mono" style={{ flexShrink: 0, marginTop: 2, opacity: 0.6 }}>
                {String(e.minute).padStart(2, "0")}'
              </span>
              <Icon size={14} style={{ marginTop: 3, color, flexShrink: 0 }} />
              <div style={{ fontSize: 13, color: dark ? "rgba(255,255,255,0.9)" : "rgba(0,0,0,0.85)" }}>{e.text}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
