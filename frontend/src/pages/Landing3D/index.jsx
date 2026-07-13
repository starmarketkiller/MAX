import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Canvas } from "@react-three/fiber";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Moon, Cog, GitBranch, MessageCircle, Scale } from "lucide-react";
import Scene from "./Scene";
import GlassCard from "./GlassCard";
import { STEPS, N_SECTIONS } from "./content";
import "./Landing3D.css";

gsap.registerPlugin(ScrollTrigger);

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
 * NEXUS — landing 3D cinematica (React Three Fiber + GSAP ScrollTrigger).
 * La scena 3D (<Canvas>) e la UI HTML (overlay assoluto) sono due alberi
 * React separati: la scena non conosce i testi, la UI non conosce Three.js —
 * comunicano solo via `progressRef`/`mouseRef`, letti a ogni frame in useFrame
 * senza mai forzare un re-render React.
 */
export default function Landing3D() {
  const navigate = useNavigate();
  const rootRef = useRef(null);
  const scrollRef = useRef(null);
  const progressRef = useRef(0);
  const mouseRef = useRef({ x: 0, y: 0 });
  const [webglOk] = useState(supportsWebGL);

  const goTo = (i) => {
    const m = document.body.scrollHeight - window.innerHeight;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: m * (i / (N_SECTIONS - 1)), behavior: reduce ? "auto" : "smooth" });
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

  // Camera <-> scroll: un solo ScrollTrigger scrub-linked mappa lo scroll
  // dell'intera pagina a un progresso 0..1, letto da CameraRig via progressRef.
  useEffect(() => {
    if (!scrollRef.current) return;
    // scrub:true = nessun ritardo lato GSAP; l'unica inerzia della camera è il
    // lerp in CameraRig. Uno scrub numerico qui sopra sommerebbe una seconda
    // sorgente di smoothing e la camera impiegherebbe secondi a "arrivare".
    //
    // end come funzione (non "bottom bottom" su un trigger) perché l'altezza
    // reale del documento cambia quando i web font (Space Grotesk/JetBrains
    // Mono) finiscono di caricare — un end fissato al primo calcolo lascerebbe
    // la camera senza mai raggiungere il finale.
    const st = ScrollTrigger.create({
      start: 0,
      end: () => document.documentElement.scrollHeight - window.innerHeight,
      scrub: true,
      onUpdate: (self) => {
        progressRef.current = self.progress;
      },
    });
    const refresh = () => ScrollTrigger.refresh();
    window.addEventListener("load", refresh);
    document.fonts?.ready?.then(refresh);
    const fontTimer = setTimeout(refresh, 1200);
    const onMouse = (e) => {
      mouseRef.current.x = e.clientX / window.innerWidth - 0.5;
      mouseRef.current.y = e.clientY / window.innerHeight - 0.5;
    };
    window.addEventListener("mousemove", onMouse, { passive: true });

    const railBtns = [...rootRef.current.querySelectorAll(".nx3d-rail button")];
    const hint = rootRef.current.querySelector(".nx3d-hint");
    const sectionLabel = rootRef.current.querySelector("#nx3d-hud-section");
    let raf = 0;
    const uiTick = () => {
      const p = Math.min(Math.max(progressRef.current, 0), 1);
      const active = Math.round(p * (N_SECTIONS - 1));
      railBtns.forEach((b, i) => b.classList.toggle("on", i === active));
      if (hint) hint.style.opacity = p > 0.02 ? "0" : "0.85";
      if (sectionLabel) sectionLabel.textContent = `SEZIONE 0${active + 1} / 0${N_SECTIONS}`;
      rootRef.current.querySelectorAll(".nx3d-glasspanel").forEach((el, i) => {
        const side = i === 0 ? -1 : 1;
        el.style.transform = `translateY(calc(-50% + ${mouseRef.current.y * -14}px)) translateX(${side * mouseRef.current.x * 10}px)`;
      });
      raf = requestAnimationFrame(uiTick);
    };
    raf = requestAnimationFrame(uiTick);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("mousemove", onMouse);
      window.removeEventListener("load", refresh);
      clearTimeout(fontTimer);
      st.kill();
    };
  }, []);

  return (
    <div className="nx3d" ref={rootRef}>
      {webglOk ? (
        <div className="nx3d-gl-wrap">
          <Canvas
            camera={{ fov: 62, near: 0.1, far: 600, position: [0, 3, 15] }}
            gl={{ antialias: true, powerPreference: "high-performance" }}
            dpr={[1, 2]}
          >
            <Scene progressRef={progressRef} mouseRef={mouseRef} />
          </Canvas>
        </div>
      ) : (
        <div className="nx3d-fallback show">
          Il tuo browser non supporta WebGL.
          <br />
          Prova un browser aggiornato su desktop.
        </div>
      )}

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
      <div className="nx3d-hint">Scrolla per viaggiare nel motore</div>

      <main className="nx3d-scroll" ref={scrollRef}>
        <section className="nx3d-panel center">
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
          </GlassCard>
        </section>

        {STEPS.map((s, i) => {
          const Icon = STEP_ICONS[i];
          return (
            <section className="nx3d-panel step" key={s.badge}>
              <div className="nx3d-step-icon" aria-hidden="true"><Icon size={32} strokeWidth={1.6} /></div>
              <GlassCard badge={s.badge} title={s.title}>
                <p className="mt-3.5 text-[16px] font-medium text-white/85 leading-relaxed">{s.desc}</p>
              </GlassCard>
            </section>
          );
        })}

        <section className="nx3d-panel center">
          <GlassCard center>
            <span className="nx3d-eyebrow justify-center">Entra</span>
            <h2 className="m-0 mt-4 font-grotesk font-bold text-[clamp(38px,6vw,72px)] leading-[1.02] tracking-tight text-white drop-shadow-[0_0_30px_rgba(56,189,248,0.25)]">
              Il tuo trading,<br />ripensato.
            </h2>
            <p className="nx3d-lede">Apri il motore. Guarda cosa può fare per te.</p>
            <div className="nx3d-cta">
              <button className="nx3d-btn primary" onClick={() => navigate("/login")}>Apri il Backtest Lab</button>
              <button className="nx3d-btn" onClick={() => goTo(0)}>Torna alla partenza</button>
            </div>
            <p className="nx3d-disc">Risultati da backtest su dati storici: non sono garanzia di rendimenti futuri. Il trading a leva comporta rischio di perdita del capitale.</p>
          </GlassCard>
        </section>
      </main>
    </div>
  );
}
