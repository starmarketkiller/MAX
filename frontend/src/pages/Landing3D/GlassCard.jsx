import { motion } from "framer-motion";

/**
 * Componente UI in Glassmorphism: pannello scuro semitrasparente,
 * sfocatura forte dello sfondo, bordo sottile con bagliore ciano.
 * L'ingresso (fade + slight rise + blur-out) è affidato a Framer Motion.
 */
export default function GlassCard({ badge, title, children, center = false, wide = false, className = "" }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30, filter: "blur(6px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, amount: 0.5 }}
      transition={{ duration: 0.75, ease: [0.2, 0.8, 0.2, 1] }}
      className={[
        "relative rounded-2xl border border-cyan-400/40 bg-black/45 backdrop-blur-md",
        "shadow-[0_30px_70px_-30px_rgba(0,0,0,0.85)] px-8 py-9 sm:px-10 sm:py-10",
        "before:absolute before:inset-0 before:rounded-2xl before:pointer-events-none",
        "before:shadow-[inset_0_0_44px_rgba(56,230,255,0.08)]",
        wide ? "max-w-3xl" : "max-w-[440px]",
        center ? "mx-auto text-center" : "",
        className,
      ].join(" ")}
    >
      {badge && (
        <span className="inline-block mb-4 rounded-full border border-cyan-400/60 px-3.5 py-1.5 font-quantum font-bold text-[11px] tracking-[0.16em] uppercase text-cyan-300">
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
