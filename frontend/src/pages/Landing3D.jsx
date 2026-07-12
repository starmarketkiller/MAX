import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import * as THREE from "three";
import "./Landing3D.css";

/**
 * NEXUS — immersive 3D landing.
 * Real WebGL (Three.js): perspective camera flown by scroll through a corridor of
 * candlesticks along a glowing equity tube, in a galaxy of points, with floating
 * code/profit glyphs and a custom multi-pass bloom. Mouse tilts the camera (parallax).
 */
export default function Landing3D() {
  const navigate = useNavigate();
  const rootRef = useRef(null);
  const canvasRef = useRef(null);

  // smooth-scroll helper for the internal section rail / CTAs
  const goTo = (i) => {
    const m = document.body.scrollHeight - window.innerHeight;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: m * (i / 2), behavior: reduce ? "auto" : "smooth" });
  };

  // Page title/description for this route only — restored on unmount so the
  // rest of the app keeps its own (index.html default: "NEXUS — Cockpit").
  useEffect(() => {
    const prevTitle = document.title;
    const metaDesc = document.querySelector('meta[name="description"]');
    const prevDesc = metaDesc ? metaDesc.getAttribute("content") : null;
    document.title = "NEXUS — Viaggio nel motore di trading algoritmico";
    if (metaDesc) {
      metaDesc.setAttribute(
        "content",
        "NEXUS opera l'oro validando ogni strategia su due finestre temporali indipendenti prima di fidarsene. Entra nel motore."
      );
    }
    return () => {
      document.title = prevTitle;
      if (metaDesc && prevDesc !== null) metaDesc.setAttribute("content", prevDesc);
    };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const root = rootRef.current;
    if (!canvas || !root) return;

    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
    } catch (e) {
      const fb = root.querySelector(".nx3d-fallback");
      if (fb) fb.classList.add("show");
      canvas.style.display = "none";
      return;
    }
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(window.devicePixelRatio, 2);
    renderer.setPixelRatio(dpr);
    renderer.setSize(window.innerWidth, window.innerHeight);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x04060f);
    scene.fog = new THREE.FogExp2(0x05070f, 0.0065);
    const camera = new THREE.PerspectiveCamera(62, window.innerWidth / window.innerHeight, 0.1, 600);

    scene.add(new THREE.AmbientLight(0x22406a, 1.1));
    const dir = new THREE.DirectionalLight(0x9fd8ff, 1.4);
    dir.position.set(5, 10, 6);
    scene.add(dir);
    // rim/fill indigo — non illumina, contorna: da' volume dove la key light lascia il buio.
    const rim = new THREE.DirectionalLight(0x6d5ef0, 0.55);
    rim.position.set(-8, 2, -4);
    scene.add(rim);
    const pt = new THREE.PointLight(0x38bdf8, 60, 60);
    pt.position.set(0, 1, 2);
    scene.add(pt);

    const disposables = [];
    const track = (o) => { disposables.push(o); return o; };

    // ---- core crystal ----
    const coreGeo = track(new THREE.IcosahedronGeometry(2, 0));
    const coreMat = track(new THREE.MeshStandardMaterial({ color: 0x2e6fd6, emissive: 0x0a3a7a, emissiveIntensity: 0.7, metalness: 0.6, roughness: 0.25, flatShading: true }));
    const core = new THREE.Mesh(coreGeo, coreMat);
    core.position.set(0, 1, 0);
    scene.add(core);
    const wireGeo = track(new THREE.WireframeGeometry(new THREE.IcosahedronGeometry(2.04, 0)));
    const wireMat = track(new THREE.LineBasicMaterial({ color: 0x7ff0ff, transparent: true, opacity: 0.5 }));
    const coreWire = new THREE.LineSegments(wireGeo, wireMat);
    coreWire.position.copy(core.position);
    scene.add(coreWire);

    // ---- riflesso: pavimento vetro/metallo che restituisce un'eco capovolta ----
    const floorGeo = track(new THREE.PlaneGeometry(240, 240));
    const floorMat = track(new THREE.MeshStandardMaterial({ color: 0x060a16, metalness: 0.9, roughness: 0.18, envMapIntensity: 1.2 }));
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -7;
    scene.add(floor);

    // ---- market corridor of candlesticks ----
    const NC = 70;
    let price = 0, seed = 11;
    const rnd = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };
    const candleGeo = track(new THREE.BoxGeometry(0.55, 1, 0.55));
    const candleMat = track(new THREE.MeshBasicMaterial());
    const candles = new THREE.InstancedMesh(candleGeo, candleMat, NC);
    const dummy = new THREE.Object3D();
    const cUp = new THREE.Color(0x2ee88f), cDn = new THREE.Color(0xff6b7f);
    const curvePts = [];
    for (let i = 0; i < NC; i++) {
      const z = 4 - i * 2.8, o = price, dv = (rnd() - 0.46) * 2.0;
      price += dv;
      const cl = price, up = cl >= o, h = Math.max(0.4, Math.abs(cl - o)) * 0.8, mid = (o + cl) / 2, x = Math.sin(i * 0.16) * 3.0;
      dummy.position.set(x, mid * 0.6, z);
      dummy.scale.set(1, h, 1);
      dummy.rotation.set(0, 0, 0);
      dummy.updateMatrix();
      candles.setMatrixAt(i, dummy.matrix);
      candles.setColorAt(i, up ? cUp : cDn);
      curvePts.push(new THREE.Vector3(x, price * 0.6 + 3.0, z));
    }
    candles.instanceMatrix.needsUpdate = true;
    if (candles.instanceColor) candles.instanceColor.needsUpdate = true;
    scene.add(candles);

    // ---- glowing equity tube ----
    const curve = new THREE.CatmullRomCurve3(curvePts);
    const tubeGeo = track(new THREE.TubeGeometry(curve, 240, 0.11, 10, false));
    const tubeMat = track(new THREE.MeshBasicMaterial({ color: 0x38e6ff }));
    const tube = new THREE.Mesh(tubeGeo, tubeMat);
    scene.add(tube);

    // ---- galaxy points ----
    const softDisc = () => {
      const c = document.createElement("canvas");
      c.width = c.height = 64;
      const x = c.getContext("2d");
      const g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
      g.addColorStop(0, "rgba(255,255,255,1)");
      g.addColorStop(0.3, "rgba(255,255,255,.7)");
      g.addColorStop(1, "rgba(255,255,255,0)");
      x.fillStyle = g; x.fillRect(0, 0, 64, 64);
      return new THREE.CanvasTexture(c);
    };
    const disc = track(softDisc());
    const NP = 2600;
    const gp = new Float32Array(NP * 3), gc = new Float32Array(NP * 3);
    const palette = [[0.35, 0.65, 1.0], [0.13, 0.83, 0.97], [0.9, 0.95, 1.0], [0.4, 0.9, 0.75]];
    for (let i = 0; i < NP; i++) {
      gp[i * 3] = (Math.random() - 0.5) * 120;
      gp[i * 3 + 1] = (Math.random() - 0.5) * 70;
      gp[i * 3 + 2] = Math.random() * -220 + 10;
      const col = palette[(Math.random() * palette.length) | 0];
      gc[i * 3] = col[0]; gc[i * 3 + 1] = col[1]; gc[i * 3 + 2] = col[2];
    }
    const gGeo = track(new THREE.BufferGeometry());
    gGeo.setAttribute("position", new THREE.Float32BufferAttribute(gp, 3));
    gGeo.setAttribute("color", new THREE.Float32BufferAttribute(gc, 3));
    const gMat = track(new THREE.PointsMaterial({ size: 0.7, map: disc, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true }));
    const galaxy = new THREE.Points(gGeo, gMat);
    scene.add(galaxy);

    // ---- floating code / profit glyphs ----
    const glyphTex = (text, color) => {
      const c = document.createElement("canvas");
      c.width = 256; c.height = 96;
      const x = c.getContext("2d");
      x.clearRect(0, 0, 256, 96);
      x.font = "bold 54px ui-monospace,Menlo,Consolas,monospace";
      x.textAlign = "center"; x.textBaseline = "middle";
      x.fillStyle = color; x.shadowColor = color; x.shadowBlur = 18;
      x.fillText(text, 128, 50);
      return new THREE.CanvasTexture(c);
    };
    const tokens = [["BUY", "#34d399"], ["SELL", "#fb7185"], ["+0.8R", "#38e6ff"], ["XAU", "#eaf2ff"], ["ATR", "#38e6ff"], ["D1", "#8ea6cf"], ["H4", "#8ea6cf"], ["R:R", "#34d399"], ["SL", "#fb7185"], ["TP", "#34d399"], ["{ }", "#60a5fa"], ["0x3A", "#8ea6cf"]];
    const glyphs = [];
    for (let i = 0; i < 46; i++) {
      const tk = tokens[i % tokens.length];
      const tex = track(glyphTex(tk[0], tk[1]));
      const mat = track(new THREE.SpriteMaterial({ map: tex, transparent: true, blending: THREE.AdditiveBlending, opacity: 0.85, depthWrite: false }));
      const sp = new THREE.Sprite(mat);
      sp.position.set((Math.random() - 0.5) * 40, (Math.random() - 0.5) * 26, -Math.random() * 190 + 6);
      const s = 1.6 + Math.random() * 1.4;
      sp.scale.set(s * 2.2, s, 1);
      scene.add(sp);
      glyphs.push(sp);
    }

    // ---- camera flight path ----
    const camPath = new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, 3, 15), new THREE.Vector3(5, 4.5, -24), new THREE.Vector3(-4, 7, -64),
      new THREE.Vector3(3, 10, -118), new THREE.Vector3(0, 15, -176),
    ]);
    const lookPath = new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 3, -40), new THREE.Vector3(0, 6, -80),
      new THREE.Vector3(0, 10, -130), new THREE.Vector3(0, 15, -190),
    ]);

    // ---- bloom (custom multi-pass) ----
    const ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const postScene = new THREE.Scene();
    const quadGeo = track(new THREE.PlaneGeometry(2, 2));
    const quad = new THREE.Mesh(quadGeo);
    postScene.add(quad);
    const RT = (w, h) => new THREE.WebGLRenderTarget(Math.max(1, w | 0), Math.max(1, h | 0), { minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter });
    let rtScene, rtA, rtB;
    const makeRTs = () => {
      const w = window.innerWidth * dpr, h = window.innerHeight * dpr;
      if (rtScene) rtScene.dispose();
      if (rtA) rtA.dispose();
      if (rtB) rtB.dispose();
      rtScene = RT(w, h); rtA = RT(w / 2, h / 2); rtB = RT(w / 2, h / 2);
    };
    makeRTs();
    const VS = "varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,0.0,1.0);}";
    const brightMat = track(new THREE.ShaderMaterial({
      uniforms: { tD: { value: null }, thr: { value: 0.55 } }, vertexShader: VS,
      fragmentShader: "precision highp float;varying vec2 vUv;uniform sampler2D tD;uniform float thr;void main(){vec3 c=texture2D(tD,vUv).rgb;float l=dot(c,vec3(0.299,0.587,0.114));float k=smoothstep(thr,thr+0.35,l);gl_FragColor=vec4(c*k,1.0);}",
    }));
    const mkBlur = () => new THREE.ShaderMaterial({
      uniforms: { tD: { value: null }, dir: { value: new THREE.Vector2(1, 0) }, texel: { value: new THREE.Vector2(1 / 512, 1 / 512) } }, vertexShader: VS,
      fragmentShader: "precision highp float;varying vec2 vUv;uniform sampler2D tD;uniform vec2 dir;uniform vec2 texel;void main(){vec2 o=dir*texel;vec3 s=texture2D(tD,vUv).rgb*0.227;s+=texture2D(tD,vUv+o*1.384).rgb*0.316;s+=texture2D(tD,vUv-o*1.384).rgb*0.316;s+=texture2D(tD,vUv+o*3.230).rgb*0.070;s+=texture2D(tD,vUv-o*3.230).rgb*0.070;gl_FragColor=vec4(s,1.0);}",
    });
    const blurH = track(mkBlur()), blurV = track(mkBlur());
    const compMat = track(new THREE.ShaderMaterial({
      uniforms: { tScene: { value: null }, tBloom: { value: null }, inten: { value: 1.25 }, uT: { value: 0 } }, vertexShader: VS,
      fragmentShader: "precision highp float;varying vec2 vUv;uniform sampler2D tScene;uniform sampler2D tBloom;uniform float inten;uniform float uT;"
        + "void main(){vec3 c=texture2D(tScene,vUv).rgb;vec3 b=texture2D(tBloom,vUv).rgb;vec3 col=c+b*inten;col=col/(col+vec3(0.6))*1.6;"
        // vignette del canopy: i bordi si scuriscono appena, l'occhio resta al centro
        + "vec2 uv=vUv-0.5;float vig=1.0-dot(uv,uv)*0.55;col*=vig;"
        // scanline sottilissima del sensore HUD, quasi impercettibile
        + "float sl=sin((vUv.y*820.0)-uT*2.0)*0.015;col+=sl;"
        + "gl_FragColor=vec4(col,1.0);}",
    }));
    const pass = (mat, target) => { quad.material = mat; renderer.setRenderTarget(target); renderer.render(postScene, ortho); };

    // ---- interaction state ----
    let targP = 0, prog = 0, mx = 0, my = 0, cmx = 0, cmy = 0;
    const onScroll = () => { const m = document.body.scrollHeight - window.innerHeight; targP = m > 0 ? window.scrollY / m : 0; };
    const onMouse = (e) => { mx = e.clientX / window.innerWidth - 0.5; my = e.clientY / window.innerHeight - 0.5; };
    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
      makeRTs();
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("mousemove", onMouse, { passive: true });
    window.addEventListener("resize", onResize);

    const railBtns = [...root.querySelectorAll(".nx3d-rail button")];
    const hint = root.querySelector(".nx3d-hint");

    // ---- count-up figures ----
    const fmt = (v, d) => Number(v).toLocaleString("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d });
    const io = new IntersectionObserver((es) => es.forEach((e) => {
      if (!e.isIntersecting) return;
      const el = e.target; io.unobserve(el);
      const to = +el.dataset.to, dc = +(el.dataset.dec || 0), pr = el.dataset.pre || "", su = el.dataset.suf || "";
      let s = null;
      const st = (t) => { if (!s) s = t; const p = Math.min((t - s) / 1300, 1), e2 = 1 - Math.pow(1 - p, 3); el.textContent = pr + fmt(to * e2, dc) + su; if (p < 1) requestAnimationFrame(st); };
      requestAnimationFrame(st);
    }), { threshold: 0.6 });
    root.querySelectorAll(".nx3d-fig .nx3d-v").forEach((el) => io.observe(el));

    // ---- render loop ----
    const tmpPos = new THREE.Vector3(), tmpLook = new THREE.Vector3(), clock = new THREE.Clock();
    let raf = 0;
    const tick = () => {
      const t = clock.getElapsedTime();
      prog += (targP - prog) * 0.06;
      cmx += ((reduce ? 0 : mx) - cmx) * 0.05;
      cmy += ((reduce ? 0 : my) - cmy) * 0.05;
      const p = Math.min(Math.max(prog, 0), 1);
      camPath.getPointAt(p, tmpPos);
      lookPath.getPointAt(Math.min(p + 0.02, 1), tmpLook);
      camera.position.set(tmpPos.x + cmx * 5, tmpPos.y - cmy * 3.5, tmpPos.z);
      camera.lookAt(tmpLook.x + cmx * 2, tmpLook.y - cmy * 1.5, tmpLook.z);

      core.rotation.y = t * 0.3; core.rotation.x = t * 0.15; coreWire.rotation.copy(core.rotation);
      tube.material.color.setHSL(0.52, 1, 0.6 + Math.sin(t * 2) * 0.06);
      galaxy.rotation.y = t * 0.01;
      for (let i = 0; i < glyphs.length; i++) { glyphs[i].position.y += Math.sin(t * 0.5 + i) * 0.002; glyphs[i].material.rotation = Math.sin(t * 0.2 + i) * 0.05; }

      renderer.setRenderTarget(rtScene); renderer.render(scene, camera);
      brightMat.uniforms.tD.value = rtScene.texture; pass(brightMat, rtA);
      const tx = 1 / (window.innerWidth * dpr / 2), ty = 1 / (window.innerHeight * dpr / 2);
      blurH.uniforms.tD.value = rtA.texture; blurH.uniforms.dir.value.set(1, 0); blurH.uniforms.texel.value.set(tx, ty); pass(blurH, rtB);
      blurV.uniforms.tD.value = rtB.texture; blurV.uniforms.dir.value.set(0, 1); blurV.uniforms.texel.value.set(tx, ty); pass(blurV, rtA);
      compMat.uniforms.tScene.value = rtScene.texture; compMat.uniforms.tBloom.value = rtA.texture; compMat.uniforms.uT.value = t;
      renderer.setRenderTarget(null); quad.material = compMat; renderer.render(postScene, ortho);

      root.querySelectorAll(".nx3d-card").forEach((c) => {
        const d = parseFloat(c.dataset.par) || 1;
        c.style.transform = `translate3d(${cmx * -30 * d}px,${cmy * -20 * d}px,0)`;
      });
      const active = Math.round(p * 2);
      railBtns.forEach((b, i) => b.classList.toggle("on", i === active));
      if (hint) hint.style.opacity = p > 0.02 ? "0" : "0.85";
      const sectionLabel = root.querySelector("#nx3d-hud-section");
      if (sectionLabel) sectionLabel.textContent = `SEZIONE 0${active + 1} / 03`;
      root.querySelectorAll(".nx3d-glasspanel").forEach((el, i) => {
        const side = i === 0 ? -1 : 1;
        el.style.transform = `translateY(calc(-50% + ${cmy * -14}px)) translateX(${side * cmx * 10}px)`;
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    // ---- cleanup ----
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("mousemove", onMouse);
      window.removeEventListener("resize", onResize);
      io.disconnect();
      if (rtScene) rtScene.dispose();
      if (rtA) rtA.dispose();
      if (rtB) rtB.dispose();
      disposables.forEach((o) => o && o.dispose && o.dispose());
      renderer.dispose();
    };
  }, []);

  return (
    <div className="nx3d" ref={rootRef}>
      <canvas className="nx3d-gl" ref={canvasRef} />
      <div className="nx3d-fallback">Il tuo browser non supporta WebGL.<br />Prova un browser aggiornato su desktop.</div>

      <div className="nx3d-hud" aria-hidden="true">
        <span className="nx3d-hud-corner tl" />
        <span className="nx3d-hud-corner tr" />
        <span className="nx3d-hud-corner bl" />
        <span className="nx3d-hud-corner br" />
        <div className="nx3d-hud-sweep" />
        <div className="nx3d-hud-label tl">NEXUS · XAU/USD</div>
        <div className="nx3d-hud-label tr">MOTORE MULTI-TIMEFRAME</div>
        <div className="nx3d-hud-label bl">VALIDAZIONE · 3M + 3Y</div>
        <div className="nx3d-hud-label br" id="nx3d-hud-section">SEZIONE 01 / 03</div>
      </div>

      <aside className="nx3d-glasspanel left" aria-hidden="true">
        <div className="nx3d-gp-title">Motore</div>
        <div className="nx3d-gp-row"><span>Strategie</span><b>36</b></div>
        <div className="nx3d-gp-row"><span>Simbolo</span><b>XAU/USD</b></div>
        <div className="nx3d-gp-row"><span>Modalità</span><b>Hedge</b></div>
      </aside>
      <aside className="nx3d-glasspanel right" aria-hidden="true">
        <div className="nx3d-gp-title">Validazione</div>
        <div className="nx3d-gp-row"><span>Finestre</span><b>2</b></div>
        <div className="nx3d-gp-row"><span>Storico</span><b>10 anni</b></div>
        <div className="nx3d-gp-row"><span>Metodo</span><b>Doppio test</b></div>
      </aside>

      <nav className="nx3d-rail" aria-label="Sezioni">
        <button className="on" aria-label="Sezione 1" onClick={() => goTo(0)} />
        <button aria-label="Sezione 2" onClick={() => goTo(1)} />
        <button aria-label="Sezione 3" onClick={() => goTo(2)} />
      </nav>
      <div className="nx3d-hint">Scrolla per viaggiare nel motore</div>

      <main className="nx3d-scroll">
        <section className="nx3d-panel">
          <div className="nx3d-card" data-par="1.3">
            <span className="nx3d-eyebrow">Viaggio nel trading algoritmico</span>
            <h1>NEXUS</h1>
            <p className="nx3d-lede">Vola <b>dentro il mercato dell'oro</b>. Tra le candele, lungo la curva del profitto.</p>
            <p className="nx3d-sub">Non guardi un grafico: lo attraversi. Muovi il mouse per virare, scrolla per accelerare.</p>
            <div className="nx3d-cta">
              <button className="nx3d-btn primary" onClick={() => navigate("/login")}>Entra nel motore</button>
              <button className="nx3d-btn" onClick={() => goTo(1)}>Come funziona</button>
            </div>
          </div>
        </section>

        <section className="nx3d-panel right">
          <div className="nx3d-card" data-par="1.7">
            <span className="nx3d-eyebrow">Il motore</span>
            <h2>Ogni candela<br />è una decisione.</h2>
            <p className="nx3d-lede">Dieci strategie, ognuna nella sua corsia. Multi-timeframe. Uscite su misura.</p>
            <p className="nx3d-sub">Trend che corrono, mean-reversion che incassano. E la curva sale.</p>
          </div>
        </section>

        <section className="nx3d-panel center">
          <div className="nx3d-card" data-par="1.0">
            <span className="nx3d-eyebrow" style={{ justifyContent: "center" }}>Il metodo</span>
            <h2>Non ci fidiamo di un solo backtest.</h2>
            <p className="nx3d-lede">Ogni strategia viene validata su <b>almeno due finestre indipendenti</b> — pochi mesi e diversi anni — prima di essere considerata affidabile.</p>
            <p className="nx3d-sub">Se regge solo su una, resta a rischio minimo o si spegne. Un risultato che sembra ottimo su un periodo corto e crolla su uno lungo non è un edge: è rumore travestito da fortuna. Non lo pubblichiamo come prova finché non regge su entrambi.</p>
            <div className="nx3d-figs">
              <div className="nx3d-fig"><div className="nx3d-v c" data-to="36" data-dec="0">0</div><div className="nx3d-k">Strategie testate indipendentemente</div></div>
              <div className="nx3d-fig"><div className="nx3d-v c" data-to="2" data-dec="0">0</div><div className="nx3d-k">Finestre temporali per ogni verdetto</div></div>
              <div className="nx3d-fig"><div className="nx3d-v c" data-to="10" data-suf=" anni" data-dec="0">0</div><div className="nx3d-k">Storico usato per lo screening</div></div>
            </div>
            <div className="nx3d-cta">
              <button className="nx3d-btn primary" onClick={() => navigate("/login")}>Apri il Backtest Lab</button>
              <button className="nx3d-btn" onClick={() => goTo(0)}>Torna alla partenza</button>
            </div>
            <p className="nx3d-disc">Risultati da backtest su dati storici: non sono garanzia di rendimenti futuri. Il trading a leva comporta rischio di perdita del capitale.</p>
          </div>
        </section>
      </main>
    </div>
  );
}
