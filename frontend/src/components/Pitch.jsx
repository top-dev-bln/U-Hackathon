export default function Pitch({ dark = true, children, className = "" }) {
  const stroke = "#ffffff";
  const sw = 0.5;
  const bg = "#4a8c3a";

  return (
    <svg
      viewBox="0 0 100 68"
      className={className}
      style={{ width: "100%", height: "100%", display: "block" }}
      preserveAspectRatio="xMidYMid meet"
    >
      {/* Solid green background */}
      <rect x="0" y="0" width="100" height="68" fill={bg} />

      {/* Outer border */}
      <rect x="2" y="2" width="96" height="64" fill="none" stroke={stroke} strokeWidth={sw} />

      {/* Halfway line */}
      <line x1="50" y1="2" x2="50" y2="66" stroke={stroke} strokeWidth={sw} />

      {/* Centre circle */}
      <circle cx="50" cy="34" r="9.15" fill="none" stroke={stroke} strokeWidth={sw} />
      {/* Centre spot */}
      <circle cx="50" cy="34" r="0.7" fill={stroke} />

      {/* Corner arcs */}
      <path d="M 2 5.5  A 3.5 3.5 0 0 1 5.5 2"   fill="none" stroke={stroke} strokeWidth={sw} />
      <path d="M 94.5 2 A 3.5 3.5 0 0 1 98 5.5"  fill="none" stroke={stroke} strokeWidth={sw} />
      <path d="M 2 62.5 A 3.5 3.5 0 0 0 5.5 66"  fill="none" stroke={stroke} strokeWidth={sw} />
      <path d="M 94.5 66 A 3.5 3.5 0 0 0 98 62.5" fill="none" stroke={stroke} strokeWidth={sw} />

      {/* ── LEFT PENALTY AREA (16.5m box) ── */}
      <rect x="2" y="15" width="16.5" height="38" fill="none" stroke={stroke} strokeWidth={sw} />
      {/* Left 6-yard box */}
      <rect x="2" y="25.5" width="5.5" height="17" fill="none" stroke={stroke} strokeWidth={sw} />
      {/* Left penalty spot */}
      <circle cx="13.5" cy="34" r="0.6" fill={stroke} />
      {/* Left penalty arc */}
      <path d="M 18.5 26.5 A 9.15 9.15 0 0 1 18.5 41.5" fill="none" stroke={stroke} strokeWidth={sw} />
      {/* Left goal */}
      <rect x="-0.5" y="29.5" width="2.5" height="9" fill="none" stroke={stroke} strokeWidth={sw} />

      {/* ── RIGHT PENALTY AREA ── */}
      <rect x="81.5" y="15" width="16.5" height="38" fill="none" stroke={stroke} strokeWidth={sw} />
      {/* Right 6-yard box */}
      <rect x="92.5" y="25.5" width="5.5" height="17" fill="none" stroke={stroke} strokeWidth={sw} />
      {/* Right penalty spot */}
      <circle cx="86.5" cy="34" r="0.6" fill={stroke} />
      {/* Right penalty arc */}
      <path d="M 81.5 26.5 A 9.15 9.15 0 0 0 81.5 41.5" fill="none" stroke={stroke} strokeWidth={sw} />
      {/* Right goal */}
      <rect x="98" y="29.5" width="2.5" height="9" fill="none" stroke={stroke} strokeWidth={sw} />

      {children}
    </svg>
  );
}
