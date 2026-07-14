const CHIPS = [
  { top: "18%", left: "9%", w: 108, delay: "0s", label: "SCAN::BULL", kind: "reticle" },
  { top: "64%", left: "6%", w: 92, delay: "-4.5s", label: "Δ +0.42%", kind: "spark" },
  { top: "24%", right: "8%", w: 108, delay: "-1.8s", label: "SCAN::BEAR", kind: "reticle" },
  { top: "58%", right: "7%", w: 96, delay: "-7.2s", label: "VOL 0.88σ", kind: "spark" },
  { top: "83%", left: "42%", w: 118, delay: "-3s", label: "SYNC :: OK", kind: "code" },
];

function Sparkline() {
  return (
    <svg viewBox="0 0 60 20" width="46" height="16" aria-hidden="true">
      <polyline
        points="0,14 8,10 16,15 24,6 32,11 40,4 48,9 56,3"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
      />
    </svg>
  );
}

function Reticle() {
  return (
    <svg viewBox="0 0 32 32" width="22" height="22" aria-hidden="true">
      <circle cx="16" cy="16" r="10" fill="none" stroke="currentColor" strokeWidth="1" />
      <line x1="16" y1="0" x2="16" y2="8" stroke="currentColor" strokeWidth="1" />
      <line x1="16" y1="24" x2="16" y2="32" stroke="currentColor" strokeWidth="1" />
      <line x1="0" y1="16" x2="8" y2="16" stroke="currentColor" strokeWidth="1" />
      <line x1="24" y1="16" x2="32" y2="16" stroke="currentColor" strokeWidth="1" />
    </svg>
  );
}

/**
 * Livello di vetro in primissimo piano — più vicino di tutto il resto in
 * scena, l'AI che "scansiona" il mercato: mirini sopra toro/orso, micro
 * sparkline, etichette di stato, alla deriva lentissima e indipendente
 * dallo scroll. L'aberrazione cromatica (text-shadow rosso/verde sfalsato)
 * e il bordo si intensificano con --nx3d-vel (impostata in index.jsx dalla
 * velocità di scroll) — più veloce scorri, più l'AI sembra "agganciarsi"
 * nervosamente ai dati. Nascosto su schermi stretti per non affollare un
 * layout mobile già compresso.
 */
export default function HUDForeground() {
  return (
    <div className="nx3d-hudfg" aria-hidden="true">
      {CHIPS.map((c, i) => (
        <div
          key={i}
          className={`nx3d-hudfg-chip ${c.kind}`}
          style={{
            top: c.top,
            left: c.left,
            right: c.right,
            width: c.w,
            animationDelay: c.delay,
          }}
        >
          <span className="nx3d-hudfg-icon">
            {c.kind === "reticle" ? <Reticle /> : c.kind === "spark" ? <Sparkline /> : null}
          </span>
          <span className="nx3d-hudfg-label">{c.label}</span>
        </div>
      ))}
    </div>
  );
}
