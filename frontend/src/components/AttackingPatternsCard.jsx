import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";

export default function AttackingPatternsCard({ data = null, dark = true }) {
  const border = dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.1)";

  const flank = data?.flankBreakdown || { left: 0, center: 0, right: 0 };
  const flankData = [
    { name: "Left", value: flank.left },
    { name: "Center", value: flank.center },
    { name: "Right", value: flank.right },
  ];

  const dominant = data?.mostDangerousFlank || "—";
  const totalAttacks = data?.totalAttacks || 0;
  const avgXg = data?.avgXgPerAttack ?? 0;

  return (
    <div style={{ padding: 20, background: dark ? "rgba(20,20,20,0.6)" : "#fff", border, backdropFilter: "blur(6px)", height: "100%", boxSizing: "border-box" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div className="label" style={{ opacity: 0.6 }}>Attacking Patterns · Live</div>
        <span className="chip-mono" style={{ color: dark ? "rgba(255,255,255,0.6)" : "rgba(0,0,0,0.6)" }}>
          {totalAttacks} attacks
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
        <StatMini label="Dominant Flank" value={dominant} dark={dark} />
        <StatMini label="Avg xG/Attack" value={avgXg.toFixed(3)} dark={dark} />
      </div>

      <div style={{ height: 100 }}>
        <ResponsiveContainer>
          <BarChart data={flankData} barCategoryGap="20%">
            <XAxis dataKey="name" stroke={dark ? "#666" : "#999"} fontSize={10} tickLine={false} axisLine={false} />
            <YAxis hide />
            <Tooltip
              contentStyle={{ background: dark ? "#0a0a0a" : "#fff", border: `1px solid ${dark ? "#222" : "#ddd"}`, borderRadius: 0, fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}
            />
            <Bar dataKey="value" fill="#E30613" radius={0} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {data?.insight && (
        <div style={{ marginTop: 8, fontSize: 11, opacity: 0.6, fontFamily: "JetBrains Mono, monospace", lineHeight: 1.5, borderLeft: "2px solid var(--uc-red)", paddingLeft: 8 }}>
          {data.insight}
        </div>
      )}
    </div>
  );
}

function StatMini({ label, value, dark }) {
  const border = dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.08)";
  return (
    <div style={{ border, padding: "8px 10px" }}>
      <div className="label" style={{ opacity: 0.5, fontSize: 9 }}>{label}</div>
      <div className="font-display" style={{ fontWeight: 900, fontSize: 20, textTransform: "uppercase" }}>{value}</div>
    </div>
  );
}
