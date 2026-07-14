import { useEffect, useRef } from "react";
import { impactBump } from "./impactTiming";

/**
 * Un drone di sottofondo continuo che segue lo scroll: cutoff del filtro
 * e volume salgono avvicinandosi allo scontro, un impulso più acuto
 * esplode al momento dell'impatto, poi tutto si assesta di nuovo verso
 * il basso — un crescendo vero, non un loop statico. I browser bloccano
 * l'audio senza un gesto dell'utente: parte al primo scroll/tocco/click,
 * in silenzio se non arriva mai (niente errori, nessun blocco visibile).
 */
export default function useAmbientAudio(progressRef, enabledRef) {
  useEffect(() => {
    let ctx = null;
    let nodes = null;
    let raf = null;
    let started = false;

    function start() {
      if (started) return;
      started = true;
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      ctx = new Ctx();

      const osc1 = ctx.createOscillator();
      osc1.type = "sawtooth";
      osc1.frequency.value = 54;
      const osc2 = ctx.createOscillator();
      osc2.type = "sine";
      osc2.frequency.value = 54 * 1.5;
      const osc3 = ctx.createOscillator();
      osc3.type = "triangle";
      osc3.frequency.value = 27;

      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.value = 220;
      filter.Q.value = 0.9;

      const gain = ctx.createGain();
      gain.gain.value = 0;

      osc1.connect(filter);
      osc2.connect(filter);
      osc3.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);

      osc1.start();
      osc2.start();
      osc3.start();
      gain.gain.linearRampToValueAtTime(enabledRef.current ? 0.045 : 0, ctx.currentTime + 2.5);

      nodes = { osc1, osc2, osc3, filter, gain };

      const loop = () => {
        if (ctx && nodes) {
          const p = Math.min(Math.max(progressRef.current || 0, 0), 1);
          const bump = impactBump(p);
          const t = ctx.currentTime;
          const targetFreq = 220 + p * 900 + bump * 2200;
          const targetGain = enabledRef.current ? 0.035 + p * 0.05 + bump * 0.09 : 0;
          nodes.filter.frequency.setTargetAtTime(targetFreq, t, 0.4);
          nodes.gain.gain.setTargetAtTime(targetGain, t, 0.5);
        }
        raf = requestAnimationFrame(loop);
      };
      loop();
    }

    const opts = { once: true, passive: true };
    window.addEventListener("scroll", start, opts);
    window.addEventListener("touchstart", start, opts);
    window.addEventListener("click", start, opts);
    window.addEventListener("keydown", start, opts);

    return () => {
      window.removeEventListener("scroll", start, opts);
      window.removeEventListener("touchstart", start, opts);
      window.removeEventListener("click", start, opts);
      window.removeEventListener("keydown", start, opts);
      if (raf) cancelAnimationFrame(raf);
      if (ctx) {
        try {
          ctx.close();
        } catch {
          // già chiuso o mai partito: nulla da fare
        }
      }
    };
  }, [progressRef, enabledRef]);
}
