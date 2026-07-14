import { useEffect, useMemo, useRef, useState } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

/**
 * Il video dell'arena come texture su uno schermo 3D vero — non un
 * <video> piatto in overlay. Inclinato, con una cornice che si illumina
 * (bordo emissivo) e un'ombra proiettata sul pavimento sotto: la stessa
 * ripresa cinematografica, ma vissuta come oggetto nello spazio, non come
 * sfondo incollato.
 *
 * VideoTexture creata a mano (non con drei/useVideoTexture): quell'hook
 * importa hls.js in modo statico anche se non serve mai per un mp4 locale
 * — +370KB gzip di codice morto nel bundle. Poche righe qui evitano il peso.
 *
 * `progressRef` è la posizione di scroll (0..1 sull'intera pagina): pilota
 * direttamente il punto del video mostrato — avanti scrollando giù,
 * indietro scrollando su ("playback" bidirezionale) — con un lerp per
 * restare morbido anche se lo scroll è a scatti.
 */
export default function VideoScreen({ progressRef, position = [0, 1.5, 0], rotation = [-0.06, 0.18, 0] }) {
  const { gl } = useThree();
  const [ready, setReady] = useState(false);
  const videoRef = useRef(null);
  const smoothT = useRef(0);
  const frameRef = useRef();

  const video = useMemo(() => {
    const v = document.createElement("video");
    v.muted = true;
    v.loop = false;
    v.playsInline = true;
    v.preload = "auto";
    const source = document.createElement("source");
    source.src = `${process.env.PUBLIC_URL}/video/arena.mp4`;
    source.type = "video/mp4";
    v.appendChild(source);
    const sourceWebm = document.createElement("source");
    sourceWebm.src = `${process.env.PUBLIC_URL}/video/arena.webm`;
    sourceWebm.type = "video/webm";
    v.appendChild(sourceWebm);
    return v;
  }, []);

  const texture = useMemo(() => {
    const t = new THREE.VideoTexture(video);
    if ("colorSpace" in t) t.colorSpace = gl.outputColorSpace;
    else t.encoding = gl.outputEncoding;
    return t;
  }, [video, gl]);

  useEffect(() => {
    videoRef.current = video;
    const onReady = () => setReady(true);
    video.addEventListener("loadedmetadata", onReady);
    video.load();
    return () => {
      video.removeEventListener("loadedmetadata", onReady);
      texture.dispose();
    };
  }, [video, texture]);

  useFrame((state, delta) => {
    if (!ready || !video.duration || Number.isNaN(video.duration)) return;
    const target = Math.min(Math.max(progressRef.current, 0), 1) * video.duration;
    const k = 1 - Math.exp(-delta * 6);
    smoothT.current += (target - smoothT.current) * k;
    // seek solo se lo scarto e' apprezzabile: evita di martellare currentTime
    // ad ogni frame (costoso e inutile sotto la soglia percepibile).
    if (Math.abs(video.currentTime - smoothT.current) > 0.02) {
      video.currentTime = smoothT.current;
    }
    const t = state.clock.elapsedTime;
    if (frameRef.current) frameRef.current.material.emissiveIntensity = 0.55 + Math.sin(t * 1.4) * 0.12;
  });

  return (
    <group position={position} rotation={rotation}>
      <mesh castShadow>
        <planeGeometry args={[9, 9]} />
        <meshBasicMaterial map={texture} toneMapped={false} />
      </mesh>
      {/* cornice sottile che si illumina piano — il bordo dello "schermo" */}
      <mesh ref={frameRef} position={[0, 0, -0.02]}>
        <planeGeometry args={[9.3, 9.3]} />
        <meshStandardMaterial color="#0a1830" emissive="#38bdf8" emissiveIntensity={0.55} />
      </mesh>
      <pointLight color="#38bdf8" intensity={18} distance={14} position={[0, 0, 2.5]} />
    </group>
  );
}
