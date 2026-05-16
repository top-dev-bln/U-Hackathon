import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

export default function XGComparison({ liveState }) {
  const home = liveState?.xg_home ?? 0;
  const away = liveState?.xg_away ?? 0;
  const gh = liveState?.score?.home ?? 0;
  const ga = liveState?.score?.away ?? 0;

  const data = [
    { team: liveState?.home || "U CLUJ", xG: home, Goals: gh },
    { team: liveState?.away || "OPP", xG: away, Goals: ga },
  ];

  return (
    <div style={{ padding: 24, background: "#fff", border: "1px solid rgba(0,0,0,0.1)" }}>
      <div className="label" style={{ opacity: 0.6, marginBottom: 16 }}>xG Created vs Goals Scored</div>

      <div style={{ height: 320 }}>
        <ResponsiveContainer>
          <BarChart data={data} barCategoryGap="30%">
            <CartesianGrid stroke="rgba(0,0,0,0.06)" vertical={false} />
            <XAxis dataKey="team" stroke="#525252" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis stroke="#525252" fontSize={11} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ background: "#fff", border: "1px solid #ddd", borderRadius: 0, fontFamily: "JetBrains Mono, monospace", fontSize: 11 }} />
            <Legend wrapperStyle={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.18em" }} />
            <Bar dataKey="xG" fill="#0a0a0a" />
            <Bar dataKey="Goals" fill="#E30613" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 16 }}>
        <InsightBox team={liveState?.home || "U CLUJ"} xg={home} g={gh} />
        <InsightBox team={liveState?.away || "OPP"} xg={away} g={ga} />
      </div>
    </div>
  );
}

function InsightBox({ team, xg, g }) {
  const diff = (g - xg).toFixed(2);
  const over = Number(diff) >= 0;
  return (
    <div style={{ border: "1px solid rgba(0,0,0,0.1)", padding: 12 }}>
      <div className="label" style={{ opacity: 0.6 }}>{team}</div>
      <div className="font-display" style={{ fontWeight: 700, fontSize: 16, marginTop: 4 }}>
        {over ? "Outperforming" : "Underperforming"} xG by{" "}
        <span style={{ color: over ? "#16a34a" : "var(--uc-red)" }}>
          {over ? "+" : ""}{diff}
        </span>
      </div>
    </div>
  );
}
