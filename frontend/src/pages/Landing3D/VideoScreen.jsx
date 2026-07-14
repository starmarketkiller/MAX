import { useEffect, useMemo, useRef, useState } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Edges } from "@react-three/drei";
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
 *
 * Lo schermo è un box (non un piano): ha uno spessore vero, visibile di
 * taglio quando ruota — è questo, insieme al pavimento riflettente e al
 * girare della camera, che fa leggere la scena come uno spazio 3D reale
 * invece che un video con un bordo. Ruota anche lui, indipendentemente
 * dalla camera, seguendo lo scroll: si "gira" nello spazio mentre si legge.
 */
export default function VideoScreen({ progressRef, position = [0, 1.9, 0] }) {
  const { gl } = useThree();
  const [ready, setReady] = useState(false);
  const videoRef = useRef(null);
  const smoothT = useRef(0);
  const groupRef = useRef();

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

  const videoMaterial = useMemo(() => new THREE.MeshBasicMaterial({ map: texture, toneMapped: false }), [texture]);
  const frameMaterial = useMemo(
    () => new THREE.MeshStandardMaterial({ color: "#0d2140", emissive: "#38bdf8", emissiveIntensity: 0.75, metalness: 0.75, roughness: 0.3 }),
    []
  );
  const boxMaterials = useMemo(
    () => [frameMaterial, frameMaterial, frameMaterial, frameMaterial, videoMaterial, frameMaterial],
    [frameMaterial, videoMaterial]
  );

  useEffect(() => {
    videoRef.current = video;
    const onReady = () => setReady(true);
    video.addEventListener("loadedmetadata", onReady);
    video.load();
    return () => {
      video.removeEventListener("loadedmetadata", onReady);
      texture.dispose();
      videoMaterial.dispose();
      frameMaterial.dispose();
    };
  }, [video, texture, videoMaterial, frameMaterial]);

  useFrame((state, delta) => {
    if (ready && video.duration && !Number.isNaN(video.duration)) {
      const target = Math.min(Math.max(progressRef.current, 0), 1) * video.duration;
      const k = 1 - Math.exp(-delta * 6);
      smoothT.current += (target - smoothT.current) * k;
      // seek solo se lo scarto e' apprezzabile: evita di martellare currentTime
      // ad ogni frame (costoso e inutile sotto la soglia percepibile).
      if (Math.abs(video.currentTime - smoothT.current) > 0.02) {
        video.currentTime = smoothT.current;
      }
    }
    const t = state.clock.elapsedTime;
    frameMaterial.emissiveIntensity = 0.75 + Math.sin(t * 1.4) * 0.15;
    if (groupRef.current) {
      const p = Math.min(Math.max(progressRef.current, 0), 1);
      // rotazione propria dello schermo, indipendente dalla camera: si "gira"
      // nello spazio seguendo lo scroll, rivelando lo spessore del box.
      groupRef.current.rotation.y = -0.32 + p * 0.62 + Math.sin(t * 0.15) * 0.025;
      groupRef.current.rotation.x = -0.08 + Math.sin(t * 0.12) * 0.015;
      groupRef.current.position.y = position[1] + Math.sin(t * 0.25) * 0.06;
    }
  });

  return (
    <group ref={groupRef} position={position}>
      <mesh castShadow material={boxMaterials}>
        <boxGeometry args={[6.4, 6.4, 1.1]} />
        {/* linee di contorno che convergono in prospettiva — l'indizio di
            profondità più diretto: senza, lo spessore del box si perde
            quasi a video fermo o quasi frontale. */}
        <Edges scale={1.001} color="#7dd3fc" />
      </mesh>
      <pointLight color="#38bdf8" intensity={20} distance={16} position={[0, 0, 3]} />
    </group>
  );
}
