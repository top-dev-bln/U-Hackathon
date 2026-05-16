import { AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";

export default function XGTracker({ history = [], home = "U CLUJ", away = "OPP", dark = true }) {
  const data = history.map((h) => ({ minute: h.minute, home: h.home, away: h.away }));
  const last = data[data.length - 1] || { home: 0, away: 0 };
  const stroke = dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)";
  const textColor = dark ? "#a3a3a3" : "#525252";
  const border = dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.1)";

  return (
    <div style={{ padding: 20, background: dark ? "rgba(20,20,20,0.6)" : "#fff", border, backdropFilter: "blur(6px)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div className="label" style={{ opacity: 0.6 }}>xG · Live</div>
        <div className="font-mono" style={{ fontSize: 10, opacity: 0.6 }}>vs minute</div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
        <StatBox label={home} value={(last.home ?? 0).toFixed(2)} color={dark ? "#fff" : "#0a0a0a"} dark={dark} />
        <StatBox label={away} value={(last.away ?? 0).toFixed(2)} color="var(--uc-red)" dark={dark} />
      </div>

      <div style={{ height: 160 }}>
        <ResponsiveContainer>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="gHome" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={dark ? "#ffffff" : "#0a0a0a"} stopOpacity={0.5} />
                <stop offset="100%" stopColor={dark ? "#ffffff" : "#0a0a0a"} stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gAway" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#E30613" stopOpacity={0.55} />
                <stop offset="100%" stopColor="#E30613" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={stroke} vertical={false} />
            <XAxis dataKey="minute" stroke={textColor} fontSize={10} tickLine={false} axisLine={false} />
            <YAxis stroke={textColor} fontSize={10} tickLine={false} axisLine={false} width={28} />
            <Tooltip
              contentStyle={{
                background: dark ? "#0a0a0a" : "#fff",
                border: `1px solid ${dark ? "#222" : "#ddd"}`,
                borderRadius: 0,
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 11,
              }}
            />
            <Area type="monotone" dataKey="home" stroke={dark ? "#fff" : "#0a0a0a"} strokeWidth={1.5} fill="url(#gHome)" />
            <Area type="monotone" dataKey="away" stroke="#E30613" strokeWidth={1.5} fill="url(#gAway)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function StatBox({ label, value, color, dark }) {
  const border = dark ? "1px solid rgba(255,255,255,0.1)" : "1px solid rgba(0,0,0,0.1)";
  return (
    <div style={{ border, padding: 12 }}>
      <div className="label" style={{ opacity: 0.6 }}>{label}</div>
      <div className="font-display" style={{ fontWeight: 900, fontSize: 28, color }}>{value}</div>
    </div>
  );
}
