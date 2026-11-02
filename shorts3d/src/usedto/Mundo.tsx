// El set y el diorama: almacén de Nueva York de 1850 (ladrillo, azulejo verde azulado, madera y latón) y, sobre una
// base de madera oscura con el nombre del canal grabado, el hueco del ascensor con su mecanismo. Al lado, en la
// misma repisa, el ascensor moderno. Materiales físicos + reflejos de entorno + posproceso.
import React, {useEffect, useLayoutEffect, useMemo, useState} from 'react';
import {continueRender, delayRender, useCurrentFrame} from 'remotion';
import {useThree} from '@react-three/fiber';
import {RoundedBox} from '@react-three/drei';
import {EffectComposer, N8AO, DepthOfField, Bloom, ToneMapping, Vignette} from '@react-three/postprocessing';
import {ToneMappingMode} from 'postprocessing';
import * as THREE from 'three';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';
import {aplicarCamara, camaraEn} from './planos';
import {estado, M, V3} from './estado';
import {SPEC} from './spec';
import {ladrillo, azulejo, madera, placa} from './texturas';
import {fuenteLista} from './fuente';
import {rnd, clamp} from '../anim';

const C = SPEC.color;
// ---------- materiales ----------
const Laton: React.FC<{rough?: number}> = ({rough = 0.28}) => <meshPhysicalMaterial color={C.oro} metalness={1} roughness={rough} clearcoat={0.4} clearcoatRoughness={0.2} />;
const Acero: React.FC<{rough?: number}> = ({rough = 0.18}) => <meshPhysicalMaterial color={C.acero} metalness={1} roughness={rough} />;
const Madera: React.FC<{clara?: boolean}> = ({clara}) => <meshPhysicalMaterial map={madera(clara)} roughness={0.55} clearcoat={0.35} clearcoatRoughness={0.35} />;

const Camara: React.FC = () => {
  const f = useCurrentFrame();
  const {camera} = useThree();
  useLayoutEffect(() => aplicarCamara(camera as THREE.PerspectiveCamera, f), [f, camera]);
  return null;
};
/** reflejos de entorno sin bajar ningún HDRI: una habitación generada y filtrada (PMREM) */
const Entorno: React.FC = () => {
  const {gl, scene} = useThree();
  useEffect(() => {
    const pm = new THREE.PMREMGenerator(gl);
    const env = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = env;
    (scene as unknown as {environmentIntensity: number}).environmentIntensity = 0.9;
    return () => { env.dispose(); pm.dispose(); };
  }, [gl, scene]);
  return null;
};

// ---------- el set ----------
const Set: React.FC = () => (
  <group>
    {/* mesa larga de madera */}
    <mesh position={[1.45, -0.05, 0.3]} receiveShadow><boxGeometry args={[9, 0.1, 4]} /><Madera clara /></mesh>
    {/* pared: azulejo abajo, ladrillo arriba, moldura de madera */}
    <mesh position={[1.4, 0.9, -2.1]} receiveShadow><planeGeometry args={[14, 2.0]} /><meshPhysicalMaterial map={azulejo()} roughness={0.18} clearcoat={0.8} /></mesh>
    <mesh position={[1.4, 4.4, -2.1]} receiveShadow><planeGeometry args={[14, 5.0]} /><meshStandardMaterial map={ladrillo()} roughness={0.9} /></mesh>
    <mesh position={[1.4, 1.93, -2.05]} castShadow><boxGeometry args={[14, 0.1, 0.08]} /><Madera /></mesh>
    {/* vigas */}
    {[-1.5, 1.4, 4.3].map((x) => <mesh key={x} position={[x, 5.6, -0.4]} castShadow><boxGeometry args={[0.25, 0.3, 5]} /><Madera /></mesh>)}
    {/* repisa del fondo con frascos de ámbar (bokeh cálido detrás) */}
    <mesh position={[1.6, 2.9, -1.9]} castShadow><boxGeometry args={[6, 0.06, 0.35]} /><Madera /></mesh>
    {Array.from({length: 9}, (_, i) => (
      <mesh key={i} position={[-1.0 + i * 0.62 + rnd(i, 1) * 0.15, 3.1 + rnd(i, 2) * 0.05, -1.85]} castShadow>
        <cylinderGeometry args={[0.08, 0.09, 0.34 + rnd(i, 3) * 0.12, 20]} />
        <meshPhysicalMaterial color={i % 3 ? C.ambar : '#2f6b4f'} roughness={0.08} metalness={0} transparent opacity={0.75} clearcoat={1} />
      </mesh>
    ))}
    {/* lámpara de latón en la pared, con bombilla que brilla (bloom) */}
    <group position={[-2.2, 3.6, -1.95]}>
      <mesh rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.03, 0.03, 0.3, 12]} /><Laton /></mesh>
      <mesh position={[0, -0.05, 0.3]}><sphereGeometry args={[0.07, 24, 16]} /><meshBasicMaterial color="#ffd9a0" toneMapped={false} /></mesh>
      <pointLight position={[0, -0.05, 0.38]} intensity={2.5} distance={4} color="#ffbe7a" />
    </group>
  </group>
);

// ---------- piezas del diorama ----------
const Base: React.FC<{x: number; ancho: number}> = ({x, ancho}) => {
  const [lista, setLista] = useState(false);
  useEffect(() => { const h = delayRender('placa grabada'); fuenteLista.then(() => { setLista(true); continueRender(h); }); }, []);
  return (
    <group position={[x, 0, 0]}>
      <RoundedBox args={[ancho, M.baseTop, 1.0]} radius={0.035} smoothness={4} position={[0, M.baseTop / 2, 0]} castShadow receiveShadow><Madera /></RoundedBox>
      {lista && (
        <mesh position={[0, M.baseTop / 2, 0.502]}>
          <planeGeometry args={[ancho * 0.8, ancho * 0.1]} />
          <meshPhysicalMaterial map={placa(SPEC.canal)} roughness={0.4} metalness={0.2} clearcoat={0.5} />
        </mesh>
      )}
    </group>
  );
};

const Riel: React.FC<{lado: number; dientes: boolean}> = ({lado, dientes}) => {
  const h = M.rielTop - M.baseTop;
  const n = Math.floor(h / M.dientePaso);
  return (
    <group position={[lado * (M.rielX + 0.05), 0, 0]}>
      <mesh position={[0, M.baseTop + h / 2, 0]} castShadow receiveShadow><boxGeometry args={[0.08, h, 0.1]} /><Madera /></mesh>
      {dientes && (
        <group position={[-lado * 0.05, 0, 0]}>
          <mesh position={[0, M.baseTop + h / 2, 0]} castShadow><boxGeometry args={[0.012, h, 0.06]} /><Acero rough={0.3} /></mesh>
          {Array.from({length: n}, (_, i) => (
            <mesh key={i} position={[-lado * 0.012, M.baseTop + i * M.dientePaso + 0.02, 0]} rotation={[0, 0, lado * Math.PI / 2]} castShadow>
              <coneGeometry args={[0.011, 0.022, 4]} /><Acero rough={0.25} />
            </mesh>
          ))}
        </group>
      )}
    </group>
  );
};

/** cuerda o cable entre dos puntos, con flojedad opcional (curva) */
const Soga: React.FC<{a: V3; b: V3; r: number; tipo: 'canamo' | 'alambre'; flojo?: number; fase?: number}> = ({a, b, r, tipo, flojo = 0, fase = 0}) => {
  const geo = useMemo(() => {
    const pts = Array.from({length: 12}, (_, i) => {
      const t = i / 11;
      const p = new THREE.Vector3().lerpVectors(new THREE.Vector3(...a), new THREE.Vector3(...b), t);
      p.x += Math.sin(t * Math.PI) * flojo * 0.5 + Math.sin(t * 9 + fase) * flojo * 0.12;
      p.z += Math.sin(t * Math.PI * 2 + fase) * flojo * 0.15;
      return p;
    });
    return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 40, r, 10, false);
  }, [a, b, r, flojo, fase]);
  return (
    <mesh geometry={geo} castShadow>
      {tipo === 'canamo' ? <meshPhysicalMaterial color="#b8925a" roughness={0.9} sheen={1} sheenColor="#e8c890" /> : <meshPhysicalMaterial color="#e3e8ee" metalness={0.85} roughness={0.32} />}
    </mesh>
  );
};
/** fibras rotas que asoman donde la cuerda se gasta */
const Fibras: React.FC<{y: number; cuanto: number; tipo: 'canamo' | 'alambre'}> = ({y, cuanto, tipo}) => (
  <group position={[0, y, 0]}>
    {Array.from({length: 14}, (_, i) => {
      const vis = cuanto * 14 > i;
      if (!vis) return null;
      const ang = rnd(i, 1) * Math.PI * 2, largo = 0.012 + rnd(i, 2) * 0.03 * cuanto;
      return (
        <mesh key={i} position={[Math.cos(ang) * 0.02, (rnd(i, 3) - 0.5) * 0.08, Math.sin(ang) * 0.02]} rotation={[Math.sin(ang) * 1.2, 0, -Math.cos(ang) * 1.2]}>
          <cylinderGeometry args={[0.0012, 0.0006, largo, 4]} />
          {tipo === 'canamo' ? <meshStandardMaterial color="#d9b77c" roughness={1} /> : <meshStandardMaterial color="#e8edf2" metalness={1} roughness={0.25} />}
        </mesh>
      );
    })}
  </group>
);

const Cabina: React.FC<{y: number; s: ReturnType<typeof estado>; f: number}> = ({y, s, f}) => {
  const abre = s.muelleAbierto;
  return (
    <group position={[0, y, 0]}>
      <RoundedBox args={[0.82, 0.05, 0.62]} radius={0.01} position={[0, 0.025, 0]} castShadow receiveShadow><Madera clara /></RoundedBox>
      {[[-0.38, -0.28], [0.38, -0.28], [-0.38, 0.28], [0.38, 0.28]].map(([x, z], i) => (
        <mesh key={i} position={[x, 0.4, z]} castShadow><cylinderGeometry args={[0.014, 0.014, 0.76, 12]} /><Laton /></mesh>
      ))}
      {[0.32, 0.55].map((yy) => (
        <group key={yy}>
          <mesh position={[0, yy, -0.28]} rotation={[0, 0, Math.PI / 2]} castShadow><cylinderGeometry args={[0.01, 0.01, 0.76, 10]} /><Laton /></mesh>
          <mesh position={[-0.38, yy, 0]} rotation={[Math.PI / 2, 0, 0]} castShadow><cylinderGeometry args={[0.01, 0.01, 0.56, 10]} /><Laton /></mesh>
          <mesh position={[0.38, yy, 0]} rotation={[Math.PI / 2, 0, 0]} castShadow><cylinderGeometry args={[0.01, 0.01, 0.56, 10]} /><Laton /></mesh>
        </group>
      ))}
      {/* travesaño de arriba, donde se ata la cuerda */}
      <RoundedBox args={[0.84, 0.06, 0.12]} radius={0.012} position={[0, 0.78, 0]} castShadow><Madera /></RoundedBox>
      {/* freno de Otis: ballesta de acero y uñas que salen hacia los dientes */}
      {s.otis && [-1, 1].map((l) => (
        <group key={l} position={[0, 0.83, 0]} rotation={[0, 0, l * (-0.32 + abre * 0.32)]}>
          <mesh position={[l * 0.21, 0, 0]} castShadow><boxGeometry args={[0.42, 0.016, 0.07]} /><Acero /></mesh>
          <mesh position={[l * (0.42 + abre * 0.04), 0, 0]} castShadow><boxGeometry args={[0.06 + abre * 0.05, 0.03, 0.05]} /><Acero rough={0.35} /></mesh>
        </group>
      ))}
      {s.sombrero && (
        <group position={[0.12, 0.05, 0.05]} rotation={[0, 0.4, 0]}>
          <mesh position={[0, 0.005, 0]} castShadow><cylinderGeometry args={[0.1, 0.1, 0.01, 32]} /><meshPhysicalMaterial color="#141414" roughness={0.5} sheen={1} /></mesh>
          <mesh position={[0, 0.07, 0]} castShadow><cylinderGeometry args={[0.058, 0.062, 0.13, 32]} /><meshPhysicalMaterial color="#141414" roughness={0.45} sheen={1} /></mesh>
          <mesh position={[0, 0.02, 0]}><cylinderGeometry args={[0.063, 0.063, 0.02, 32]} /><meshStandardMaterial color={C.rojo} /></mesh>
        </group>
      )}
    </group>
  );
};

const Regulador: React.FC<{giro: number; bolas: number}> = ({giro, bolas}) => {
  const ang = 0.35 + clamp(bolas) * 0.85;
  return (
    <group position={[-0.38, 3.45, 0]}>
      <mesh position={[0, 0.17, 0]} castShadow><cylinderGeometry args={[0.012, 0.012, 0.34, 12]} /><Acero /></mesh>
      <group position={[0, 0.3, 0]} rotation={[0, giro, 0]}>
        {[-1, 1].map((l) => (
          <group key={l} rotation={[0, 0, l * ang]}>
            <mesh position={[0, -0.09, 0]} castShadow><cylinderGeometry args={[0.006, 0.006, 0.18, 8]} /><Laton /></mesh>
            <mesh position={[0, -0.19, 0]} castShadow><sphereGeometry args={[0.035, 32, 24]} /><Laton rough={0.15} /></mesh>
          </group>
        ))}
      </group>
    </group>
  );
};

const Banderines: React.FC<{f: number}> = ({f}) => (
  <group position={[0, 3.6, 0.15]}>
    {Array.from({length: 11}, (_, i) => {
      const x = -1.0 + i * 0.2, y = -0.12 * Math.sin((i / 10) * Math.PI);
      return (
        <mesh key={i} position={[x, y - 0.06, 0]} rotation={[Math.sin(f / 9 + i) * 0.15, 0, Math.PI]}>
          <coneGeometry args={[0.05, 0.11, 3]} />
          <meshStandardMaterial color={[C.rojo, C.blanco, '#1f3f8f'][i % 3]} roughness={0.8} side={THREE.DoubleSide} />
        </mesh>
      );
    })}
  </group>
);

const DioramaViejo: React.FC<{f: number}> = ({f}) => {
  const s = estado(f);
  const tipo = s.cuerda as 'canamo' | 'alambre';
  const r = tipo === 'canamo' ? 0.022 : 0.012;
  const topeCoche: V3 = [0, s.y + 0.81, 0];
  const polea: V3 = [0, M.poleaY - 0.12, 0];
  const yRotura = 3.0;
  // hacha que corta la cuerda en la feria de 1854
  const hacha = s.v === 'otis_feria' ? clamp(1 - s.retroceso) : 0;
  return (
    <group>
      <Base x={0} ancho={2.4} />
      <Riel lado={-1} dientes={s.otis} />
      <Riel lado={1} dientes={s.otis} />
      <RoundedBox args={[1.25, 0.1, 0.16]} radius={0.015} position={[0, M.rielTop + 0.05, 0]} castShadow><Madera /></RoundedBox>
      {/* polea de latón */}
      <group position={[0, M.poleaY, 0]} rotation={[0, 0, (M.arriba - s.y) * 8]}>
        <mesh castShadow><torusGeometry args={[0.11, 0.022, 16, 48]} /><Laton rough={0.2} /></mesh>
        <mesh rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.03, 0.03, 0.06, 16]} /><Acero /></mesh>
        {[0, 1, 2].map((k) => <mesh key={k} rotation={[0, 0, (k * Math.PI) / 3]}><boxGeometry args={[0.2, 0.012, 0.012]} /><Laton /></mesh>)}
      </group>
      <mesh position={[0, M.poleaY, -0.07]} castShadow><boxGeometry args={[0.05, 0.3, 0.02]} /><Madera /></mesh>
      {/* tambor del motor, sobre la base */}
      <group position={[0.92, 0.5, -0.12]}>
        <mesh rotation={[Math.PI / 2, 0, s.tambor]} castShadow><cylinderGeometry args={[0.13, 0.13, 0.22, 32]} /><Laton rough={0.35} /></mesh>
        {[-1, 1].map((l) => <mesh key={l} position={[0, -0.11, l * 0.13]} castShadow><boxGeometry args={[0.06, 0.22, 0.03]} /><Madera /></mesh>)}
      </group>
      <Soga a={[0.11, M.poleaY, 0]} b={[0.92, M.poleaY, -0.12]} r={r} tipo={tipo} />
      <Soga a={[0.92, M.poleaY, -0.12]} b={[0.92, 0.63, -0.12]} r={r} tipo={tipo} />
      <mesh position={[0.92, M.poleaY, -0.12]} rotation={[Math.PI / 2, 0, 0]} castShadow><cylinderGeometry args={[0.045, 0.045, 0.05, 24]} /><Laton /></mesh>
      {/* la cuerda principal: entera, o rota en dos (arriba retrocede, abajo cae floja con la cabina) */}
      {!s.roto ? (
        <>
          <Soga a={polea} b={topeCoche} r={r} tipo={tipo} />
          {s.desgaste > 0 && <Fibras y={yRotura} cuanto={s.desgaste} tipo={tipo} />}
        </>
      ) : (
        <>
          <Soga a={polea} b={[0, yRotura + 0.25 * s.retroceso, 0]} r={r} tipo={tipo} flojo={0.06 * (1 - s.retroceso)} fase={f / 2} />
          <Soga a={topeCoche} b={[0.08, Math.min(topeCoche[1] + 0.5, yRotura - 0.05), 0.05]} r={r} tipo={tipo} flojo={0.12} fase={f / 3} />
        </>
      )}
      {hacha > 0 && (
        <group position={[0.35 - hacha * 0.33, yRotura, 0.05]} rotation={[0, 0, 0.2]}>
          <mesh castShadow><boxGeometry args={[0.18, 0.12, 0.008]} /><Acero rough={0.12} /></mesh>
          <mesh position={[0.2, 0, 0]} rotation={[0, 0, Math.PI / 2]} castShadow><cylinderGeometry args={[0.012, 0.012, 0.3, 10]} /><Madera clara /></mesh>
        </group>
      )}
      <Cabina y={s.y} s={s} f={f} />
      {s.mostrarRegulador && <Regulador giro={s.regulador} bolas={s.bolas} />}
      {s.sombrero && <Banderines f={f} />}
    </group>
  );
};

const DioramaModerno: React.FC<{f: number}> = ({f}) => {
  const s = estado(f);
  const yC = 1.35;
  return (
    <group position={[M.moderno, 0, 0]}>
      <Base x={0} ancho={1.7} />
      {[-1, 1].map((l) => <mesh key={l} position={[l * 0.52, 1.8, -0.2]} castShadow><boxGeometry args={[0.05, 3.05, 0.05]} /><Acero rough={0.35} /></mesh>)}
      <mesh position={[0, 3.36, -0.1]} castShadow><boxGeometry args={[1.15, 0.08, 0.3]} /><Acero rough={0.3} /></mesh>
      <mesh position={[0, 3.5, 0]} rotation={[0, Math.PI / 2, 0]} castShadow><cylinderGeometry args={[0.14, 0.14, 0.34, 40]} /><Acero rough={0.15} /></mesh>
      {/* cabina moderna: acero cepillado y vidrio */}
      <group position={[0, yC, 0]}>
        <RoundedBox args={[0.8, 0.95, 0.6]} radius={0.03} smoothness={4} position={[0, 0.48, 0]} castShadow>
          <meshPhysicalMaterial color="#b7bec6" metalness={1} roughness={0.35} />
        </RoundedBox>
        <mesh position={[0, 0.5, 0.305]}><planeGeometry args={[0.5, 0.75]} /><meshPhysicalMaterial color="#9fd3cf" roughness={0.05} transparent opacity={0.35} clearcoat={1} /></mesh>
        <mesh position={[0, 0.93, 0.31]}><boxGeometry args={[0.24, 0.05, 0.005]} /><meshBasicMaterial color="#ffb347" toneMapped={false} /></mesh>
      </group>
      {/* cuatro cables: cada uno puede solo con la cabina; se cortan tres y no pasa nada */}
      {[-0.09, -0.03, 0.03, 0.09].map((z, i) => (
        i < s.cortes
          ? <Soga key={i} a={[0, 3.36, z]} b={[0.02, 3.0 + i * 0.03, z]} r={0.007} tipo="alambre" flojo={0.05} fase={f / 2 + i} />
          : <Soga key={i} a={[0, 3.36, z]} b={[0, yC + 0.96, z]} r={0.007} tipo="alambre" />
      ))}
    </group>
  );
};

const Luces: React.FC = () => (
  <>
    {/* llave cálida (~3500 K) arriba a la izquierda, grande y suave */}
    <spotLight position={[-3.5, 6.5, 4]} angle={0.55} penumbra={0.9} intensity={85} decay={1.6} color={SPEC.luz.llave} castShadow shadow-mapSize={[1024, 1024]} shadow-bias={-0.0004} shadow-radius={6} />
    {/* relleno frío y sutil a la derecha */}
    <directionalLight position={[5, 3, 3]} intensity={0.45} color={SPEC.luz.relleno} />
    {/* contraluz fuerte: el latón y el acero brillan contra el fondo */}
    <spotLight position={[1.5, 5, -3.5]} angle={0.6} penumbra={0.8} intensity={45} decay={1.6} color={SPEC.luz.contra} />
    <spotLight position={[-1.5, 4, -3.0]} angle={0.5} penumbra={0.8} intensity={22} decay={1.6} color={SPEC.luz.contra} />
    <hemisphereLight args={['#4a6e6a', '#2a1a12', 0.25]} />
  </>
);

const Post: React.FC = () => {
  const f = useCurrentFrame();
  const foco = camaraEn(f).foco;
  const target = useMemo(() => new THREE.Vector3(), []);
  target.set(...foco);
  return (
    <EffectComposer multisampling={2}>
      <N8AO aoRadius={0.35} intensity={2.2} distanceFalloff={0.6} quality="medium" halfRes />
      <DepthOfField target={target} focalLength={0.012} bokehScale={6} />
      <Bloom intensity={0.35} luminanceThreshold={0.85} luminanceSmoothing={0.2} mipmapBlur />
      <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
      <Vignette offset={0.3} darkness={0.45} />
    </EffectComposer>
  );
};

export const Mundo: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <>
      <Camara />
      <Entorno />
      <color attach="background" args={['#0d1a1a']} />
      <fog attach="fog" args={['#0d1a1a', 9, 22]} />
      <Luces />
      <Set />
      <DioramaViejo f={f} />
      <DioramaModerno f={f} />
      <Post />
    </>
  );
};
