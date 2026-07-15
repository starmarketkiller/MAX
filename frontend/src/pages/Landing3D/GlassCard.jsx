import { useRef, useState } from "react";
import { motion, useScroll, useTransform, useMotionValueEvent } from "framer-motion";
import ScrambleText from "./ScrambleText";

/**
 * Testo che galleggia direttamente sulla scena — niente riquadro scuro
 * dietro: il contrasto arriva da un'ombra portata forte su due livelli
 * (una vicina e netta, una larga e morbida), non da un pannello che
 * nasconde la scena.
 *
 * L'ingresso/uscita è agganciato allo scroll stesso (useScroll+
 * useTransform, non whileInView): la card entra ruotando largo su un
 * asse verticale (rotateY, fino a 70°) e scorrendo di lato (x) come se
 * arrivasse "dall'orbita" intorno alla N invece che da uno slide piatto
 * — alterna il lato (sinistra/destra) per sezione via `index`, come la
 * camera che gira intorno alla N alternando i lati (cameraPath.js). Si
 * assesta piatta al centro, poi rotea e scivola via dal lato opposto
 * mentre esce, sparendo prima di raggiungere l'angolo massimo. Il titolo
 * si "decodifica" (ScrambleText) non appena la sezione si blocca in
 * posizione, invece di un fade-in classico.
 */
export default function GlassCard({ badge, title, children, center = false, wide = false, className = "", index = 0 }) {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const [titleTrigger, setTitleTrigger] = useState(false);
  const dir = index % 2 === 0 ? 1 : -1;

  useMotionValueEvent(scrollYProgress, "change", (v) => {
    if (v > 0.32 && !titleTrigger) setTitleTrigger(true);
  });

  const opacity = useTransform(scrollYProgress, [0, 0.3, 0.7, 1], [0, 1, 1, 0]);
  const x = useTransform(scrollYProgress, [0, 0.32, 0.68, 1], [90 * dir, 0, 0, -76 * dir]);
  const y = useTransform(scrollYProgress, [0, 0.32, 0.68, 1], [56, 0, 0, -48]);
  const rotateX = useTransform(scrollYProgress, [0, 0.32, 0.68, 1], [12, 0, 0, -10]);
  const rotateY = useTransform(scrollYProgress, [0, 0.32, 0.68, 1], [68 * dir, 0, 0, -58 * dir]);
  const scale = useTransform(scrollYProgress, [0, 0.32, 0.68, 1], [0.82, 1, 1, 0.86]);

  return (
    <motion.div
      ref={ref}
      style={{
        opacity,
        x,
        y,
        rotateX,
        rotateY,
        scale,
        transformPerspective: 1100,
        willChange: "transform, opacity",
      }}
      className={[
        "relative px-6 py-6 sm:px-8 sm:py-8",
        "[filter:drop-shadow(0_2px_10px_rgba(0,0,0,0.92))_drop-shadow(0_18px_46px_rgba(0,0,0,0.75))]",
        wide ? "max-w-3xl" : "max-w-[440px]",
        center ? "mx-auto text-center" : "",
        className,
      ].join(" ")}
    >
      <div className="nx3d-skew-target">
        {badge && (
          <span className="inline-block mb-4 rounded-full border border-cyan-400/60 bg-black/50 backdrop-blur-sm px-3.5 py-1.5 font-quantum font-bold text-[11px] tracking-[0.16em] uppercase text-cyan-300">
            {badge}
          </span>
        )}
        {title && (
          <h2 className="m-0 font-grotesk font-bold leading-[1.12] tracking-tight text-white text-[clamp(25px,2.6vw,34px)]">
            <ScrambleText text={title} trigger={titleTrigger} />
          </h2>
        )}
        {children}
      </div>
    </motion.div>
  );
}
