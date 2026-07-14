import { useEffect, useMemo, useRef, useState } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

const FRAME_COUNT = 191;
const FRAME_URL = (i) => `${process.env.PUBLIC_URL}/video/frames/f${String(i).padStart(4, "0")}.jpg`;

/**
 * L'arena come sfondo a schermo intero — non un video che "parte", una
 * sequenza di 191 fotogrammi (quasi il doppio dei 97 originali, interpolati
 * con ffmpeg per rendere impercettibile il passaggio da uno all'altro)
 * disegnati su un canvas e scelti in base allo scroll. Zero player, zero
 * seek su un mp4 compresso (che su H.264 può scattare quando si cerca
 * avanti/indietro spesso) — solo un indice di array, sempre istantaneo.
 *
 * Il canvas è una texture su un piano agganciato alla camera stessa
 * (figlio della camera, non della scena): resta sempre esattamente
 * quanto il frustum, a qualunque distanza si trovi la camera — "schermo
 * intero" per davvero, non un riquadro fluttuante con bordi visibili.
 *
 * La profondità vera arriva da altrove: il pavimento riflettente e il
 * pulviscolo (Atmosphere) stanno nel mondo 3D davanti a questo sfondo e
 * si muovono con parallasse reale mentre la camera avanza; qui in più
 * simuliamo l'ingresso nell'arena con uno zoom progressivo sul fotogramma
 * (scala + pan verso il centro) sincronizzato allo stesso scroll.
 */
export default function ArenaBackdrop({ progressRef }) {
  const { camera, size } = useThree();
  const meshRef = useRef();
  const canvasRef = useRef();
  const ctxRef = useRef();
  const textureRef = useRef();
  const imagesRef = useRef([]);
  const [loadedCount, setLoadedCount] = useState(0);
  const smoothIdx = useRef(0);
  const lastDrawn = useRef(-1);
  const lastZoom = useRef(-1);

  useEffect(() => {
    const c = document.createElement("canvas");
    c.width = 1280;
    c.height = 1280;
    canvasRef.current = c;
    ctxRef.current = c.getContext("2d");
    const tex = new THREE.CanvasTexture(c);
    if ("colorSpace" in tex) tex.colorSpace = THREE.SRGBColorSpace;
    tex.minFilter = THREE.LinearFilter;
    tex.magFilter = THREE.LinearFilter;
    textureRef.current = tex;
    if (meshRef.current) meshRef.current.material.map = tex;

    let cancelled = false;
    const imgs = new Array(FRAME_COUNT);
    imagesRef.current = imgs;
    let loaded = 0;
    // carica prima i fotogrammi chiave (ogni 6°) per avere subito qualcosa
    // di utilizzabile su tutto il range, poi riempie il resto in background.
    const order = [];
    for (let i = 0; i < FRAME_COUNT; i += 6) order.push(i);
    for (let i = 0; i < FRAME_COUNT; i++) if (i % 6 !== 0) order.push(i);
    order.forEach((i) => {
      const img = new Image();
      img.onload = () => {
        if (cancelled) return;
        loaded++;
        setLoadedCount(loaded);
      };
      img.src = FRAME_URL(i);
      imgs[i] = img;
    });

    return () => {
      cancelled = true;
      tex.dispose();
    };
  }, []);

  const geo = useMemo(() => new THREE.PlaneGeometry(1, 1), []);
  const mat = useMemo(() => new THREE.MeshBasicMaterial({ toneMapped: false }), []);

  // trova il fotogramma caricato più vicino a quello desiderato — così il
  // primo scroll è già reattivo anche prima che tutti i 191 siano arrivati.
  const nearestLoaded = (idx) => {
    const imgs = imagesRef.current;
    if (imgs[idx] && imgs[idx].complete && imgs[idx].naturalWidth) return idx;
    for (let d = 1; d < FRAME_COUNT; d++) {
      const a = idx - d, b = idx + d;
      if (a >= 0 && imgs[a] && imgs[a].complete && imgs[a].naturalWidth) return a;
      if (b < FRAME_COUNT && imgs[b] && imgs[b].complete && imgs[b].naturalWidth) return b;
    }
    return -1;
  };

  useFrame((state, delta) => {
    const p = Math.min(Math.max(progressRef.current, 0), 1);
    const targetIdx = p * (FRAME_COUNT - 1);
    const k = 1 - Math.exp(-delta * 10);
    smoothIdx.current += (targetIdx - smoothIdx.current) * k;
    const idx = Math.round(smoothIdx.current);
    const zoom = 1 + p * 0.22; // avvicinamento progressivo dentro il fotogramma

    if (loadedCount > 0 && (idx !== lastDrawn.current || Math.abs(zoom - lastZoom.current) > 0.003)) {
      const real = nearestLoaded(idx);
      if (real >= 0) {
        const img = imagesRef.current[real];
        const ctx = ctxRef.current;
        const c = canvasRef.current;
        ctx.filter = "saturate(1.12) contrast(1.04)";
        ctx.fillStyle = "#050a16";
        ctx.fillRect(0, 0, c.width, c.height);
        const w = c.width * zoom;
        const h = c.height * zoom;
        const x = (c.width - w) / 2;
        const y = (c.height - h) / 2 - p * c.height * 0.02;
        ctx.drawImage(img, x, y, w, h);
        textureRef.current.needsUpdate = true;
        lastDrawn.current = idx;
        lastZoom.current = zoom;
      }
    }

    // il quad resta figlio della camera e riempie sempre il frustum, a
    // qualunque distanza lo si metta — "schermo intero" garantito.
    if (meshRef.current) {
      const dist = 20;
      const vFov = (camera.fov * Math.PI) / 180;
      const h = 2 * Math.tan(vFov / 2) * dist;
      const w = h * (size.width / size.height);
      meshRef.current.scale.set(w * 1.02, h * 1.02, 1);
      meshRef.current.position.set(0, 0, -dist);
    }
  });

  return (
    <primitive object={camera}>
      <mesh ref={meshRef} geometry={geo} material={mat} renderOrder={-10} />
    </primitive>
  );
}
