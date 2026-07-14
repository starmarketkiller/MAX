import { motion } from "framer-motion";

/**
 * Testo che galleggia direttamente sulla scena — niente più riquadro
 * scuro dietro: per restare leggibile sopra un'immagine impegnativa il
 * contrasto arriva da un'ombra portata forte su ogni elemento (due
 * livelli: una vicina e netta, una larga e morbida), non da un pannello
 * che nasconde la scena. L'ingresso (fade + slight rise + blur-out) è
 * affidato a Framer Motion.
 */
export default function GlassCard({ badge, title, children, center = false, wide = false, className = "" }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30, filter: "blur(6px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, amount: 0.5 }}
      transition={{ duration: 0.75, ease: [0.2, 0.8, 0.2, 1] }}
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
