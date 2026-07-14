import { useEffect, useRef, useState } from "react";

const CHARS = "01アイウエオ<>/[]{}#%&*ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const STEPS = 14;
const STEP_MS = 32;

/**
 * Il titolo non appare con un semplice fade — si "decodifica": parte
 * come una sequenza di caratteri casuali (stile terminale/IA) e si
 * assesta rapidamente, da sinistra a destra, nel testo vero, non appena
 * la sezione si blocca in posizione (trigger passato da GlassCard in
 * base allo scroll).
 */
export default function ScrambleText({ text, trigger }) {
  const [display, setDisplay] = useState(text);
  const done = useRef(false);
  const timer = useRef();

  useEffect(() => {
    if (!trigger || done.current) return;
    done.current = true;
    const letters = text.split("");
    const revealCount = new Array(letters.length).fill(0);
    let iter = 0;

    const step = () => {
      iter++;
      const threshold = Math.floor((iter / STEPS) * letters.length);
      const out = letters.map((ch, i) => {
        if (ch === " ") return " ";
        if (i < threshold) return ch;
        return CHARS[Math.floor(Math.random() * CHARS.length)];
      });
      setDisplay(out.join(""));
      if (iter < STEPS) {
        timer.current = setTimeout(step, STEP_MS);
      } else {
        setDisplay(text);
      }
    };
    step();
    return () => clearTimeout(timer.current);
  }, [trigger, text]);

  return display;
}
