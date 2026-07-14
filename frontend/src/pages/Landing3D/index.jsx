import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Canvas } from "@react-three/fiber";
import { Moon, Cog, GitBranch, MessageCircle, Scale } from "lucide-react";
import GlassCard from "./GlassCard";
import Scene from "./Scene";
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
 * NEXUS — landing cinematica. Nessun video: toro, orso, il loro scontro e
 * il re vivono come elementi 3D veri (ritagli con alpha reale, non uno
 * schermo che riproduce qualcosa) dentro uno spazio nero, con luci, ombre
 * sul pavimento e una camera che vola dentro la scena scrollando — libera
 * e profonda, non un punto fermo. Se il browser non supporta WebGL, resta
 * visibile un fermo immagine statico — non sparisce mai del tutto.
 */
export default function Landing3D() {
  const navigate = useNavigate();
  const rootRef = useRef(null);
  const sectionRefs = useRef([]);
  const progressRef = useRef(0);
  const [webglOk] = useState(supportsWebGL);

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
        <img
          className="nx3d-video-bg"
          src={`${process.env.PUBLIC_URL}/images/cutouts/king.webp`}
          alt=""
          aria-hidden="true"
        />
      )}
      <div className="nx3d-video-scrim" aria-hidden="true" />

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
        {STEPS.map((s, i) => {
          const Icon = STEP_ICONS[i];
          return (
            <section
              className="nx3d-panel step"
              key={s.badge}
              ref={(el) => { sectionRefs.current[i] = el; }}
            >
              <div className="nx3d-step-icon" aria-hidden="true"><Icon size={32} strokeWidth={1.6} /></div>
              <GlassCard badge={s.badge} title={s.title}>
                <p className="mt-3.5 text-[16px] font-medium text-white/85 leading-relaxed">{s.desc}</p>
              </GlassCard>
            </section>
          );
        })}

        <section className="nx3d-panel center" ref={(el) => { sectionRefs.current[N_SECTIONS - 1] = el; }}>
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
              <button className="nx3d-btn" onClick={() => goTo(0)}>Perché ti serve</button>
            </div>
            <p className="nx3d-disc">Risultati da backtest su dati storici: non sono garanzia di rendimenti futuri. Il trading a leva comporta rischio di perdita del capitale.</p>
          </GlassCard>
        </section>
      </main>
    </div>
  );
}
