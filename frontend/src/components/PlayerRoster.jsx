import { useState, useMemo } from "react";
import dailyRaw  from "../data/players_daily.json";
import weeklyRaw from "../data/players_weekly.json";

// ── ssId map by full name (for Sofascore photos) ──────────────────────────────
const SS_IDS = {
  "Alessandro Murgia":      559470,
  "Alex Mihai Orban":       2086370,
  "Alexandru Bota":         1477485,
  "Alexandru Chipciu":      44435,
  "Alin Chinteș":           1426614,
  "Alin Toșca":             110210,
  "Andrei Gheorghiță":      1113174,
  "Andrej Fábry":           824206,
  "Atanas Trică":           1907275,
  "Dan Nistor":             93842,
  "Dino Mikanović":         245249,
  "Dorin Codrea":           946446,
  "Elio Capradossi":        284355,
  "Gabriel Simion":         849788,
  "Issouf Macalou":         1101188,
  "Iulian Cristea":         578526,
  "Jasper van der Werff":   925011,
  "Jonathan Cissé":         1005396,
  "Jovo Lukić":             927797,
  "Matei Moraru":           1152491,
  "Miguel Muñoz Fernández": 914160,
  "Mouhamadou Drammeh":     1085101,
  "Omar El Sawy":           1146209,
  "Ovidiu Bic":             812807,
  "Taiwo Quadri Olakunle":  2430478,
  "Virgiliu Postolachi":    901913,
};

const SS = (name) => {
  const id = SS_IDS[name];
  return id ? `https://img.sofascore.com/api/v1/player/${id}/image` : null;
};

// ── Meta maps ─────────────────────────────────────────────────────────────────
const CLUSTER_META = {
  "explosive short-burst": { bg: "#fee2e2", color: "#b91c1c" },
  "high volume":           { bg: "#dbeafe", color: "#1d4ed8" },
  "balanced":              { bg: "#dcfce7", color: "#15803d" },
  "low load":              { bg: "#fef9c3", color: "#a16207" },
};
const DEFAULT_CLUSTER = { bg: "#e5e7eb", color: "#374151" };

const AC_META = {
  below_optimal: { label: "BELOW OPT", bg: "#fef9c3", color: "#a16207" },
  optimal:       { label: "OPTIMAL",   bg: "#dcfce7", color: "#15803d" },
  above_optimal: { label: "ABOVE OPT", bg: "#fee2e2", color: "#b91c1c" },
};

// ── Color helpers ─────────────────────────────────────────────────────────────
function formColor(v) {
  if (v >= 70) return "#16a34a";
  if (v >= 50) return "#f59e0b";
  return "#E30613";
}
function fatigueColor(p) {
  if (p >= 0.65) return "#b91c1c";
  if (p >= 0.40) return "#a16207";
  return "#15803d";
}
function fatigueBg(p) {
  if (p >= 0.65) return "#fee2e2";
  if (p >= 0.40) return "#fef9c3";
  return "#dcfce7";
}
function fatigueLabel(p) {
  if (p >= 0.65) return "HIGH RISK";
  if (p >= 0.40) return "MODERATE";
  return "LOW RISK";
}
function acColor(v) {
  if (v > 1.2)  return "#b91c1c";
  if (v > 1.05) return "#f59e0b";
  if (v < 0.9)  return "#60a5fa";
  return "#22c55e";
}

function MiniBar({ value, color, max = 100 }) {
  return (
    <div style={{ height: 3, background: "rgba(255,255,255,0.1)", width: "100%", marginTop: 3, borderRadius: 2 }}>
      <div style={{ height: "100%", width: `${Math.min((value / max) * 100, 100)}%`, background: color, borderRadius: 2 }} />
    </div>
  );
}

// ── Get latest snapshot per player ───────────────────────────────────────────
function getLatestPerPlayer(rawData) {
  const map = {};
  for (const row of rawData.data) {
    const key = row.player_full_name;
    if (!map[key] || row.date > map[key].date) {
      map[key] = row;
    }
  }
  return Object.values(map);
}

// ── Player Card ───────────────────────────────────────────────────────────────
function PlayerCard({ p }) {
  const [flipped, setFlipped] = useState(false);
  const cluster  = CLUSTER_META[p.cluster_profile?.toLowerCase()] || CLUSTER_META[p.cluster_profile] || DEFAULT_CLUSTER;
  const acMeta   = AC_META[p.ac_combined_status] || AC_META["optimal"];
  const initials = p.player_full_name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
  const fProb    = p.fatigue_risk_prob;
  const photoUrl = SS(p.player_full_name);

  return (
    <div
      onMouseEnter={() => setFlipped(true)}
      onMouseLeave={() => setFlipped(false)}
      style={{ perspective: 1000, cursor: "pointer", height: 360 }}
    >
      <div style={{
        position: "relative", width: "100%", height: "100%",
        transformStyle: "preserve-3d",
        transform: flipped ? "rotateY(180deg)" : "rotateY(0deg)",
        transition: "transform 0.55s cubic-bezier(0.4, 0.2, 0.2, 1)",
      }}>

        {/* ── FRONT ── */}
        <div style={{ position: "absolute", inset: 0, backfaceVisibility: "hidden", WebkitBackfaceVisibility: "hidden", overflow: "hidden" }}>
          {photoUrl && (
            <img src={photoUrl} alt="" style={{ position: "absolute", inset: "-10px", width: "calc(100% + 20px)", height: "calc(100% + 20px)", objectFit: "cover", objectPosition: "center top", filter: "blur(14px) brightness(0.35)", transform: "scale(1.05)" }} onError={(e) => { e.currentTarget.style.display = "none"; }} />
          )}
          <div style={{ position: "absolute", inset: 0, background: "linear-gradient(160deg, #0a0a0a 0%, #1a0505 100%)" }} />
          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span className="font-display" style={{ fontSize: 52, fontWeight: 900, color: "rgba(255,255,255,0.1)" }}>{initials}</span>
          </div>
          {photoUrl && (
            <img src={photoUrl} alt={p.player_full_name} style={{ position: "absolute", left: "50%", top: "4px", transform: "translateX(-50%)", height: "78%", width: "auto", objectFit: "contain", objectPosition: "top center" }} onError={(e) => { e.currentTarget.style.display = "none"; }} />
          )}
          <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to top, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.4) 45%, transparent 70%)" }} />

          <div style={{ position: "absolute", top: 8, left: 8, fontFamily: "JetBrains Mono, monospace", fontSize: 9, color: "rgba(255,255,255,0.6)", fontWeight: 700, background: "rgba(0,0,0,0.4)", padding: "2px 6px", textTransform: "uppercase" }}>
            {p.player_role}
          </div>
          <div style={{ position: "absolute", top: 8, right: 8, padding: "2px 6px", background: fatigueBg(fProb), color: fatigueColor(fProb), fontSize: 8, fontFamily: "JetBrains Mono, monospace", fontWeight: 700 }}>
            {fatigueLabel(fProb)}
          </div>

          <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, padding: "10px 12px" }}>
            <div className="font-display" style={{ fontWeight: 900, fontSize: 13, textTransform: "uppercase", color: "#fff", lineHeight: 1.1, textShadow: "0 1px 4px rgba(0,0,0,0.8)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{p.player_full_name}</div>
            <div style={{ marginTop: 4, display: "inline-block", padding: "1px 6px", background: cluster.bg, color: cluster.color, fontSize: 8, fontFamily: "JetBrains Mono, monospace", fontWeight: 700 }}>{p.cluster_profile}</div>
          </div>
        </div>

        {/* ── BACK ── */}
        <div style={{
          position: "absolute", inset: 0,
          backfaceVisibility: "hidden", WebkitBackfaceVisibility: "hidden",
          transform: "rotateY(180deg)",
          background: "#0a0a0a", color: "#fff",
          padding: "14px 14px 12px",
          display: "flex", flexDirection: "column", gap: 7,
          border: "1px solid rgba(227,6,19,0.4)", overflow: "hidden",
        }}>
          {/* Name */}
          <div style={{ borderBottom: "1px solid rgba(255,255,255,0.07)", paddingBottom: 6 }}>
            <div className="font-display" style={{ fontWeight: 900, fontSize: 13, textTransform: "uppercase", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{p.player_full_name}</div>
            <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 9, color: "rgba(255,255,255,0.35)", marginTop: 2 }}>{p.player_role} · {p.date}</div>
          </div>

          {/* Form Score */}
          <div>
            <div className="label" style={{ fontSize: 9, opacity: 0.35, marginBottom: 4 }}>Form Score</div>
            <div style={{ display: "flex", gap: 8 }}>
              {[{ label: "7d", val: p.form_score_7d }, { label: "14d", val: p.form_score_14d }].map(f => (
                <div key={f.label} style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 9, opacity: 0.4 }}>{f.label}</span>
                    <span className="font-display" style={{ fontWeight: 900, fontSize: 20, color: formColor(f.val) }}>{Math.round(f.val)}</span>
                  </div>
                  <MiniBar value={f.val} color={formColor(f.val)} />
                </div>
              ))}
            </div>
          </div>

          {/* Fatigue */}
          <div style={{ padding: "5px 8px", background: fatigueBg(fProb), borderLeft: `3px solid ${fatigueColor(fProb)}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 9, color: fatigueColor(fProb), fontWeight: 700 }}>Fatigue Risk</span>
            <span className="font-display" style={{ fontWeight: 900, fontSize: 18, color: fatigueColor(fProb) }}>{Math.round(fProb * 100)}%</span>
          </div>

          {/* AC Status */}
          <div style={{ padding: "4px 8px", background: acMeta.bg, borderLeft: `3px solid ${acMeta.color}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 9, color: acMeta.color, fontWeight: 700 }}>A:C Status</span>
            <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 9, color: acMeta.color, fontWeight: 700 }}>{acMeta.label}</span>
          </div>

          {/* A:C Windows */}
          <div>
            <div className="label" style={{ fontSize: 9, opacity: 0.35, marginBottom: 4 }}>A:C Windows (7:28)</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "4px 8px" }}>
              {[
                { label: "Dist.",  val: p.ac_distance_7_28 },
                { label: "HI",    val: p.ac_high_int_7_28 },
                { label: "Load",  val: p.ac_load_7_28 },
              ].map(w => (
                <div key={w.label}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 8, opacity: 0.4 }}>{w.label}</span>
                    <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, fontWeight: 700, color: acColor(w.val ?? 1) }}>{(w.val ?? 0).toFixed(2)}</span>
                  </div>
                  <MiniBar value={(w.val ?? 0) * 50} color={acColor(w.val ?? 1)} max={80} />
                </div>
              ))}
            </div>
          </div>

          {/* Load metrics */}
          <div>
            <div className="label" style={{ fontSize: 9, opacity: 0.35, marginBottom: 4 }}>Physical Metrics</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "3px 8px" }}>
              {[
                { label: "Distance",   val: `${((p.distance_m ?? 0) / 1000).toFixed(2)} km` },
                { label: "m/min",      val: (p.distance_per_min ?? 0).toFixed(1) },
                { label: "HI dist.",   val: `${(p.high_int_acc_abs_m ?? 0).toFixed(0)} m` },
                { label: "Load proxy", val: `${((p.training_load_proxy ?? 0) / 1000).toFixed(1)}k` },
              ].map(m => (
                <div key={m.label} style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 8, opacity: 0.4 }}>{m.label}</span>
                  <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 9, color: "rgba(255,255,255,0.8)", fontWeight: 700 }}>{m.val}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Cluster */}
          <div style={{ marginTop: "auto", padding: "4px 8px", background: cluster.bg, color: cluster.color, fontSize: 9, fontFamily: "JetBrains Mono, monospace", fontWeight: 700, textAlign: "center" }}>
            {p.cluster_profile?.toUpperCase()}
          </div>
        </div>

      </div>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function PlayerRoster() {
  const [cadence,    setCadence]    = useState("weekly");
  const [roleFilter, setRoleFilter] = useState("ALL");
  const [acFilter,   setAcFilter]   = useState("ALL");

  const players = useMemo(() => {
    const raw = cadence === "daily" ? dailyRaw : weeklyRaw;
    return getLatestPerPlayer(raw);
  }, [cadence]);

  const roles      = ["ALL", "Forward", "Midfielder", "Defender", "Goalkeeper"];
  const acStatuses = ["ALL", "below_optimal", "optimal", "above_optimal"];
  const acLabels   = { ALL: "All", below_optimal: "Below Opt", optimal: "Optimal", above_optimal: "Above Opt" };

  const filtered = players.filter(p => {
    const roleOk = roleFilter === "ALL" || p.player_role === roleFilter;
    const acOk   = acFilter   === "ALL" || p.ac_combined_status === acFilter;
    return roleOk && acOk;
  });

  const highRisk = players.filter(p => p.fatigue_risk_prob >= 0.65).length;
  const avgForm  = players.length
    ? Math.round(players.reduce((a, p) => a + p.form_score_7d, 0) / players.length)
    : 0;

  return (
    <div style={{ padding: "28px 40px", background: "#f5f5f5", minHeight: "100%" }}>

      {/* Header */}
      <div style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 className="font-display" style={{ fontWeight: 900, fontSize: 40, textTransform: "uppercase", margin: 0, letterSpacing: "-1px" }}>
            Squad Load Monitor
          </h1>
          <p className="font-mono" style={{ fontSize: 11, opacity: 0.5, marginTop: 4 }}>
            {players.length} players · Hover for detailed analytics
          </p>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          {[
            { label: "Avg Form (7d)",      value: avgForm,        color: formColor(avgForm) },
            { label: "High Fatigue Risk", value: highRisk,       color: "#E30613" },
            { label: "Total Players",     value: players.length, color: "#0a0a0a" },
          ].map(s => (
            <div key={s.label} style={{ padding: "10px 18px", background: "#fff", border: "1px solid rgba(0,0,0,0.1)", textAlign: "center" }}>
              <div className="label" style={{ fontSize: 9, opacity: 0.5 }}>{s.label}</div>
              <div className="font-display" style={{ fontWeight: 900, fontSize: 28, color: s.color }}>{s.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 16, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>

        {/* Cadence toggle */}
        <div style={{ display: "flex", border: "1px solid rgba(0,0,0,0.15)" }}>
          {[{ key: "daily", label: "Daily" }, { key: "weekly", label: "Weekly" }].map(c => (
            <button key={c.key} onClick={() => setCadence(c.key)} style={{
              padding: "5px 16px", fontSize: 11, fontFamily: "JetBrains Mono, monospace",
              textTransform: "uppercase", letterSpacing: "0.08em",
              border: "none", cursor: "pointer",
              background: cadence === c.key ? "#0a0a0a" : "transparent",
              color: cadence === c.key ? "#fff" : "rgba(0,0,0,0.5)",
              transition: "all 0.15s",
            }}>{c.label}</button>
          ))}
        </div>

        <div style={{ width: 1, height: 24, background: "rgba(0,0,0,0.1)" }} />

        {/* Role filter */}
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {roles.map(r => (
            <button key={r} onClick={() => setRoleFilter(r)} style={{
              padding: "4px 12px", fontSize: 11, fontFamily: "JetBrains Mono, monospace",
              textTransform: "uppercase", letterSpacing: "0.08em",
              border: "1px solid rgba(0,0,0,0.15)", cursor: "pointer",
              background: roleFilter === r ? "#0a0a0a" : "none",
              color: roleFilter === r ? "#fff" : "rgba(0,0,0,0.5)",
              transition: "all 0.15s",
            }}>{r === "ALL" ? "All positions" : r}</button>
          ))}
        </div>

        <div style={{ width: 1, height: 24, background: "rgba(0,0,0,0.1)" }} />

        {/* AC filter */}
        <div style={{ display: "flex", gap: 4 }}>
          {acStatuses.map(s => {
            const meta = s === "ALL" ? { bg: "#0a0a0a", color: "#fff" } : AC_META[s];
            const isActive = acFilter === s;
            return (
              <button key={s} onClick={() => setAcFilter(s)} style={{
                padding: "4px 12px", fontSize: 11, fontFamily: "JetBrains Mono, monospace",
                textTransform: "uppercase", letterSpacing: "0.08em",
                border: `1px solid ${isActive ? meta.color : "rgba(0,0,0,0.15)"}`,
                cursor: "pointer",
                background: isActive ? meta.bg : "none",
                color: isActive ? meta.color : "rgba(0,0,0,0.5)",
                transition: "all 0.15s",
              }}>{acLabels[s]}</button>
            );
          })}
        </div>
      </div>

      {/* Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 }}>
        {filtered.map(p => <PlayerCard key={p.player_full_name} p={p} />)}
      </div>

    </div>
  );
}
