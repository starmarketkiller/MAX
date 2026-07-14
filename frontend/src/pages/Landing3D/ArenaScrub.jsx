import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

const FRAME_COUNT = 97;
const EAGER_COUNT = 14; // caricati subito, bloccano il "pronto"; il resto arriva in background
const PIN_DISTANCE = "+=380%"; // quanto scroll serve per scorrere tutti i frame

const frameUrl = (i) => `${process.env.PUBLIC_URL}/arena/f${String(i + 1).padStart(3, "0")}.webp`;

/**
 * L'arena: 97 frame di un video generato via AI (toro vs orso, cyberpunk),
 * proiettati su un <canvas> 2D e scrubbati con lo scroll — non un <video>
 * con seek diretto (il file ha B-frame, il seek non e' mai fluido), ma una
 * sequenza di immagini disegnate a mano, frame per frame, in base al
 * progresso dello scroll. E' lo standard per gli hero cinematici (stile
 * Apple). Sostituisce l'hero R3F: canvas 2D separato dal <Canvas> R3F della
 * scena successiva, che comincia solo dopo questa sezione.
 *
 * L'ultimo ~15% dello scroll pinnato tiene fermo sull'ultimo frame e fa
 * apparire il contenuto passato come children (il reveal di NEXUS) — lo
 * scroll resta "bloccato" (pin) finche' non e' del tutto visibile, come
 * da richiesta.
 */
export default function ArenaScrub({ children, arenaDpr = 2, progressRef, onReady }) {
  const sectionRef = useRef(null);
  const canvasRef = useRef(null);
  const heroRef = useRef(null);
  const vignetteRef = useRef(null);
  const hintRef = useRef(null);
  const imagesRef = useRef([]);
  const [ready, setReady] = useState(false);
  const [loadPct, setLoadPct] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const imgs = new Array(FRAME_COUNT);
    let loaded = 0;

    const loadOne = (i) =>
      new Promise((resolve) => {
        const img = new Image();
        img.onload = img.onerror = () => {
          loaded += 1;
          if (i < EAGER_COUNT) setLoadPct(Math.round((loaded / EAGER_COUNT) * 100));
          resolve(img);
        };
        img.src = frameUrl(i);
        imgs[i] = img;
      });

    (async () => {
      await Promise.all(Array.from({ length: EAGER_COUNT }, (_, i) => loadOne(i)));
      if (cancelled) return;
      imagesRef.current = imgs;
      setReady(true);
      for (let i = EAGER_COUNT; i < FRAME_COUNT; i++) loadOne(i); // il resto in sordina
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!ready) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio, arenaDpr);
    let lastDrawn = -1;

    const resize = () => {
      canvas.width = Math.round(window.innerWidth * dpr);
      canvas.height = Math.round(window.innerHeight * dpr);
      canvas.style.width = "100%";
      canvas.style.height = "100%";
      lastDrawn = -1; // ridisegna al prossimo frame utile dopo un resize
    };
    resize();
    window.addEventListener("resize", resize);

    const drawFrame = (idx) => {
      const clamped = Math.max(0, Math.min(FRAME_COUNT - 1, idx));
      // se il frame target non e' ancora arrivato, resta sull'ultimo buono
      // invece di lampeggiare un canvas vuoto durante uno scroll veloce.
      let useIdx = clamped;
      while (useIdx > 0 && !(imagesRef.current[useIdx]?.complete && imagesRef.current[useIdx]?.naturalWidth)) {
        useIdx -= 1;
      }
      if (useIdx === lastDrawn) return;
      const img = imagesRef.current[useIdx];
      if (!img || !img.naturalWidth) return;
      lastDrawn = useIdx;
      const cw = canvas.width;
      const ch = canvas.height;
      const scale = Math.max(cw / img.naturalWidth, ch / img.naturalHeight);
      const dw = img.naturalWidth * scale;
      const dh = img.naturalHeight * scale;
      ctx.clearRect(0, 0, cw, ch);
      ctx.drawImage(img, (cw - dw) / 2, (ch - dh) / 2, dw, dh);
    };
    drawFrame(0);

    const st = ScrollTrigger.create({
      trigger: sectionRef.current,
      start: "top top",
      end: PIN_DISTANCE,
      pin: true,
      pinSpacing: true,
      scrub: 0.4,
      onUpdate: (self) => {
        const p = self.progress;
        if (progressRef) progressRef.current = p;
        // 0-85% dello scroll pinnato = scrubbing dei frame; 85-100% = hold
        // sull'ultimo frame mentre il reveal NEXUS sale in dissolvenza.
        const scrubP = Math.min(p / 0.85, 1);
        drawFrame(Math.round(scrubP * (FRAME_COUNT - 1)));
        const revealP = Math.max(0, (p - 0.85) / 0.15);
        if (heroRef.current) {
          heroRef.current.style.opacity = revealP;
          heroRef.current.style.pointerEvents = revealP > 0.5 ? "auto" : "none";
          heroRef.current.style.transform = `translateY(${(1 - revealP) * 24}px)`;
        }
        if (vignetteRef.current) vignetteRef.current.style.opacity = Math.min(1, revealP * 1.4) * 0.72;
        if (hintRef.current) hintRef.current.style.opacity = p > 0.02 ? "0" : "0.85";
      },
    });

    // Il pin di quest'arena inserisce uno spacer che allunga il documento —
    // se il ScrollTrigger del "journey" (in index.jsx) venisse creato prima
    // che questo spacer esista, misurerebbe il documento ancora corto e
    // resterebbe con confini sbagliati per tutta la sessione (un refresh
    // successivo non basta: a quel punto e' gia' cache-ato). Invece di
    // inseguire il timing di un refresh, avvisiamo index.jsx che puo' creare
    // il suo ScrollTrigger solo ORA — doppio rAF perche' ScrollTrigger.create
    // (pin:true) non commette il layout del pin-spacer nello stesso tick.
    requestAnimationFrame(() => requestAnimationFrame(() => onReady?.()));

    return () => {
      st.kill();
      window.removeEventListener("resize", resize);
    };
  }, [ready, arenaDpr]);

  return (
    <section ref={sectionRef} className="nx-arena">
      <canvas ref={canvasRef} className="nx-arena-canvas" />
      {!ready && (
        <div className="nx-arena-loading">
          <span className="nx-arena-loading-bar"><span style={{ width: `${loadPct}%` }} /></span>
          <span>Caricamento arena · {loadPct}%</span>
        </div>
      )}
      <div ref={vignetteRef} className="nx-arena-vignette" aria-hidden="true" />
      <div ref={heroRef} className="nx-arena-hero">
        {children}
      </div>
      {ready && <div ref={hintRef} className="nx-arena-hint">Scrolla per entrare nell'arena</div>}
    </section>
  );
}
