import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Canvas } from "@react-three/fiber";
import { Moon, Cog, GitBranch, MessageCircle, Scale, Volume2, VolumeX } from "lucide-react";
import GlassCard from "./GlassCard";
import Scene from "./Scene";
import HUDForeground from "./HUDForeground";
import useAmbientAudio from "./useAmbientAudio";
import { STEPS, N_SECTIONS } from "./content";
import "./Landing3D.css";

const STEP_ICONS = [Moon, Cog, GitBranch, MessageCircle, Scale];

function supportsWebGL() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl") || c.getContext("experimental-webgl")));
  } catch {
    return false;
  }
}

/**
 * NEXUS — landing cinematica. Niente illustrazioni: un unico oggetto 3D
 * vero, la N di NEXUS (geometria reale, non un'immagine), dentro uno
 * spazio nero con luci, un pavimento che riflette e una camera che le
 * gira intorno e ci vola dentro scrollando — libera e profonda, non un
 * punto fermo. Se il browser non supporta WebGL, resta visibile un
 * fondale a gradiente statico — non sparisce mai del tutto.
 */
export default function Landing3D() {
  const navigate = useNavigate();
  const rootRef = useRef(null);
  const sectionRefs = useRef([]);
  const progressRef = useRef(0);
  const velocityRef = useRef(0);
  const enabledRef = useRef(true);
  const [webglOk] = useState(supportsWebGL);
  const [audioOn, setAudioOn] = useState(true);

  useAmbientAudio(progressRef, enabledRef);

  const toggleAudio = () => {
    enabledRef.current = !enabledRef.current;
    setAudioOn(enabledRef.current);
  };

  const goTo = (i) => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    sectionRefs.current[i]?.scrollIntoView({ behavior: reduce ? "auto" : "smooth" });
  };

  useEffect(() => {
    const prevTitle = document.title;
    const metaDesc = document.querySelector('meta[name="description"]');
    const prevDesc = metaDesc ? metaDesc.getAttribute("content") : null;
    document.title = "NEXUS — Viaggio nel motore di trading algoritmico";
    if (metaDesc) {
      metaDesc.setAttribute(
        "content",
        "NEXUS opera l'oro validando ogni strategia su due finestre temporali indipendenti prima di fidarsene. Entra nel motore."
      );
    }
    return () => {
      document.title = prevTitle;
      if (metaDesc && prevDesc !== null) metaDesc.setAttribute("content", prevDesc);
    };
  }, []);

  // Progresso di scroll sull'intera pagina (0..1) — pilota sia la camera 3D
  // sia il punto del video mostrato (VideoScreen legge lo stesso ref).
  useEffect(() => {
    const onScroll = () => {
      const m = document.documentElement.scrollHeight - window.innerHeight;
      progressRef.current = m > 0 ? window.scrollY / m : 0;
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);

  // Velocità di scroll → peso/inerzia percepiti: uno skewY leggerissimo su
  // testi ed energia, un filo di motion blur, mentre si scrolla veloce.
  // Non è agganciato a un singolo evento scroll (che smette di sparare
  // quando l'utente si ferma): un loop continuo smussa verso la velocità
  // istantanea e, appena lo scroll si ferma, quella stessa smussatura la
  // riporta a zero da sola — l'equivalente di una molla senza libreria di
  // fisica dedicata.
  //
  // Il loop però NON gira per sempre: un requestAnimationFrame perenne che
  // scrive 3 custom property ad ogni frame, 60 volte al secondo, anche a
  // scroll fermo da minuti, è lavoro sprecato che compete con il thread
  // che gestisce lo scroll stesso — probabile causa di uno scroll
  // "impastato" su schermi non velocissimi. Si ferma da solo appena la
  // velocità è tornata a zero (valori arrotondati abbastanza da produrre
  // la stessa stringa, cosicché il motore CSS non re-invalidi lo stile a
  // ogni frame anche negli ultimi istanti prima di fermarsi) e riparte al
  // scroll successivo.
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return undefined;
    let raf = null;
    let lastY = window.scrollY;
    let lastT = performance.now();
    let vel = 0;
    let idleFrames = 0;

    const tick = (t) => {
      const dt = Math.max(t - lastT, 1);
      const y = window.scrollY;
      const instant = y - lastY;
      lastY = y;
      lastT = t;
      const k = Math.min(dt / 140, 1);
      vel += (instant - vel) * k;
      velocityRef.current = vel;

      if (rootRef.current) {
        const skewDeg = Math.max(-7, Math.min(7, -vel * 0.35));
        const blurPx = Math.min(Math.abs(vel) * 0.22, 3.5);
        const velNorm = Math.min(Math.abs(vel) / 18, 1);
        rootRef.current.style.setProperty("--nx3d-skew", `${skewDeg.toFixed(2)}deg`);
        rootRef.current.style.setProperty("--nx3d-blur", `${blurPx.toFixed(2)}px`);
        rootRef.current.style.setProperty("--nx3d-vel", velNorm.toFixed(2));
      }

      if (Math.abs(vel) < 0.05) {
        idleFrames += 1;
        if (idleFrames > 20) {
          raf = null;
          return; // ferma il loop: si riattiva al prossimo scroll
        }
      } else {
        idleFrames = 0;
      }
      raf = requestAnimationFrame(tick);
    };

    const ensureRunning = () => {
      if (raf === null) {
        lastY = window.scrollY;
        lastT = performance.now();
        idleFrames = 0;
        raf = requestAnimationFrame(tick);
      }
    };
    raf = requestAnimationFrame(tick);
    window.addEventListener("scroll", ensureRunning, { passive: true });
    return () => {
      window.removeEventListener("scroll", ensureRunning);
      if (raf !== null) cancelAnimationFrame(raf);
    };
  }, []);

  // Quale sezione è attiva: un IntersectionObserver per sezione, solo per
  // la rail dei puntini e l'etichetta — indipendente dalla camera 3D.
  useEffect(() => {
    const railBtns = [...rootRef.current.querySelectorAll(".nx3d-rail button")];
    const sectionLabel = rootRef.current.querySelector("#nx3d-hud-section");
    const sections = sectionRefs.current.filter(Boolean);
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!visible) return;
        const idx = sections.indexOf(visible.target);
        if (idx < 0) return;
        railBtns.forEach((b, i) => b.classList.toggle("on", i === idx));
        if (sectionLabel) sectionLabel.textContent = `SEZIONE 0${idx + 1} / 0${N_SECTIONS}`;
      },
      { threshold: [0.5, 0.7, 0.9] }
    );
    sections.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <div className="nx3d" ref={rootRef}>
      {webglOk ? (
        <div className="nx3d-gl-wrap">
          <Canvas
            shadows
            camera={{ fov: 45, near: 0.1, far: 80, position: [0, 2.4, 15] }}
            gl={{ antialias: true, powerPreference: "high-performance" }}
            dpr={[1, 2]}
          >
            <Scene progressRef={progressRef} />
          </Canvas>
        </div>
      ) : (
        <div className="nx3d-video-bg nx3d-fallback-bg" aria-hidden="true" />
      )}
      <div className="nx3d-video-scrim" aria-hidden="true" />

      <HUDForeground />

      <button
        type="button"
        className="nx3d-audio-btn"
        onClick={toggleAudio}
        aria-label={audioOn ? "Disattiva audio" : "Attiva audio"}
        aria-pressed={audioOn}
      >
        {audioOn ? <Volume2 size={17} strokeWidth={1.8} /> : <VolumeX size={17} strokeWidth={1.8} />}
      </button>

      <div className="nx3d-hud" aria-hidden="true">
        <span className="nx3d-hud-corner tl" />
        <span className="nx3d-hud-corner tr" />
        <span className="nx3d-hud-corner bl" />
        <span className="nx3d-hud-corner br" />
        <div className="nx3d-hud-sweep" />
        <div className="nx3d-hud-label tl">NEXUS · XAU/USD</div>
        <div className="nx3d-hud-label tr">MOTORE MULTI-TIMEFRAME</div>
        <div className="nx3d-hud-label bl">VALIDAZIONE · 3M + 3Y</div>
        <div className="nx3d-hud-label br" id="nx3d-hud-section">SEZIONE 01 / 0{N_SECTIONS}</div>
      </div>

      <aside className="nx3d-glasspanel left" aria-hidden="true">
        <div className="nx3d-gp-title">Motore</div>
        <div className="nx3d-gp-row"><span>Simbolo</span><b>XAU/USD</b></div>
        <div className="nx3d-gp-row"><span>Modalità</span><b>Hedge</b></div>
        <div className="nx3d-gp-row"><span>Stato</span><b>Sempre attivo</b></div>
      </aside>
      <aside className="nx3d-glasspanel right" aria-hidden="true">
        <div className="nx3d-gp-title">Validazione</div>
        <div className="nx3d-gp-row"><span>Finestre</span><b>2</b></div>
        <div className="nx3d-gp-row"><span>Storico</span><b>10 anni</b></div>
        <div className="nx3d-gp-row"><span>Metodo</span><b>Doppio test</b></div>
      </aside>

      <nav className="nx3d-rail" aria-label="Sezioni">
        {Array.from({ length: N_SECTIONS }).map((_, i) => (
          <button key={i} className={i === 0 ? "on" : undefined} aria-label={`Sezione ${i + 1}`} onClick={() => goTo(i)} />
        ))}
      </nav>

      <main className="nx3d-scroll">
        <section className="nx3d-panel center" ref={(el) => { sectionRefs.current[0] = el; }}>
          <GlassCard center wide className="max-w-[880px]">
            <span className="nx3d-eyebrow justify-center">Trading algoritmico · costruito con l'AI</span>
            <h1>NEXUS</h1>
            <p className="nx3d-lede">Il motore che pensa per te, <b>mentre tu vivi la tua vita</b>.</p>
            <p className="mt-4 max-w-[46ch] mx-auto text-[clamp(16px,1.5vw,19px)] font-medium leading-relaxed text-white/85">
              Non un altro EA scritto a mano e abbandonato al suo destino. Un sistema progettato, testato e corretto da
              un'intelligenza artificiale che non dorme mai.
            </p>
            <div className="nx3d-cta">
              <button className="nx3d-btn primary" onClick={() => navigate("/login")}>Entra nel motore</button>
              <button className="nx3d-btn" onClick={() => goTo(1)}>Perché ti serve</button>
            </div>
            <p className="nx3d-disc">Risultati da backtest su dati storici: non sono garanzia di rendimenti futuri. Il trading a leva comporta rischio di perdita del capitale.</p>
          </GlassCard>
        </section>

        {STEPS.map((s, i) => {
          const Icon = STEP_ICONS[i];
          return (
            <section
              className="nx3d-panel step"
              key={s.badge}
              ref={(el) => { sectionRefs.current[i + 1] = el; }}
            >
              <div className="nx3d-step-icon" aria-hidden="true"><Icon size={32} strokeWidth={1.6} /></div>
              <GlassCard badge={s.badge} title={s.title} index={i}>
                <p className="mt-3.5 text-[16px] font-medium text-white/85 leading-relaxed">{s.desc}</p>
              </GlassCard>
            </section>
          );
        })}
      </main>
    </div>
  );
}
