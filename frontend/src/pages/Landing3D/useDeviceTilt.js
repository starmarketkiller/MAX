import { useEffect, useRef } from "react";

/**
 * Un ref condiviso {x,y} in -1..1: sul desktop segue il mouse (R3F lo dà
 * già gratis via `pointer` in useThree), qui aggiungiamo il giroscopio
 * per il telefono — se il dispositivo si inclina, lo spazio 3D risponde
 * come se stessimo guardando dentro l'arena da un oblò. iOS richiede un
 * permesso esplicito (richiesto al primo tocco/scroll, non invasivo: se
 * l'utente lo nega semplicemente il parallasse resta solo sul mouse).
 */
export default function useDeviceTilt() {
  const tilt = useRef({ x: 0, y: 0 });

  useEffect(() => {
    let active = true;
    const onOrient = (e) => {
      if (!active || e.gamma === null || e.beta === null) return;
      // gamma: inclinazione sinistra/destra (-90..90), beta: avanti/indietro (-180..180)
      tilt.current.x = Math.max(-1, Math.min(1, e.gamma / 28));
      tilt.current.y = Math.max(-1, Math.min(1, (e.beta - 45) / 28));
    };

    const attach = () => window.addEventListener("deviceorientation", onOrient);

    const needsPermission =
      typeof window.DeviceOrientationEvent !== "undefined" &&
      typeof window.DeviceOrientationEvent.requestPermission === "function";

    if (needsPermission) {
      const grant = () => {
        window.DeviceOrientationEvent.requestPermission().then((state) => {
          if (state === "granted") attach();
        }).catch(() => {});
        window.removeEventListener("touchend", grant);
        window.removeEventListener("scroll", grant);
      };
      window.addEventListener("touchend", grant, { once: true });
      window.addEventListener("scroll", grant, { once: true, passive: true });
      return () => {
        active = false;
        window.removeEventListener("touchend", grant);
        window.removeEventListener("scroll", grant);
        window.removeEventListener("deviceorientation", onOrient);
      };
    }

    attach();
    return () => {
      active = false;
      window.removeEventListener("deviceorientation", onOrient);
    };
  }, []);

  return tilt;
}
