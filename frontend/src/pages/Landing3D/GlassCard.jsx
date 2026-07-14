import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";

/**
 * Testo che galleggia direttamente sulla scena — niente riquadro scuro
 * dietro: il contrasto arriva da un'ombra portata forte su due livelli
 * (una vicina e netta, una larga e morbida), non da un pannello che
 * nasconde la scena.
 *
 * L'ingresso/uscita è agganciato allo scroll stesso (useScroll+
 * useTransform, non whileInView): mentre la sezione sale nel viewport il
 * blocco ruota leggermente in avanti (rotateX) e scivola su, si assesta
 * piatto al centro, poi ruota all'indietro e scivola via mentre esce in
 * alto — un vero movimento di "slide" 3D legato al gesto di scroll, non
 * un fade-in innescato una volta sola.
 */
export default function GlassCard({ badge, title, children, center = false, wide = false, className = "" }) {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });

  const opacity = useTransform(scrollYProgress, [0, 0.22, 0.8, 1], [0, 1, 1, 0]);
  const y = useTransform(scrollYProgress, [0, 0.22, 0.8, 1], [64, 0, 0, -56]);
  const rotateX = useTransform(scrollYProgress, [0, 0.22, 0.8, 1], [16, 0, 0, -12]);
  const scale = useTransform(scrollYProgress, [0, 0.22, 0.8, 1], [0.94, 1, 1, 0.96]);

  return (
    <motion.div
      ref={ref}
      style={{
        opacity,
        y,
        rotateX,
        scale,
        transformPerspective: 900,
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
      {badge && (
        <span className="inline-block mb-4 rounded-full border border-cyan-400/60 bg-black/50 backdrop-blur-sm px-3.5 py-1.5 font-quantum font-bold text-[11px] tracking-[0.16em] uppercase text-cyan-300">
          {badge}
        </span>
      )}
      {title && (
        <h2 className="m-0 font-grotesk font-bold leading-[1.12] tracking-tight text-white text-[clamp(25px,2.6vw,34px)]">
          {title}
        </h2>
      )}
      {children}
    </motion.div>
  );
}
