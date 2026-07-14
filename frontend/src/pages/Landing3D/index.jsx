import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Canvas } from "@react-three/fiber";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Moon, Cog, GitBranch, MessageCircle, Scale } from "lucide-react";
import Scene from "./Scene";
import GlassCard from "./GlassCard";
import ArenaScrub from "./ArenaScrub";
import { STEPS, N_SECTIONS } from "./content";
import { detectQuality, QUALITY_PRESETS } from "./quality";
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
 * NEXUS — landing 3D cinematica. Due motori di rendering distinti in
 * sequenza sulla stessa pagina: l'arena (canvas 2D, 97 frame scrubbati con
 * lo scroll) come apertura, poi il viaggio R3F (Three.js via React Three
 * Fiber + GSAP ScrollTrigger) per le tappe successive. La UI HTML (overlay
 * assoluto) comunica con entrambi solo via ref, letti ad ogni frame senza
 * mai forzare un re-render React.
 */
export default function Landing3D() {
  const navigate = useNavigate();
  const rootRef = useRef(null);
  const journeyRef = useRef(null);
  const sectionRefs = useRef([]);
  const progressRef = useRef(0);
  const arenaProgressRef = useRef(0);
  const mouseRef = useRef({ x: 0, y: 0 });
  const [webglOk] = useState(supportsWebGL);
  const [quality] = useState(detectQuality);
  const [arenaReady, setArenaReady] = useState(false);

  const goTo = (i) => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (i === 0) {
      window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
      return;
    }
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

  // Camera del viaggio R3F <-> scroll: un solo ScrollTrigger scrub-linked,
  // agganciato al wrapper del "journey" (dopo l'arena) cosi' il progresso
  // 0..1 copre solo le tappe R3F. Creato SOLO dopo che ArenaScrub segnala
  // (via onReady) che il proprio pin esiste gia' nel DOM — altrimenti questo
  // trigger misurerebbe "top top"/"bottom bottom" contro un documento ancora
  // corto (l'arena non ancora pinnata) e resterebbe con confini sbagliati
  // per tutta la sessione: il progresso del viaggio "correrebbe" troppo in
  // fretta rispetto allo scroll reale. Non basta un refresh() successivo per
  // rimediare — la sequenza giusta e' non crearlo troppo presto.
  useEffect(() => {
    if (!arenaReady || !journeyRef.current) return;
    const st = ScrollTrigger.create({
      trigger: journeyRef.current,
      start: "top top",
      end: "bottom bottom",
      scrub: true,
      onUpdate: (self) => {
        progressRef.current = self.progress;
      },
    });
    // i webfont possono ancora arrivare dopo e cambiare di poco le altezze
    // del testo (non i ~4000px dell'arena, quello e' gia' risolto sopra) —
    // un refresh qui corregge quel margine residuo, il trigger esiste gia'.
    document.fonts?.ready?.then(() => ScrollTrigger.refresh());
    return () => st.kill();
  }, [arenaReady]);

  // UI chrome indipendente dallo scroll-trigger del viaggio: mouse parallax,
  // rail dei puntini, etichetta sezione — attiva da subito, non aspetta l'arena.
  useEffect(() => {
    const onMouse = (e) => {
      mouseRef.current.x = e.clientX / window.innerWidth - 0.5;
      mouseRef.current.y = e.clientY / window.innerHeight - 0.5;
    };
    window.addEventListener("mousemove", onMouse, { passive: true });

    const railBtns = [...rootRef.current.querySelectorAll(".nx3d-rail button")];
    const sectionLabel = rootRef.current.querySelector("#nx3d-hud-section");
    let raf = 0;
    const uiTick = () => {
      const arenaDone = arenaProgressRef.current > 0.999;
      const journeyP = Math.min(Math.max(progressRef.current, 0), 1);
      const active = arenaDone ? 1 + Math.round(journeyP * (N_SECTIONS - 2)) : 0;
      railBtns.forEach((b, i) => b.classList.toggle("on", i === active));
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
    };
  }, []);

  return (
    <div className="nx3d" ref={rootRef}>
      {webglOk ? (
        <div className="nx3d-gl-wrap">
          <Canvas
            camera={{ fov: 62, near: 0.1, far: 600, position: [4, 4, -14] }}
            gl={{ antialias: quality === "high", powerPreference: "high-performance" }}
            dpr={QUALITY_PRESETS[quality].dpr}
          >
            <Scene progressRef={progressRef} mouseRef={mouseRef} quality={quality} />
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

      <main className="nx3d-scroll">
        <ArenaScrub
          progressRef={arenaProgressRef}
          arenaDpr={QUALITY_PRESETS[quality].arenaDpr}
          onReady={() => setArenaReady(true)}
        >
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
        </ArenaScrub>

        <div ref={journeyRef}>
          {STEPS.map((s, i) => {
            const Icon = STEP_ICONS[i];
            return (
              <section
                className="nx3d-panel step"
                key={s.badge}
                ref={(el) => { sectionRefs.current[i + 1] = el; }}
              >
                <div className="nx3d-step-icon" aria-hidden="true"><Icon size={32} strokeWidth={1.6} /></div>
                <GlassCard badge={s.badge} title={s.title}>
                  <p className="mt-3.5 text-[16px] font-medium text-white/85 leading-relaxed">{s.desc}</p>
                </GlassCard>
              </section>
            );
          })}

          <section className="nx3d-panel center" ref={(el) => { sectionRefs.current[N_SECTIONS - 1] = el; }}>
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
        </div>
      </main>
    </div>
  );
}
