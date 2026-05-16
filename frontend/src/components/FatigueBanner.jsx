import { AlertTriangle, X } from "lucide-react";
import { useState } from "react";

export default function FatigueBanner({ alerts = [] }) {
  const [dismissed, setDismissed] = useState(new Set());
  const active = alerts.filter((a) => !dismissed.has(a.id));
  if (active.length === 0) return null;
  const a = active[0];

  return (
    <div className="slide-down" style={{ position: "sticky", top: 0, zIndex: 50 }}>
      <div style={{ background: "var(--uc-red)", color: "white" }}>
        <div
          style={{
            padding: "12px 32px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1 }}>
            <div
              className="pulse-red"
              style={{
                width: 36,
                height: 36,
                display: "grid",
                placeItems: "center",
                background: "rgba(0,0,0,0.3)",
              }}
            >
              <AlertTriangle size={18} />
            </div>
            <div>
              <div className="label" style={{ letterSpacing: "0.3em" }}>
                Fatigue Alert · MIN {a.minute}'
              </div>
              <div className="font-display" style={{ fontWeight: 700, fontSize: 18, textTransform: "uppercase" }}>
                ⚠ {a.text}
              </div>
            </div>
          </div>
          <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 12, textAlign: "right" }}>
            <div style={{ opacity: 0.8 }}>LOAD INDEX</div>
            <div style={{ fontWeight: 700, fontSize: 24 }}>{a.load_index ?? "—"}</div>
          </div>
          <button
            onClick={() => setDismissed(new Set([...dismissed, a.id]))}
            style={{
              width: 32,
              height: 32,
              display: "grid",
              placeItems: "center",
              background: "none",
              border: "none",
              color: "white",
              cursor: "pointer",
            }}
          >
            <X size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
