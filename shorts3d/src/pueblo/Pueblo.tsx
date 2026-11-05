// EL PUEBLO (compartido por los 6 videos) y sus interiores. Low-poly modular y muy saturado. Coordenadas fijas:
// el pueblo en el origen; el cuarto en x=200, el basurero en x=-200 y la oficina de la alcaldía en z=200, para que
// cada escena monte solo lo que necesita y las cámaras sean siempre las mismas entre episodios.
import React, {useEffect, useMemo, useState} from 'react';
import {continueRender, delayRender} from 'remotion';
import * as THREE from 'three';
import {SPEC} from './spec';
import {fuenteLista} from './fuente';
import type {V3} from './tipos';
import {rnd} from '../anim';
import {matMundo} from './look/mirada';
import {grassHD, cobbleHD, roofHD, stoneHD, rep, planksHD} from '../skill_cartoon/bridge/paint';
const T = {pasto: () => rep(grassHD(), 18, 18), plaza: () => rep(cobbleHD(), 6, 6), camino: () => rep(stoneHD(), 2, 8), madera: () => rep(planksHD(), 2, 2)};

const C = SPEC.color;
/** material del mundo: el Lambert de dos tonos de la skill (sombra fría, luz cálida), con textura pintada opcional */
export const M: React.FC<{c: string; e?: string; ei?: number; map?: THREE.Texture}> = ({c, e, ei, map}) => <primitive object={matMundo(c, {e, ei, map})} attach="material" />;
export const Caja: React.FC<{p: V3; s: V3; c: string; r?: V3; e?: string; ei?: number; sombra?: boolean; map?: THREE.Texture}> = ({p, s, c, r, e, ei, sombra = true, map}) => (
  <mesh position={p} rotation={r} castShadow={sombra} receiveShadow><boxGeometry args={s} /><M c={c} e={e} ei={ei} map={map} /></mesh>
);
export const Techo: React.FC<{p: V3; w: number; d: number; h: number; c: string; rot?: number}> = ({p, w, d, h, c, rot = 0}) => (
  <mesh position={p} rotation={[0, rot, 0]} castShadow>
    <cylinderGeometry args={[0.01, w * 0.72, h, 4, 1]} /><M c={c} />
  </mesh>
);
/** techo a dos aguas: prisma */
export const DosAguas: React.FC<{p: V3; w: number; d: number; h: number; c: string}> = ({p, w, d, h, c}) => {
  const geo = useMemo(() => {
    const s = new THREE.Shape(); s.moveTo(-w / 2 - 0.25, 0); s.lineTo(w / 2 + 0.25, 0); s.lineTo(0, h); s.closePath();
    const g = new THREE.ExtrudeGeometry(s, {depth: d + 0.4, bevelEnabled: false}); g.translate(0, 0, -(d + 0.4) / 2); return g;
  }, [w, d, h]);
  return <mesh geometry={geo} position={p} castShadow><M c="#ffffff" map={roofHD(c)} /></mesh>;
};

// ---------- carteles con letras (Montserrat) ----------
const texCache = new Map<string, THREE.Texture>();
const texCartel = (texto: string, fondo: string, color: string) => {
  const k = texto + fondo + color;
  if (!texCache.has(k)) {
    const cv = document.createElement('canvas'); cv.width = 1024; cv.height = 256;
    const c = cv.getContext('2d')!;
    const pintar = () => {
    c.fillStyle = fondo; c.fillRect(0, 0, 1024, 256);
    c.strokeStyle = 'rgba(0,0,0,0.25)'; c.lineWidth = 16; c.strokeRect(8, 8, 1008, 240);
    c.fillStyle = color; c.font = '800 150px Montserrat'; c.textAlign = 'center'; c.textBaseline = 'middle';
    let tam = 150; while (c.measureText(texto).width > 940 && tam > 40) { tam -= 6; c.font = `800 ${tam}px Montserrat`; }
    c.fillText(texto, 512, 136);
    };
    pintar();
    const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
    texCache.set(k, t);
    // si la fuente aún no había cargado, se vuelve a pintar en cuanto esté (Remotion espera a la fuente)
    fuenteLista.then(() => { c.clearRect(0, 0, 1024, 256); pintar(); t.needsUpdate = true; });
  }
  return texCache.get(k)!;
};
export const Cartel: React.FC<{p: V3; w: number; texto: string; fondo?: string; color?: string; rotY?: number}> = ({p, w, texto, fondo = '#fff6dc', color = '#5a2d0c', rotY = 0}) => {
  const lista = true;
  return (
    <group position={p} rotation={[0, rotY, 0]}>
      <mesh position={[0, 0, -0.03]} castShadow><boxGeometry args={[w + 0.12, w / 4 + 0.12, 0.06]} /><M c="#7a4a1e" /></mesh>
      {lista && <mesh><planeGeometry args={[w, w / 4]} /><meshStandardMaterial map={texCartel(texto, fondo, color)} roughness={0.7} /></mesh>}
    </group>
  );
};

// ---------- piezas del pueblo ----------
export const Ventana: React.FC<{p: V3; s?: [number, number]; noche?: boolean; luz?: boolean; rotY?: number}> = ({p, s = [0.8, 0.9], noche, luz = true, rotY = 0}) => (
  <group position={p} rotation={[0, rotY, 0]}>
    <mesh><planeGeometry args={s} /><meshStandardMaterial color={noche && luz ? C.ventana : '#9fd8ff'} emissive={noche && luz ? C.ventana : '#000'} emissiveIntensity={noche && luz ? 1.2 : 0} roughness={0.2} /></mesh>
    <Caja p={[0, 0, 0.02]} s={[s[0] + 0.12, 0.08, 0.06]} c="#fff" />
    <Caja p={[0, 0, 0.02]} s={[0.08, s[1] + 0.12, 0.06]} c="#fff" />
    <Caja p={[0, -s[1] / 2 - 0.05, 0.06]} s={[s[0] + 0.25, 0.08, 0.16]} c="#fff" />
  </group>
);
export const Casa: React.FC<{p: V3; w?: number; d?: number; h?: number; pared: string; techo: string; rotY?: number; noche?: boolean; puerta?: string}> = ({p, w = 4, d = 4, h = 3, pared, techo, rotY = 0, noche, puerta = '#8b4a2b'}) => (
  <group position={p} rotation={[0, rotY, 0]}>
    <Caja p={[0, h / 2, 0]} s={[w, h, d]} c={pared} />
    <DosAguas p={[0, h, 0]} w={w} d={d} h={1.6} c={techo} />
    <Caja p={[0, 0.95, d / 2 + 0.01]} s={[0.9, 1.9, 0.08]} c={puerta} />
    <mesh position={[0.3, 0.95, d / 2 + 0.06]}><sphereGeometry args={[0.06, 8, 6]} /><M c="#ffd166" /></mesh>
    <Ventana p={[-w / 4 - 0.25, h * 0.58, d / 2 + 0.02]} noche={noche} />
    <Ventana p={[w / 4 + 0.25, h * 0.58, d / 2 + 0.02]} noche={noche} />
  </group>
);
export const Farol: React.FC<{p: V3; noche?: boolean}> = ({p, noche}) => (
  <group position={p}>
    <mesh position={[0, 1.4, 0]} castShadow><cylinderGeometry args={[0.07, 0.1, 2.8, 8]} /><M c="#2b2d42" /></mesh>
    <mesh position={[0, 2.95, 0]}><boxGeometry args={[0.36, 0.42, 0.36]} /><meshStandardMaterial color={C.farol} emissive={C.farol} emissiveIntensity={noche ? 2 : 0.25} /></mesh>
    <mesh position={[0, 3.25, 0]}><coneGeometry args={[0.3, 0.25, 4]} /><M c="#2b2d42" /></mesh>
    {noche && <pointLight position={[0, 2.8, 0]} intensity={8} distance={9} decay={1.5} color={C.farol} />}
  </group>
);
export const Banca: React.FC<{p: V3; rotY?: number}> = ({p, rotY = 0}) => (
  <group position={p} rotation={[0, rotY, 0]}>
    <Caja p={[0, 0.45, 0]} s={[1.8, 0.1, 0.5]} c="#c1793f" />
    <Caja p={[0, 0.85, -0.22]} s={[1.8, 0.5, 0.08]} c="#c1793f" />
    {[-0.75, 0.75].map((x) => <Caja key={x} p={[x, 0.22, 0]} s={[0.1, 0.45, 0.45]} c="#2b2d42" />)}
  </group>
);
export const Arbol: React.FC<{p: V3; s?: number; tono?: number}> = ({p, s = 1, tono = 0}) => (
  <group position={p} scale={s}>
    <mesh position={[0, 0.9, 0]} castShadow><cylinderGeometry args={[0.18, 0.26, 1.8, 6]} /><M c="#7a4a24" /></mesh>
    <mesh position={[0, 2.4, 0]} castShadow><icosahedronGeometry args={[1.15, 0]} /><M c={tono ? '#2f9e44' : '#40c057'} /></mesh>
    <mesh position={[0.3, 3.1, 0.2]} castShadow><icosahedronGeometry args={[0.75, 0]} /><M c={tono ? '#40c057' : '#69db7c'} /></mesh>
  </group>
);
const Nube: React.FC<{p: V3; s: number}> = ({p, s}) => (
  <group position={p} scale={s}>
    {[[0, 0, 0, 1.2], [1.3, -0.2, 0, 0.9], [-1.3, -0.25, 0, 0.85], [0.5, 0.5, 0, 0.9]].map(([x, y, z, r], i) => (
      <mesh key={i} position={[x, y, z]}><icosahedronGeometry args={[r, 1]} /><meshStandardMaterial color="#ffffff" roughness={1} flatShading emissive="#ffffff" emissiveIntensity={0.25} /></mesh>
    ))}
  </group>
);
/** torre del reloj: las agujas marcan `hora` (decimal, 3.55 = 3:33) */
export const TorreReloj: React.FC<{hora: number; noche?: boolean}> = ({hora, noche}) => {
  const h = (hora % 12) / 12 * Math.PI * 2, m = (hora % 1) * Math.PI * 2;
  return (
    <group position={[0, 0, -13]}>
      <Caja p={[0, 4.5, 0]} s={[3, 9, 3]} c="#f4e1c1" />
      <Caja p={[0, 9.4, 0]} s={[3.4, 0.8, 3.4]} c="#d4a373" />
      <mesh position={[0, 10.9, 0]} rotation={[0, Math.PI / 4, 0]} castShadow><coneGeometry args={[2.5, 2.4, 4]} /><M c={C.techoAzul} /></mesh>
      <group position={[0, 7.4, 1.52]}>
        <mesh rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[1.05, 1.05, 0.1, 32]} /><meshStandardMaterial color="#fffaf0" emissive={noche ? '#fff1c1' : '#000'} emissiveIntensity={noche ? 0.8 : 0} /></mesh>
        {Array.from({length: 12}, (_, i) => <Caja key={i} p={[Math.sin(i / 12 * Math.PI * 2) * 0.88, Math.cos(i / 12 * Math.PI * 2) * 0.88, 0.07]} s={[0.07, 0.16, 0.02]} c="#333" r={[0, 0, -i / 12 * Math.PI * 2]} />)}
        <group rotation={[0, 0, -h]}><Caja p={[0, 0.28, 0.09]} s={[0.09, 0.56, 0.03]} c="#222" /></group>
        <group rotation={[0, 0, -m]}><Caja p={[0, 0.4, 0.11]} s={[0.06, 0.8, 0.03]} c="#222" /></group>
        <mesh position={[0, 0, 0.12]}><sphereGeometry args={[0.07, 10, 8]} /><M c="#222" /></mesh>
      </group>
      <Caja p={[0, 1.2, 1.52]} s={[1.2, 2.4, 0.1]} c="#8b4a2b" />
    </group>
  );
};
export const Fuente: React.FC<{f: number}> = ({f}) => (
  <group>
    <mesh position={[0, 0.35, 0]} castShadow receiveShadow><cylinderGeometry args={[2.1, 2.3, 0.7, 12]} /><M c="#bfc6d1" /></mesh>
    <mesh position={[0, 0.66, 0]}><cylinderGeometry args={[1.85, 1.85, 0.05, 24]} /><meshStandardMaterial color="#38b6ff" roughness={0.15} emissive="#1b78c0" emissiveIntensity={0.15 + 0.05 * Math.sin(f / 9)} /></mesh>
    <mesh position={[0, 1.2, 0]} castShadow><cylinderGeometry args={[0.25, 0.35, 1.2, 8]} /><M c="#bfc6d1" /></mesh>
    <mesh position={[0, 1.85, 0]} castShadow><cylinderGeometry args={[0.8, 0.6, 0.25, 12]} /><M c="#bfc6d1" /></mesh>
    {Array.from({length: 6}, (_, i) => {
      const a = i / 6 * Math.PI * 2, k = ((f * 0.04 + i / 6) % 1);
      return <mesh key={i} position={[Math.cos(a) * (0.5 + k * 0.9), 2.1 + Math.sin(k * Math.PI) * 0.6 - k * 1.3, Math.sin(a) * (0.5 + k * 0.9)]}><sphereGeometry args={[0.08, 8, 6]} /><meshStandardMaterial color="#8fd3ff" transparent opacity={0.85} /></mesh>;
    })}
  </group>
);

/** EL PUEBLO completo, alrededor de la plaza */
export const Pueblo: React.FC<{f: number; noche?: boolean; hora?: number; sinCasas?: string[]; panaderia?: string}> = ({f, noche, hora = 10.2, panaderia = 'PANADERÍA'}) => {
  const arboles = useMemo(() => Array.from({length: 46}, (_, i) => {
    const a = (i / 46) * Math.PI * 2 + rnd(i, 1) * 0.1, r = 27 + rnd(i, 2) * 12;
    return {p: [Math.cos(a) * r, 0, Math.sin(a) * r - 4] as V3, s: 0.9 + rnd(i, 3) * 0.8, t: i % 2};
  }), []);
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><circleGeometry args={[60, 48]} /><M c="#ffffff" map={T.pasto()} /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]} receiveShadow><circleGeometry args={[9.5, 40]} /><M c="#ffffff" map={T.plaza()} /></mesh>
      {[0, Math.PI / 2, Math.PI, -Math.PI / 2].map((r) => (
        <mesh key={r} rotation={[-Math.PI / 2, 0, r]} position={[Math.sin(r) * 17, 0.015, Math.cos(r) * 17]} receiveShadow><planeGeometry args={[3.2, 16]} /><M c="#ffffff" map={T.camino()} /></mesh>
      ))}
      <Fuente f={f} />
      <TorreReloj hora={hora} noche={noche} />
      {/* ALCALDÍA, PANADERÍA y ESCUELA */}
      <group position={[-11, 0, -7]} rotation={[0, 0.6, 0]}>
        <Caja p={[0, 2.5, 0]} s={[7, 5, 4.5]} c="#f2e8cf" />
        <DosAguas p={[0, 5, 0]} w={7} d={4.5} h={1.8} c={C.techoRojo} />
        {[-2.4, -0.8, 0.8, 2.4].map((x) => <Caja key={x} p={[x, 1.6, 2.45]} s={[0.35, 3.2, 0.35]} c="#ffffff" />)}
        <Caja p={[0, 1.2, 2.26]} s={[1.3, 2.4, 0.06]} c="#6b3b1f" />
        <Ventana p={[-1.6, 3.8, 2.27]} noche={noche} />
        <Ventana p={[1.6, 3.8, 2.27]} noche={noche} />
        <Cartel p={[0, 4.55, 2.3]} w={3.2} texto="ALCALDÍA" fondo="#fff" color="#b3261e" />
      </group>
      <group position={[11, 0, -7]} rotation={[0, -0.6, 0]}>
        <Caja p={[0, 1.8, 0]} s={[5.5, 3.6, 4.2]} c="#ffd6a5" />
        <DosAguas p={[0, 3.6, 0]} w={5.5} d={4.2} h={1.6} c={C.techoNaranja} />
        {Array.from({length: 7}, (_, i) => <Caja key={i} p={[-2.4 + i * 0.8, 3.5, 2.5]} s={[0.8, 0.12, 1]} c={i % 2 ? '#ffffff' : '#e63946'} r={[0.35, 0, 0]} />)}
        <Ventana p={[-1.3, 1.6, 2.12]} s={[1.6, 1.2]} noche={noche} />
        <Caja p={[1.4, 1.0, 2.12]} s={[0.9, 2.0, 0.06]} c="#8b4a2b" />
        <Cartel p={[0, 3.1, 2.16]} w={3.4} texto={panaderia} fondo="#fff3d6" color="#8b4a2b" />
      </group>
      <group position={[-13, 0, 6]} rotation={[0, 1.6, 0]}>
        <Caja p={[0, 2.2, 0]} s={[8, 4.4, 4.5]} c="#bde0fe" />
        <DosAguas p={[0, 4.4, 0]} w={8} d={4.5} h={1.7} c={C.techoAzul} />
        {[-2.8, -1, 1, 2.8].map((x) => <Ventana key={x} p={[x, 2.4, 2.27]} noche={noche} />)}
        <Cartel p={[0, 3.9, 2.3]} w={3.2} texto="ESCUELA" fondo="#fff" color="#1d4e89" />
        <mesh position={[3.6, 5.2, 0]}><cylinderGeometry args={[0.04, 0.04, 2, 6]} /><M c="#555" /></mesh>
      </group>
      {/* casas de colores separadas */}
      <Casa p={[13, 0, 6]} pared="#ffadad" techo={C.techoAzul} rotY={-1.6} noche={noche} />
      <Casa p={[17, 0, -1]} pared="#caffbf" techo={C.techoRojo} rotY={-1.3} noche={noche} />
      <Casa p={[-18, 0, -1]} pared="#ffc6ff" techo={C.techoNaranja} rotY={1.3} noche={noche} />
      <Casa p={[6, 0, 15]} pared="#fdffb6" techo={C.techoRojo} rotY={Math.PI} noche={noche} />
      <Casa p={[-6, 0, 15]} pared="#a0c4ff" techo={C.techoNaranja} rotY={Math.PI} noche={noche} />
      <Casa p={[18, 0, 12]} pared="#ffd6a5" techo={C.techoAzul} rotY={-2.3} noche={noche} />
      <Casa p={[-18, 0, 12]} pared="#9bf6ff" techo={C.techoRojo} rotY={2.3} noche={noche} />
      {[0.4, 1.2, 2.0, 2.8, 3.6, 4.4, 5.2, 6.0].map((a) => <Farol key={a} p={[Math.cos(a) * 9.2, 0, Math.sin(a) * 9.2]} noche={noche} />)}
      <Banca p={[-5.5, 0, 0]} rotY={Math.PI / 2} />
      <Banca p={[5.5, 0, 0]} rotY={-Math.PI / 2} />
      {arboles.map((t, i) => <Arbol key={i} p={t.p} s={t.s} tono={t.t} />)}
      {!noche && [[-20, 22, -40, 3], [10, 26, -45, 3.6], [32, 20, -30, 2.6], [-36, 18, -20, 2.4]].map(([x, y, z, s], i) => <Nube key={i} p={[x + Math.sin(f / 200 + i) * 2, y, z]} s={s} />)}
      {noche && <mesh position={[-25, 30, -45]}><sphereGeometry args={[3, 24, 16]} /><meshBasicMaterial color="#fff6d5" /></mesh>}
    </group>
  );
};

/** cielo + luces. De día: brillante, uniforme, sombras suaves. De noche: azul oscuro con luz cálida, nunca negro. */
export const Luz: React.FC<{noche?: boolean; interior?: boolean}> = ({noche, interior}) => (
  <>
    <color attach="background" args={[noche ? C.noche : C.cielo]} />
    <fog attach="fog" args={[noche ? C.noche : C.cieloBajo, 40, 90]} />
    <hemisphereLight args={[noche ? '#6d8fe0' : '#cfefff', noche ? '#1a2244' : '#7bd36f', noche ? 0.9 : 1.25]} />
    <directionalLight position={[12, 22, 14]} intensity={noche ? 0.5 : 2.2} color={noche ? '#9db8ff' : '#fff6e6'} castShadow
      shadow-mapSize={[2048, 2048]} shadow-camera-left={-30} shadow-camera-right={30} shadow-camera-top={30} shadow-camera-bottom={-30} shadow-radius={4} shadow-bias={-0.0005} />
    {!noche && <directionalLight position={[-10, 8, -6]} intensity={0.5} color="#bfe0ff" />}
    {interior && <ambientLight intensity={noche ? 0.25 : 0.4} />}
  </>
);

// ---------- interiores ----------
export const CUARTO: V3 = [200, 0, 0];
/** cuarto de un niño: cama, ventana, armario, lámpara. Se ve desde +z (pared frontal abierta). */
export const Cuarto: React.FC<{noche?: boolean; vacio?: boolean; pared?: string; luzLampara?: boolean; children?: React.ReactNode}> = ({noche, vacio, pared = '#ffd6e0', luzLampara = true, children}) => (
  <group position={CUARTO}>
    <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[8, 7]} /><M c="#e0a070" map={T.madera()} /></mesh>
    <Caja p={[0, 1.6, -3.5]} s={[8, 3.2, 0.2]} c={pared} sombra={false} />
    <Caja p={[-4, 1.6, 0]} s={[0.2, 3.2, 7]} c={pared} sombra={false} />
    <Caja p={[4, 1.6, 0]} s={[0.2, 3.2, 7]} c={pared} sombra={false} />
    {/* ventana con la noche o el día afuera */}
    <group position={[1.6, 1.8, -3.39]}>
      <mesh><planeGeometry args={[1.6, 1.3]} /><meshBasicMaterial color={noche ? '#28407e' : '#8fd3ff'} /></mesh>
      {noche && <mesh position={[0.4, 0.3, 0.01]}><circleGeometry args={[0.15, 16]} /><meshBasicMaterial color="#fff6d5" /></mesh>}
      <Caja p={[0, 0, 0.03]} s={[1.72, 0.08, 0.06]} c="#fff" />
      <Caja p={[0, 0, 0.03]} s={[0.08, 1.42, 0.06]} c="#fff" />
      <Caja p={[0, -0.7, 0.1]} s={[1.9, 0.08, 0.25]} c="#fff" />
    </group>
    {!vacio && (<>
      {/* cama */}
      <Caja p={[-2.2, 0.3, -1.9]} s={[1.6, 0.6, 2.6]} c="#8d5b3c" />
      <Caja p={[-2.2, 0.66, -1.85]} s={[1.5, 0.14, 2.5]} c="#4ea8de" />
      <Caja p={[-2.2, 0.8, -2.9]} s={[1.1, 0.16, 0.45]} c="#ffffff" />
      <Caja p={[-2.2, 0.9, -3.3]} s={[1.7, 1.2, 0.12]} c="#8d5b3c" />
      {/* mesa de noche con lámpara */}
      <Caja p={[-0.9, 0.35, -3.0]} s={[0.6, 0.7, 0.6]} c="#a0522d" />
      <mesh position={[-0.9, 0.95, -3.0]}><coneGeometry args={[0.22, 0.3, 12]} /><meshStandardMaterial color="#ffe8a3" emissive="#ffcc66" emissiveIntensity={noche && luzLampara ? 1.5 : 0.1} /></mesh>
      {noche && luzLampara && <pointLight position={[-0.9, 1.1, -2.7]} intensity={3.5} distance={6} decay={1.5} color="#ffb85c" />}
      {/* alfombra */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, -0.5]} receiveShadow><circleGeometry args={[1.4, 24]} /><M c="#ffd166" /></mesh>
    </>)}
    {children}
    {noche && <pointLight position={[1.6, 2, -2.6]} intensity={2.2} distance={7} decay={1.4} color="#7fa2ff" />}
  </group>
);
/** armario: `temblor` lo hace moverse solo; `cinta` lo cierra con cinta; `ojos` = algo dentro mirando */
export const Armario: React.FC<{p: V3; f: number; temblor?: number; cinta?: boolean; ojos?: number; abierto?: number}> = ({p, f, temblor = 0, cinta, ojos = 0, abierto = 0}) => {
  const sx = Math.sin(f * 1.3) * 0.03 * temblor;
  return (
    <group position={p} rotation={[0, 0, sx]}>
      <Caja p={[0, 1.2, 0]} s={[1.6, 2.4, 0.8]} c="#9c6644" />
      <group position={[-0.78, 1.2, 0.42]} rotation={[0, -abierto * 0.4 - temblor * 0.08 * Math.abs(Math.sin(f * 0.9)), 0]}>
        <Caja p={[0.39, 0, 0]} s={[0.76, 2.2, 0.06]} c="#b07d56" />
      </group>
      <Caja p={[0.39, 1.2, 0.42]} s={[0.76, 2.2, 0.06]} c="#b07d56" />
      <mesh position={[-0.05, 1.2, 0.47]}><sphereGeometry args={[0.05, 8, 6]} /><M c="#ffd166" /></mesh>
      <mesh position={[0.05, 1.2, 0.47]}><sphereGeometry args={[0.05, 8, 6]} /><M c="#ffd166" /></mesh>
      {cinta && [-0.3, 0.3].map((y) => <Caja key={y} p={[0, 1.2 + y, 0.47]} s={[1.5, 0.12, 0.02]} c="#e9ecef" r={[0, 0, y * 0.4]} />)}
      {ojos > 0 && [-1, 1].map((s) => <mesh key={s} position={[-0.32 + s * 0.09, 1.7, 0.43]} scale={[0.05, 0.035 * ojos, 0.01]}><sphereGeometry args={[1, 10, 8]} /><meshBasicMaterial color="#ffe14d" /></mesh>)}
    </group>
  );
};

export const BASURERO: V3 = [-200, 0, 0];
export const Basurero: React.FC<{children?: React.ReactNode}> = ({children}) => {
  const pilas = useMemo(() => Array.from({length: 40}, (_, i) => ({p: [(rnd(i, 1) - 0.5) * 18, 0, -3 - rnd(i, 2) * 9] as V3, s: [0.6 + rnd(i, 3) * 1.4, 0.4 + rnd(i, 4) * 1.2, 0.6 + rnd(i, 5) * 1.2] as V3, r: rnd(i, 6) * 3, c: ['#8d99ae', '#adb5bd', '#c08552', '#6c757d', '#e9c46a', '#a3b18a'][i % 6]})), []);
  return (
    <group position={BASURERO}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><circleGeometry args={[40, 32]} /><M c="#a3a380" /></mesh>
      {pilas.map((q, i) => <Caja key={i} p={[q.p[0], q.s[1] / 2, q.p[2]]} s={q.s} c={q.c} r={[0, q.r, 0]} />)}
      {Array.from({length: 9}, (_, i) => <mesh key={i} position={[-8 + i * 2, 0.8, -14]} castShadow><cylinderGeometry args={[0.6, 0.6, 1.6, 10]} /><M c={i % 2 ? '#2a9d8f' : '#457b9d'} /></mesh>)}
      <Cartel p={[0, 2.2, -1.5]} w={3} texto="BASURERO" fondo="#ffd166" color="#3d2b1f" />
      <mesh position={[-1.5, 1.1, -1.5]}><cylinderGeometry args={[0.06, 0.06, 2.2, 6]} /><M c="#555" /></mesh>
      <mesh position={[1.5, 1.1, -1.5]}><cylinderGeometry args={[0.06, 0.06, 2.2, 6]} /><M c="#555" /></mesh>
      {children}
    </group>
  );
};

export const OFICINA: V3 = [0, 0, 200];
/** oficina del alcalde: escritorio, bandera, retrato, ventana a la plaza */
export const Oficina: React.FC<{children?: React.ReactNode}> = ({children}) => (
  <group position={OFICINA}>
    <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[9, 7]} /><M c="#b07a50" map={T.madera()} /></mesh>
    <Caja p={[0, 1.7, -3.5]} s={[9, 3.4, 0.2]} c="#e9d8a6" sombra={false} />
    <Caja p={[-4.5, 1.7, 0]} s={[0.2, 3.4, 7]} c="#e9d8a6" sombra={false} />
    <Caja p={[4.5, 1.7, 0]} s={[0.2, 3.4, 7]} c="#e9d8a6" sombra={false} />
    <Caja p={[0, 0.4, -1.5]} s={[3, 0.8, 1.3]} c="#6f4518" />
    <Caja p={[0, 0.82, -1.5]} s={[3.1, 0.06, 1.4]} c="#8b5e34" />
    <Caja p={[0, 0.65, -2.6]} s={[1, 1.3, 0.8]} c="#9d0208" />
    <Caja p={[0, 1.5, -2.85]} s={[1, 1, 0.15]} c="#9d0208" />
    <mesh position={[3.2, 1.5, -3]}><cylinderGeometry args={[0.04, 0.04, 3, 6]} /><M c="#ccc" /></mesh>
    <Caja p={[3.7, 2.5, -3]} s={[1, 0.65, 0.03]} c="#d62828" />
    <group position={[-2.4, 2.1, -3.38]}>
      <Caja p={[0, 0, 0]} s={[1.3, 1.6, 0.06]} c="#c9a227" />
      <Caja p={[0, 0, 0.04]} s={[1.1, 1.4, 0.02]} c="#2b3a67" />
      <Caja p={[0, 0.15, 0.06]} s={[0.4, 0.5, 0.02]} c="#f2c9a0" />
      <Caja p={[0, 0.55, 0.06]} s={[0.45, 0.4, 0.02]} c="#1a1a1a" />
    </group>
    <Ventana p={[2, 2, -3.39]} s={[1.5, 1.3]} />
    {children}
  </group>
);

/** camión de mudanza (todos los guiones: «Nos mudamos un lunes y nadie nos avisó») */
export const Camion: React.FC<{p: V3; rotY?: number; f: number; avanza?: number}> = ({p, rotY = 0, f, avanza = 0}) => (
  <group position={[p[0], p[1] + Math.abs(Math.sin(f * 0.5)) * 0.03 * avanza, p[2]]} rotation={[0, rotY, 0]}>
    <Caja p={[0, 1.7, -0.6]} s={[2.4, 2.6, 4.2]} c="#f8f9fa" />
    <Caja p={[0, 1.2, 2.3]} s={[2.3, 1.8, 1.6]} c="#e63946" />
    <Ventana p={[0, 1.6, 3.11]} s={[1.6, 0.6]} />
    <Cartel p={[1.22, 2.0, -0.6]} w={3} texto="MUDANZAS" fondo="#ffd166" color="#1d3557" rotY={Math.PI / 2} />
    <Cartel p={[-1.22, 2.0, -0.6]} w={3} texto="MUDANZAS" fondo="#ffd166" color="#1d3557" rotY={-Math.PI / 2} />
    {[[-1.1, 1.8], [1.1, 1.8], [-1.1, -1.8], [1.1, -1.8]].map(([x, z], i) => (
      <mesh key={i} position={[x, 0.45, z]} rotation={[f * 0.2 * avanza, 0, Math.PI / 2]} castShadow><cylinderGeometry args={[0.45, 0.45, 0.35, 16]} /><M c="#222" /></mesh>
    ))}
  </group>
);
export const CajaCarton: React.FC<{p: V3; s?: number; r?: number}> = ({p, s = 1, r = 0}) => (
  <group position={p} scale={s} rotation={[0, r, 0]}>
    <Caja p={[0, 0.3, 0]} s={[0.8, 0.6, 0.6]} c="#c8a27a" />
    <Caja p={[0, 0.61, 0]} s={[0.1, 0.02, 0.62]} c="#e8d5b5" />
  </group>
);

export const AULA: V3 = [0, 0, -200];
/** salón de la escuela: pizarra, pupitres, ventanas de día */
export const Aula: React.FC<{children?: React.ReactNode}> = ({children}) => (
  <group position={AULA}>
    <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[10, 8]} /><M c="#e0a070" map={T.madera()} /></mesh>
    <Caja p={[0, 1.7, -4]} s={[10, 3.4, 0.2]} c="#bde0fe" sombra={false} />
    <Caja p={[-5, 1.7, 0]} s={[0.2, 3.4, 8]} c="#bde0fe" sombra={false} />
    <Caja p={[5, 1.7, 0]} s={[0.2, 3.4, 8]} c="#bde0fe" sombra={false} />
    <Caja p={[0, 1.8, -3.86]} s={[4.2, 1.6, 0.06]} c="#2d4a3e" />
    <Caja p={[0, 1.8, -3.9]} s={[4.4, 1.8, 0.04]} c="#8b5e34" />
    <Ventana p={[-3.2, 1.9, -3.88]} s={[1.3, 1.2]} />
    <Ventana p={[3.2, 1.9, -3.88]} s={[1.3, 1.2]} />
    {[-2.2, 0, 2.2].map((x) => [-0.6, 1.4].map((z) => (
      <group key={x + ',' + z} position={[x, 0, z]}>
        <Caja p={[0, 0.72, 0]} s={[1.2, 0.06, 0.7]} c="#c1793f" />
        {[-0.5, 0.5].map((dx) => [-0.28, 0.28].map((dz) => <Caja key={dx + ',' + dz} p={[dx, 0.36, dz]} s={[0.06, 0.72, 0.06]} c="#6c584c" />))}
      </group>
    )))}
    {children}
  </group>
);
/** reloj digital de mesa (muestra la hora en grande) */
export const RelojMesa: React.FC<{p: V3; hora: string}> = ({p, hora}) => (
  <group position={p}>
    <Caja p={[0, 0.12, 0]} s={[0.5, 0.24, 0.16]} c="#222" />
    <Cartel p={[0, 0.13, 0.085]} w={0.44} texto={hora} fondo="#111" color="#ff4d4d" />
  </group>
);

/** la estación del tren (episodio 3), al fondo del camino norte */
export const Estacion: React.FC<{noche?: boolean}> = ({noche}) => (
  <group position={[0, 0, -34]}>
    <Caja p={[0, 0.3, 0]} s={[14, 0.6, 3]} c="#bfb7a8" />
    <Caja p={[0, 2.0, -1.0]} s={[6, 3.4, 1.6]} c="#e9c46a" />
    <DosAguas p={[0, 3.7, -1.0]} w={6} d={1.6} h={1.0} c={C.techoRojo} />
    <Ventana p={[-1.6, 2.2, -0.18]} noche={noche} />
    <Ventana p={[1.6, 2.2, -0.18]} noche={noche} />
    {[-1.5, 1.5].map((z) => <Caja key={z} p={[0, 0.05, 3.2 + z * 0.5]} s={[30, 0.1, 0.12]} c="#6c757d" />)}
    {Array.from({length: 15}, (_, i) => <Caja key={i} p={[-14 + i * 2, 0.03, 3.2]} s={[0.3, 0.06, 2.0]} c="#7a4a24" />)}
    <Cartel p={[0, 3.0, 0.62]} w={2.6} texto="ESTACIÓN" fondo="#fff" color="#1d3557" />
  </group>
);
