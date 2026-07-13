import { useEffect, useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

const VS = "varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,0.0,1.0);}";
const BRIGHT_FS =
  "precision highp float;varying vec2 vUv;uniform sampler2D tD;uniform float thr;" +
  "void main(){vec3 c=texture2D(tD,vUv).rgb;float l=dot(c,vec3(0.299,0.587,0.114));" +
  "float k=smoothstep(thr,thr+0.35,l);gl_FragColor=vec4(c*k,1.0);}";
const BLUR_FS =
  "precision highp float;varying vec2 vUv;uniform sampler2D tD;uniform vec2 dir;uniform vec2 texel;" +
  "void main(){vec2 o=dir*texel;vec3 s=texture2D(tD,vUv).rgb*0.227;" +
  "s+=texture2D(tD,vUv+o*1.384).rgb*0.316;s+=texture2D(tD,vUv-o*1.384).rgb*0.316;" +
  "s+=texture2D(tD,vUv+o*3.230).rgb*0.070;s+=texture2D(tD,vUv-o*3.230).rgb*0.070;gl_FragColor=vec4(s,1.0);}";
const COMP_FS =
  "precision highp float;varying vec2 vUv;uniform sampler2D tScene;uniform sampler2D tBloom;uniform float inten;uniform float uT;" +
  "void main(){vec3 c=texture2D(tScene,vUv).rgb;vec3 b=texture2D(tBloom,vUv).rgb;vec3 col=c+b*inten;col=col/(col+vec3(0.6))*1.6;" +
  "vec2 uv=vUv-0.5;float vig=1.0-dot(uv,uv)*0.55;col*=vig;" +
  "float sl=sin((vUv.y*820.0)-uT*2.0)*0.015;col+=sl;gl_FragColor=vec4(col,1.0);}";

/**
 * Bloom multi-pass (bright-pass + blur gaussiano separabile H/V + composite
 * con vignette/scanline) implementato in R3F puro — nessuna dipendenza
 * aggiuntiva. Registrare un useFrame con priorità disattiva il render
 * automatico di R3F: qui prendiamo il controllo del render loop.
 *
 * `bloom=false` (dispositivi di fascia bassa) salta l'intera pipeline di
 * post-processing — è il costo GPU più alto della scena — e fa un render
 * diretto. `bloomScale` riduce la risoluzione dei passaggi di blur, che
 * restano comunque morbidi perché già sfocati.
 */
export default function Effects({ bloom = true, bloomScale = 0.5 }) {
  const { gl, scene, camera, size } = useThree();
  const dpr = useMemo(() => Math.min(window.devicePixelRatio, 2), []);

  const ortho = useMemo(() => new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1), []);
  const postScene = useMemo(() => new THREE.Scene(), []);
  const quad = useMemo(() => new THREE.Mesh(new THREE.PlaneGeometry(2, 2)), []);
  useEffect(() => {
    postScene.add(quad);
    return () => postScene.remove(quad);
  }, [postScene, quad]);

  const brightMat = useMemo(
    () => new THREE.ShaderMaterial({ uniforms: { tD: { value: null }, thr: { value: 0.55 } }, vertexShader: VS, fragmentShader: BRIGHT_FS }),
    []
  );
  const blurH = useMemo(
    () => new THREE.ShaderMaterial({ uniforms: { tD: { value: null }, dir: { value: new THREE.Vector2(1, 0) }, texel: { value: new THREE.Vector2() } }, vertexShader: VS, fragmentShader: BLUR_FS }),
    []
  );
  const blurV = useMemo(
    () => new THREE.ShaderMaterial({ uniforms: { tD: { value: null }, dir: { value: new THREE.Vector2(0, 1) }, texel: { value: new THREE.Vector2() } }, vertexShader: VS, fragmentShader: BLUR_FS }),
    []
  );
  const compMat = useMemo(
    () => new THREE.ShaderMaterial({ uniforms: { tScene: { value: null }, tBloom: { value: null }, inten: { value: 1.25 }, uT: { value: 0 } }, vertexShader: VS, fragmentShader: COMP_FS }),
    []
  );

  const rts = useRef({ scene: null, a: null, b: null });
  const makeRT = (w, h) => new THREE.WebGLRenderTarget(Math.max(1, w | 0), Math.max(1, h | 0), { minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter });

  useEffect(() => {
    if (!bloom) return;
    const w = size.width * dpr;
    const h = size.height * dpr;
    const prev = rts.current;
    if (prev.scene) prev.scene.dispose();
    if (prev.a) prev.a.dispose();
    if (prev.b) prev.b.dispose();
    rts.current = { scene: makeRT(w, h), a: makeRT(w * bloomScale, h * bloomScale), b: makeRT(w * bloomScale, h * bloomScale) };
  }, [size, dpr, bloom, bloomScale]);

  useEffect(() => {
    return () => {
      const prev = rts.current;
      if (prev.scene) prev.scene.dispose();
      if (prev.a) prev.a.dispose();
      if (prev.b) prev.b.dispose();
      [brightMat, blurH, blurV, compMat].forEach((m) => m.dispose());
      quad.geometry.dispose();
    };
  }, [brightMat, blurH, blurV, compMat, quad]);

  const pass = (mat, target) => {
    quad.material = mat;
    gl.setRenderTarget(target);
    gl.render(postScene, ortho);
  };

  useFrame((state) => {
    if (!bloom) {
      gl.setRenderTarget(null);
      gl.render(scene, camera);
      return;
    }
    const { scene: rtScene, a: rtA, b: rtB } = rts.current;
    if (!rtScene) return;
    gl.setRenderTarget(rtScene);
    gl.render(scene, camera);

    brightMat.uniforms.tD.value = rtScene.texture;
    pass(brightMat, rtA);

    const tx = 1 / (size.width * dpr * bloomScale);
    const ty = 1 / (size.height * dpr * bloomScale);
    blurH.uniforms.tD.value = rtA.texture;
    blurH.uniforms.texel.value.set(tx, ty);
    pass(blurH, rtB);
    blurV.uniforms.tD.value = rtB.texture;
    blurV.uniforms.texel.value.set(tx, ty);
    pass(blurV, rtA);

    compMat.uniforms.tScene.value = rtScene.texture;
    compMat.uniforms.tBloom.value = rtA.texture;
    compMat.uniforms.uT.value = state.clock.elapsedTime;
    gl.setRenderTarget(null);
    quad.material = compMat;
    gl.render(postScene, ortho);
  }, 1);

  return null;
}
