import { useEffect, useRef } from "react";

/** Polls only while the document is visible and resumes immediately on focus. */
export function useVisiblePolling(callback, intervalMs, enabled = true) {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    if (!enabled) return undefined;
    let timer = null;
    let inFlight = false;
    const run = async () => {
      if (inFlight) return;
      inFlight = true;
      try { await callbackRef.current(); }
      finally { inFlight = false; }
    };
    const stop = () => {
      if (timer !== null) window.clearInterval(timer);
      timer = null;
    };
    const start = () => {
      stop();
      if (document.visibilityState === "visible") {
        run();
        timer = window.setInterval(run, intervalMs);
      }
    };
    const onVisibility = () => {
      if (document.visibilityState === "visible") start();
      else stop();
    };
    document.addEventListener("visibilitychange", onVisibility);
    start();
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [enabled, intervalMs]);
}
