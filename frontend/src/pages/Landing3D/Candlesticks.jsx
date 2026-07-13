import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

const UP = new THREE.Color("#2ee88f");
const DOWN = new THREE.Color("#fb7185");
// Il corridoio copre sempre la stessa lunghezza di percorso: con meno
// candele (livelli di qualità più bassi) sono più diradate, non più corte.
const TOTAL_SPAN = 243;

/**
 * Corridoio di candele giapponesi con volume reale: corpo con spessore
 * (BoxGeometry, non un piano), altezza marcata dalla vera escursione
 * open/close, e uno stoppino (wick) che arriva fino a high/low — non più
 * segmenti piatti. Affianca il nastro olografico (che resta la guida
 * dell'equity), come il vero prezzo intorno alla curva aggregata.
 */
export default function Candlesticks({ count = 90 }) {
  const bodyRef = useRef();
  const wickRef = useRef();
  const NC = count;
  const zStep = TOTAL_SPAN / NC;

  const { bodyMatrices, wickMatrices, colors } = useMemo(() => {
    let price = 6;
    let seed = 42;
    const rnd = () => {
      seed = (seed * 9301 + 49297) % 233280;
      return seed / 233280;
    };
    const bodies = [];
    const wicks = [];
    const cols = [];
    const dummy = new THREE.Object3D();

    for (let i = 0; i < NC; i++) {
      const z = 3 - i * zStep;
      const open = price;
      // discesa marcata a metà corridoio, recupero verso il finale — più
      // drammatico di un semplice rumore simmetrico, si vede da lontano.
      const phase = i / NC;
      const drift = Math.sin(phase * Math.PI) > 0.55 ? -0.55 : 0.28;
      const dv = (rnd() - 0.42 + drift * 0.5) * 2.6;
      price += dv;
      const close = price;
      const up = close >= open;
      const bodyH = Math.max(0.5, Math.abs(close - open));
      const wickTop = Math.max(open, close) + rnd() * 0.9 + 0.25;
      const wickBot = Math.min(open, close) - rnd() * 0.9 - 0.25;
      const mid = (open + close) / 2;
      const x = Math.sin(i * 0.16) * 3.2;
      const y = mid * 0.6;

      dummy.position.set(x, y, z);
      dummy.scale.set(1, bodyH, 1);
      dummy.rotation.set(0, 0, 0);
      dummy.updateMatrix();
      bodies.push(dummy.matrix.clone());

      dummy.position.set(x, ((wickTop + wickBot) / 2) * 0.6, z);
      dummy.scale.set(0.14, (wickTop - wickBot) * 0.6, 0.14);
      dummy.updateMatrix();
      wicks.push(dummy.matrix.clone());

      cols.push(up ? UP : DOWN);
    }
    return { bodyMatrices: bodies, wickMatrices: wicks, colors: cols };
  }, [NC, zStep]);

  useEffect(() => {
    if (bodyRef.current) {
      bodyMatrices.forEach((m, i) => bodyRef.current.setMatrixAt(i, m));
      colors.forEach((c, i) => bodyRef.current.setColorAt(i, c));
      bodyRef.current.instanceMatrix.needsUpdate = true;
      if (bodyRef.current.instanceColor) bodyRef.current.instanceColor.needsUpdate = true;
    }
    if (wickRef.current) {
      wickMatrices.forEach((m, i) => wickRef.current.setMatrixAt(i, m));
      colors.forEach((c, i) => wickRef.current.setColorAt(i, c));
      wickRef.current.instanceMatrix.needsUpdate = true;
      if (wickRef.current.instanceColor) wickRef.current.instanceColor.needsUpdate = true;
    }
  }, [bodyMatrices, wickMatrices, colors]);

  return (
    <>
      <instancedMesh ref={bodyRef} args={[null, null, NC]}>
        <boxGeometry args={[0.62, 1, 0.62]} />
        <meshStandardMaterial metalness={0.35} roughness={0.4} emissiveIntensity={0.35} toneMapped={false} />
      </instancedMesh>
      <instancedMesh ref={wickRef} args={[null, null, NC]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshBasicMaterial transparent opacity={0.7} />
      </instancedMesh>
    </>
  );
}
