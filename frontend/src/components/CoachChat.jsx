import { useState, useRef, useEffect } from "react";
import { fetchChat } from "../lib/api";
import { Sparkles, Send, Loader2 } from "lucide-react";

const SUGGESTED = [
  "What were our biggest defensive issues?",
  "Which player had the best pressing efficiency?",
  "Why did we lose momentum in the second half?",
  "What tactical changes should we make next match?",
  "Explain the key moments that decided the match.",
];

const MOCK_ANSWERS = {
  default: [
    "Based on the match data, the pressing efficiency dropped significantly after the 60th minute, particularly in the central midfield zones. Bic's intensity metrics show clear fatigue patterns starting at minute 63.",
    "The passing network analysis reveals strong connectivity between Nistor and Popa (16 exchanges), but weak coverage on the right flank — Gheorghe was isolated with only 6 exchanges with the striker.",
    "U Cluj dominated possession in the first half with 55% pressing intensity, but Hermannstadt exploited the space left behind Chipciu's overlapping runs in the second half.",
    "Decision quality data shows 3 high-value shooting opportunities missed by Popa (combined xG 0.91). Earlier shot decisions in the box could have changed the result.",
    "The line-breaking analysis identifies Stoica as the most dangerous runner — 10 of his runs led directly to shots on target, with an average of 34m per progressive run.",
  ],
};

let mockIdx = 0;

export default function CoachChat({ matchId, match }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: `Ready to analyze **${match?.home || "U Cluj"} ${match?.score || ""} ${match?.away || ""}** (${match?.date || ""}). Ask me anything about tactics, player performance, or key moments.`,
    },
  ]);
  const [input, setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text) => {
    const q = (text || input).trim();
    if (!q || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setLoading(true);
    try {
      const r = await fetchChat(q, matchId);
      setMessages((m) => [...m, { role: "assistant", text: r.answer || r.insight || r.response }]);
    } catch {
      // fallback mock
      const answer = MOCK_ANSWERS.default[mockIdx % MOCK_ANSWERS.default.length];
      mockIdx++;
      setMessages((m) => [...m, { role: "assistant", text: answer }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "65vh", background: "#fff", border: "1px solid rgba(0,0,0,0.1)" }}>

      {/* Header */}
      <div style={{ padding: "14px 20px", borderBottom: "1px solid rgba(0,0,0,0.08)", display: "flex", alignItems: "center", gap: 8 }}>
        <Sparkles size={14} color="var(--uc-red)" />
        <span className="label" style={{ fontWeight: 700, fontSize: 12 }}>AI Coach Assistant</span>
        <span className="font-mono" style={{ fontSize: 10, opacity: 0.4, marginLeft: "auto" }}>
          {match?.home} {match?.score} {match?.away} · {match?.date}
        </span>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: msg.role === "user" ? "flex-end" : "flex-start" }}>
            <div style={{
              maxWidth: "78%",
              padding: "10px 14px",
              fontSize: 13,
              lineHeight: 1.6,
              background: msg.role === "user" ? "#0a0a0a" : "#f4f4f4",
              color: msg.role === "user" ? "#fff" : "#0a0a0a",
              borderLeft: msg.role === "assistant" ? "3px solid var(--uc-red)" : "none",
            }}>
              {msg.text}
            </div>
            <span style={{ fontSize: 10, opacity: 0.35, marginTop: 3, fontFamily: "JetBrains Mono, monospace" }}>
              {msg.role === "user" ? "Coach" : "AI Analyst"}
            </span>
          </div>
        ))}

        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, opacity: 0.5, fontSize: 12 }}>
            <Loader2 size={13} style={{ animation: "spin 1s linear infinite" }} />
            <span style={{ fontFamily: "JetBrains Mono, monospace" }}>Analyzing match data…</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggested questions */}
      {messages.length <= 1 && (
        <div style={{ padding: "0 20px 12px", display: "flex", gap: 6, flexWrap: "wrap" }}>
          {SUGGESTED.map((s, i) => (
            <button
              key={i}
              onClick={() => send(s)}
              style={{
                fontSize: 11,
                fontFamily: "JetBrains Mono, monospace",
                padding: "5px 10px",
                background: "none",
                border: "1px solid rgba(0,0,0,0.15)",
                cursor: "pointer",
                color: "rgba(0,0,0,0.6)",
                transition: "all 0.15s",
              }}
              onMouseEnter={(e) => { e.target.style.borderColor = "var(--uc-red)"; e.target.style.color = "var(--uc-red)"; }}
              onMouseLeave={(e) => { e.target.style.borderColor = "rgba(0,0,0,0.15)"; e.target.style.color = "rgba(0,0,0,0.6)"; }}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={{ padding: "12px 20px", borderTop: "1px solid rgba(0,0,0,0.08)", display: "flex", gap: 10 }}>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask about tactics, players, key moments…"
          style={{
            flex: 1,
            padding: "10px 14px",
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 12,
            border: "1px solid rgba(0,0,0,0.15)",
            outline: "none",
            background: "#fafafa",
          }}
        />
        <button
          onClick={() => send()}
          disabled={!input.trim() || loading}
          style={{
            padding: "10px 16px",
            background: input.trim() && !loading ? "#0a0a0a" : "rgba(0,0,0,0.08)",
            border: "none",
            cursor: input.trim() && !loading ? "pointer" : "default",
            color: input.trim() && !loading ? "#fff" : "rgba(0,0,0,0.3)",
            display: "flex", alignItems: "center", gap: 6,
            transition: "all 0.2s",
          }}
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
