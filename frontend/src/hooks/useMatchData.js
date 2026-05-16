import { useEffect, useRef, useState, useCallback } from "react";
import { fetchState } from "../lib/api";

export default function useMatchData(pollMs = 2000, enabled = true) {
  const [state, setState] = useState(null);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  const tick = useCallback(async () => {
    try {
      const s = await fetchState();
      setState(s);
      setError(null);
    } catch (e) {
      setError(e?.message || "fetch error");
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    tick();
    timerRef.current = setInterval(tick, pollMs);
    return () => clearInterval(timerRef.current);
  }, [tick, pollMs, enabled]);

  return { state, error, refresh: tick };
}
