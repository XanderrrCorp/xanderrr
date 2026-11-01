// Diorama 3D low-poly (código propio). Todo se calcula a partir del cuadro: nada de useFrame ni estado.
import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {useCurrentFrame} from 'remotion';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {applyPose, camDir, camPos, poseAt} from './camara';
import {CAV, PERCH, THERMO, THERMO_H} from './lugares';
import {clamp, lerp, rnd, V3, bez3, prog, E} from './anim';
import * as S from './estado';

const C = {
  bark: '#5b3a22', barkIn: '#8a5a32', wood: '#8f5f36', wax: '#d99a2b', cell: '#f0b847', cellIn: '#a8641a',
  hornetHead: '#f29a1a', hornetDark: '#2a1a0d', hornetBand: '#f6b21f', legs: '#c27417',
  bee: '#e6aa2e', beeDark: '#2b1d10', ground: '#1f4a2a', leaf: '#2f7a3a', leaf2: '#3f9a45', far: '#123522',
};
const col = (a: string, b: string, t: number) => new THREE.Color(a).lerp(new THREE.Color(b), clamp(t));

const CamRig: React.FC = () => {
  const f = useCurrentFrame();
  const {camera} = useThree();
  useLayoutEffect(() => applyPose(camera as THREE.PerspectiveCamera, f), [f, camera]);
  return null;
};

// ---------- avispón ----------
const Ico: React.FC<{r: number; s?: V3; p?: V3; c: THREE.Color | string; e?: THREE.Color | string; ei?: number; d?: number}> = ({r, s = [1, 1, 1], p = [0, 0, 0], c, e = '#000', ei = 0, d = 1}) => (
  <mesh position={p} scale={s} castShadow>
    <icosahedronGeometry args={[r, d]} />
    <meshStandardMaterial color={c} emissive={e} emissiveIntensity={ei} flatShading roughness={0.55} metalness={0.05} />
  </mesh>
);

const Wing: React.FC<{side: 1 | -1; front: boolean; open: number; f: number; flap: number}> = ({side, front, open, f, flap}) => {
  const beat = flap > 0 ? Math.sin(f * 2.7 + (front ? 0 : 0.8)) : 0;
  const rx = side * (0.12 + open * 0.55 + flap * 0.7 * beat);
  const ry = side * (front ? 0.25 : 0.45) * (1 - open * 0.6);
  return (
    <group position={[front ? 0.38 : 0.22, 0.3, side * 0.06]} rotation={[rx, ry, 0]}>
      <mesh position={[-0.55, 0, side * 0.12]} scale={[front ? 0.6 : 0.42, 1, front ? 0.17 : 0.13]}>
        <cylinderGeometry args={[1, 1, 0.01, 10]} />
        <meshStandardMaterial color="#e8eef5" transparent opacity={0.38} side={THREE.DoubleSide} depthWrite={false} roughness={0.2} />
      </mesh>
    </group>
  );
};

const Leg: React.FC<{x: number; side: 1 | -1; k: number}> = ({x, side, k}) => (
  <group position={[x, -0.12, side * 0.18]} rotation={[side * -0.9, 0, (k - 1) * -0.45]}>
    <mesh position={[0, -0.22, 0]} castShadow>
      <cylinderGeometry args={[0.035, 0.03, 0.45, 5]} />
      <meshStandardMaterial color={C.legs} flatShading />
    </mesh>
    <group position={[0, -0.44, 0]} rotation={[side * 1.1, 0, 0]}>
      <mesh position={[0, -0.2, 0]} castShadow>
        <cylinderGeometry args={[0.028, 0.02, 0.42, 5]} />
        <meshStandardMaterial color={C.hornetDark} flatShading />
      </mesh>
    </group>
  </group>
);

export const HornetModel: React.FC<{f: number; flap: number; jaws?: number; hit?: number; heat?: number; dark?: number}> = ({f, flap, jaws = 0, hit = 0, heat = 0, dark = 0}) => {
  const k = (c: string) => col(c, '#3a2a20', dark);
  const em = hit > 0.02 ? '#ffffff' : '#ff4a10';
  const ei = Math.max(hit * 0.9, heat * 0.35);
  const open = flap > 0 ? 1 : 0;
  const bands: [number, number, string][] = [[-0.3, 0.33, C.hornetBand], [-0.56, 0.37, C.hornetDark], [-0.8, 0.31, C.hornetBand], [-0.98, 0.2, C.hornetDark]];
  return (
    <group>
      <Ico r={0.3} p={[0.78, 0.05, 0]} s={[0.92, 1, 1.08]} c={k(C.hornetHead)} e={em} ei={ei} />
      <Ico r={0.14} p={[0.86, 0.1, 0.21]} s={[0.6, 1, 0.7]} c="#1d120a" d={0} />
      <Ico r={0.14} p={[0.86, 0.1, -0.21]} s={[0.6, 1, 0.7]} c="#1d120a" d={0} />
      {[1, -1].map((sd) => (
        <group key={sd} position={[1.0, -0.1, sd * 0.09]} rotation={[0, sd * (0.35 + jaws * 0.7), 0]}>
          <mesh position={[0.12, 0, 0]} castShadow>
            <boxGeometry args={[0.26, 0.07, 0.09]} />
            <meshStandardMaterial color="#3a210d" flatShading />
          </mesh>
        </group>
      ))}
      {[1, -1].map((sd) => (
        <group key={'a' + sd} position={[0.95, 0.27, sd * 0.1]} rotation={[sd * -0.35, 0, -0.55]}>
          <mesh position={[0, 0.25, 0]}>
            <cylinderGeometry args={[0.018, 0.018, 0.5, 4]} />
            <meshStandardMaterial color={C.hornetDark} />
          </mesh>
        </group>
      ))}
      <Ico r={0.29} p={[0.33, 0.05, 0]} s={[1.1, 0.95, 0.95]} c={k(C.hornetDark)} e={em} ei={ei} />
      <Ico r={0.07} p={[0.0, 0.02, 0]} s={[1.6, 1, 1]} c={k(C.hornetDark)} d={0} />
      {bands.map(([x, r, c]) => (
        <Ico key={x} r={r} p={[x, 0, 0]} s={[0.9, 0.82, 0.86]} c={k(c)} e={em} ei={ei} />
      ))}
      <mesh position={[-1.2, -0.02, 0]} rotation={[0, 0, Math.PI / 2]}>
        <coneGeometry args={[0.04, 0.2, 5]} />
        <meshStandardMaterial color="#1a0f08" />
      </mesh>
      {[0, 1, 2].map((i) => [1, -1].map((sd) => <Leg key={i + '_' + sd} x={0.48 - i * 0.16} side={sd as 1 | -1} k={i} />))}
      {[1, -1].map((sd) => (
        <group key={'w' + sd}>
          <Wing side={sd as 1 | -1} front open={open} f={f} flap={flap} />
          <Wing side={sd as 1 | -1} front={false} open={open} f={f} flap={flap} />
        </group>
      ))}
    </group>
  );
};

const Hornet: React.FC<{f: number}> = ({f}) => {
  const h = S.hornet(f);
  return (
    <group position={h.pos} rotation={[0, h.heading, 0]} scale={0.78}>
      <group rotation={[h.roll, 0, 0]}>
        <HornetModel f={f} flap={h.flap} jaws={h.jaws} hit={h.hit} heat={h.heat} dark={h.dark} />
      </group>
    </group>
  );
};

const Extras: React.FC<{f: number}> = ({f}) => {
  const {inn, out} = S.extras(f);
  if (inn <= 0.001 || out >= 0.999) return null;
  const spots: V3[] = [[5.6, 3.6, 1.8], [2.9, 4.6, 2.6], [6.4, 2.2, -0.8], [1.6, 5.6, 0.6]];
  return (
    <>
      {spots.map((p, i) => {
        const from: V3 = [p[0] + 6, p[1] + 3, p[2] + 5];
        const t = clamp(inn - i * 0.12);
        const pos = bez3(from, [p[0] + 2, p[1] + 2, p[2] + 2], p, clamp(t));
        const away: V3 = [p[0] + 3 + i, p[1] + 8, p[2] - 3];
        const q = E.in(clamp(out));
        const P: V3 = [lerp(pos[0], away[0], q), lerp(pos[1], away[1], q) + 0.08 * Math.sin(f / 5 + i), lerp(pos[2], away[2], q)];
        return (
          <group key={i} position={P} rotation={[0, Math.PI + 0.4 * Math.sin(i * 2 + f / 30), 0.1 * Math.sin(f / 7 + i)]} scale={0.78 * (t > 0.01 ? 1 : 0)}>
            <HornetModel f={f + i * 3} flap={1} />
          </group>
        );
      })}
    </>
  );
};

// ---------- abejas (instanciadas) ----------
const N = 230;
type BeeData = {rest: V3; ra: number; n: V3; R: number; d: number};
const beeData: BeeData[] = Array.from({length: N}, (_, i) => {
  const a = rnd(i, 1) * Math.PI * 2, rr = Math.sqrt(rnd(i, 2));
  const rest: V3 = i < 55
    ? [Math.cos(a) * rr * 1.35, 2.2 + Math.sin(a) * rr * 1.6, -0.36 + rnd(i, 3) * 0.12]
    : [Math.cos(a) * rr * 1.2, 2.2 + Math.sin(a) * rr * 1.5, -1.25]; // escondidas detrás del panal
  const k = i + 0.5, phi = Math.acos(1 - (2 * k) / N), th = Math.PI * (1 + Math.sqrt(5)) * k;
  const n: V3 = [Math.cos(th) * Math.sin(phi), Math.cos(phi), Math.sin(th) * Math.sin(phi)];
  return {rest, ra: rnd(i, 4) * Math.PI * 2, n, R: 1.08 + 0.32 * rnd(i, 5), d: rnd(i, 6)};
});

const basis = (x: THREE.Vector3, upHint: THREE.Vector3) => {
  const X = x.clone().normalize();
  let Z = new THREE.Vector3().crossVectors(X, upHint);
  if (Z.lengthSq() < 1e-4) Z = new THREE.Vector3().crossVectors(X, new THREE.Vector3(1, 0, 0));
  Z.normalize();
  const Y = new THREE.Vector3().crossVectors(Z, X).normalize();
  return new THREE.Matrix4().makeBasis(X, Y, Z);
};

export const beeState = (f: number, i: number) => {
  const b = beeData[i];
  const sw = S.swarm(f);
  const q = E.inOut(clamp(sw * 1.7 - b.d * 0.7));
  const tight = S.tight(f);
  const R = b.R * lerp(1, 0.86, tight);
  const vib = S.vibrate(f) * 0.03;
  const target: V3 = [CAV[0] + b.n[0] * R + vib * Math.sin(f * 2.1 + i), CAV[1] + b.n[1] * R + vib * Math.sin(f * 2.7 + i * 3), CAV[2] + b.n[2] * R + vib * Math.cos(f * 2.3 + i)];
  const mid: V3 = [(b.rest[0] + target[0]) / 2 + b.n[0] * 1.4 + Math.sin(b.d * 9) * 0.8, (b.rest[1] + target[1]) / 2 + 0.9, (b.rest[2] + target[2]) / 2 + 1.2];
  return {q, pos: q <= 0 ? b.rest : q >= 1 ? target : bez3(b.rest, mid, target, q), mid, target};
};

const Bees: React.FC<{f: number}> = ({f}) => {
  const body = useRef<THREE.InstancedMesh>(null!);
  const head = useRef<THREE.InstancedMesh>(null!);
  const wing = useRef<THREE.InstancedMesh>(null!);
  const L = useMemo(() => ({
    body: new THREE.Matrix4().makeScale(0.23, 0.145, 0.145),
    head: new THREE.Matrix4().makeTranslation(0.21, 0.015, 0).multiply(new THREE.Matrix4().makeScale(0.095, 0.095, 0.095)),
  }), []);
  useLayoutEffect(() => {
    const cd = new THREE.Vector3(...camDir(f));
    const cut = S.cutaway(f), heat = S.calor(f);
    const m = new THREE.Matrix4(), tmp = new THREE.Matrix4(), c = new THREE.Color();
    const up = new THREE.Vector3(0, 1, 0);
    for (let i = 0; i < N; i++) {
      const b = beeData[i];
      const st = beeState(f, i);
      let B: THREE.Matrix4, flying = false;
      if (st.q <= 0) {
        B = basis(new THREE.Vector3(Math.cos(b.ra), Math.sin(b.ra), 0), new THREE.Vector3(0, 0, 1));
        // en el panal: el lomo mira a la cámara (eje Y del modelo hacia +z)
        B = new THREE.Matrix4().makeBasis(new THREE.Vector3(Math.cos(b.ra), Math.sin(b.ra), 0), new THREE.Vector3(0, 0, 1), new THREE.Vector3(Math.sin(b.ra), -Math.cos(b.ra), 0));
      } else if (st.q >= 1) {
        B = basis(new THREE.Vector3(-b.n[0], -b.n[1], -b.n[2]), up);
      } else {
        const nx = bez3(b.rest, st.mid, st.target, Math.min(1, st.q + 0.03));
        B = basis(new THREE.Vector3(nx[0] - st.pos[0], nx[1] - st.pos[1], nx[2] - st.pos[2]), up);
        flying = true;
      }
      const wob = st.q <= 0 ? 0.02 * Math.sin(f / 6 + i) : 0;
      B.setPosition(st.pos[0] + wob, st.pos[1], st.pos[2]);
      // corte: se esconden las abejas del lado de la cámara para ver al avispón adentro
      const facing = b.n[0] * cd.x + b.n[1] * cd.y + b.n[2] * cd.z;
      const hide = st.q > 0.98 && facing > lerp(1.2, 0.05, cut);
      const sc = hide ? 0 : 1;
      const S0 = new THREE.Matrix4().makeScale(sc, sc, sc);
      m.copy(B).multiply(S0).multiply(L.body);
      body.current.setMatrixAt(i, m);
      tmp.copy(B).multiply(S0).multiply(L.head);
      head.current.setMatrixAt(i, tmp);
      c.set(C.bee).lerp(new THREE.Color('#ff4d14'), heat * st.q * 0.85);
      body.current.setColorAt(i, c);
      for (const sd of [1, -1]) {
        const ang = flying ? 0.6 + 0.5 * Math.sin(f * 2.9 + i) : st.q >= 1 ? 0.25 + 0.18 * Math.sin(f * 4.1 + i) * S.vibrate(f) : 0.08;
        const w = new THREE.Matrix4().makeTranslation(0.0, 0.13, sd * 0.04)
          .multiply(new THREE.Matrix4().makeRotationX(sd * ang))
          .multiply(new THREE.Matrix4().makeRotationY(sd * 0.35))
          .multiply(new THREE.Matrix4().makeTranslation(-0.12, 0, sd * 0.05))
          .multiply(new THREE.Matrix4().makeScale(0.16, 0.01, 0.07));
        tmp.copy(B).multiply(S0).multiply(w);
        wing.current.setMatrixAt(i * 2 + (sd > 0 ? 0 : 1), tmp);
      }
    }
    body.current.instanceMatrix.needsUpdate = true;
    if (body.current.instanceColor) body.current.instanceColor.needsUpdate = true;
    head.current.instanceMatrix.needsUpdate = true;
    wing.current.instanceMatrix.needsUpdate = true;
  }, [f, L]);
  return (
    <>
      <instancedMesh ref={body} args={[undefined, undefined, N]} castShadow>
        <icosahedronGeometry args={[1, 1]} />
        <meshStandardMaterial color="#ffffff" flatShading roughness={0.6} />
      </instancedMesh>
      <instancedMesh ref={head} args={[undefined, undefined, N]}>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial color={C.beeDark} flatShading />
      </instancedMesh>
      <instancedMesh ref={wing} args={[undefined, undefined, N * 2]}>
        <cylinderGeometry args={[1, 1, 1, 8]} />
        <meshStandardMaterial color="#eef4fa" transparent opacity={0.45} depthWrite={false} />
      </instancedMesh>
    </>
  );
};

/** abeja suelta (las que pican al avispón en la escena 2) */
const BeeSolo: React.FC<{pos: V3; dir: V3; f: number; s?: number}> = ({pos, dir, f, s = 1}) => {
  const B = basis(new THREE.Vector3(...dir), new THREE.Vector3(0, 1, 0));
  const q = new THREE.Quaternion().setFromRotationMatrix(B);
  return (
    <group position={pos} quaternion={q} scale={s * 0.8}>
      <mesh scale={[0.3, 0.19, 0.19]} castShadow>
        <icosahedronGeometry args={[1, 1]} />
        <meshStandardMaterial color={C.bee} flatShading />
      </mesh>
      <mesh position={[0.27, 0.02, 0]} scale={0.12}>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial color={C.beeDark} flatShading />
      </mesh>
      {[1, -1].map((sd) => (
        <group key={sd} position={[0, 0.17, sd * 0.05]} rotation={[sd * (0.6 + 0.5 * Math.sin(f * 2.9 + sd)), sd * 0.35, 0]}>
          <mesh position={[-0.15, 0, sd * 0.06]} scale={[0.2, 0.01, 0.09]}>
            <cylinderGeometry args={[1, 1, 1, 8]} />
            <meshStandardMaterial color="#eef4fa" transparent opacity={0.45} depthWrite={false} />
          </mesh>
        </group>
      ))}
    </group>
  );
};

const Attackers: React.FC<{f: number}> = ({f}) => {
  const contacts: V3[] = [[-0.3, 0.35, -0.25], [0.5, 0.38, -0.3], [0.85, 0.3, 0.25]];
  const offs: V3[] = [[-1.8, 1.4, 2.4], [1.6, 1.9, 2.2], [2.2, 0.9, -1.6]];
  return (
    <>
      {S.T.golpes.map((g, k) => {
        if (f < g - 16 || f > g + 22) return null;
        const C0: V3 = [PERCH[0] + contacts[k][0], PERCH[1] + contacts[k][1], PERCH[2] + contacts[k][2]];
        const S0: V3 = [C0[0] + offs[k][0], C0[1] + offs[k][1], C0[2] + offs[k][2]];
        let pos: V3, dir: V3;
        if (f < g) {
          const t = E.in(clamp((f - (g - 16)) / 16));
          pos = [lerp(S0[0], C0[0], t), lerp(S0[1], C0[1], t), lerp(S0[2], C0[2], t)];
          dir = [C0[0] - S0[0], C0[1] - S0[1], C0[2] - S0[2]];
        } else {
          const t = E.out(clamp((f - g) / 22));
          const back: V3 = [C0[0] + offs[k][0] * 0.7, C0[1] + offs[k][1] * 0.3 + 0.6, C0[2] + offs[k][2] * 0.7];
          pos = [lerp(C0[0], back[0], t), lerp(C0[1], back[1], t) + Math.sin(t * 9) * 0.1, lerp(C0[2], back[2], t)];
          dir = [C0[0] - back[0], 0.2, C0[2] - back[2]];
        }
        const sparks = f >= g && f < g + 10;
        return (
          <group key={k}>
            <BeeSolo pos={pos} dir={dir} f={f} s={f > g + 16 ? 1 - (f - g - 16) / 6 : 1} />
            {sparks &&
              Array.from({length: 9}, (_, j) => {
                const a = (j / 9) * Math.PI * 2, u = (f - g) / 10;
                const p: V3 = [C0[0] + Math.cos(a) * u * 0.7, C0[1] + Math.sin(a) * u * 0.7, C0[2] + 0.3];
                return (
                  <mesh key={j} position={p} scale={0.07 * (1 - u)}>
                    <octahedronGeometry args={[1, 0]} />
                    <meshBasicMaterial color="#fff6c8" />
                  </mesh>
                );
              })}
          </group>
        );
      })}
    </>
  );
};

// ---------- colmena en el tronco ----------
const R = 2.2, RI = 1.85, YB = -3.2, YT = 7.6, Y0 = 0.0, Y1 = 4.4;
const cellsPos: [number, number][] = (() => {
  const out: [number, number][] = [];
  const sx = 0.25, sy = sx * 0.866;
  for (let r = -12; r <= 12; r++)
    for (let c = -8; c <= 8; c++) {
      const x = c * sx + (r % 2 ? sx / 2 : 0), y = 2.2 + r * sy;
      if ((x / 1.5) ** 2 + ((y - 2.2) / 1.75) ** 2 < 1) out.push([x, y]);
    }
  return out;
})();

const Cells: React.FC<{alarm: number}> = ({alarm}) => {
  const ref = useRef<THREE.InstancedMesh>(null!);
  useLayoutEffect(() => {
    const m = new THREE.Matrix4();
    cellsPos.forEach(([x, y], i) => {
      m.makeRotationX(Math.PI / 2).premultiply(new THREE.Matrix4().makeTranslation(x, y, -0.5));
      ref.current.setMatrixAt(i, m);
    });
    ref.current.instanceMatrix.needsUpdate = true;
  }, []);
  return (
    <instancedMesh ref={ref} args={[undefined, undefined, cellsPos.length]} receiveShadow>
      <cylinderGeometry args={[0.122, 0.122, 0.14, 6, 1, true]} />
      <meshStandardMaterial color={C.cell} emissive="#ff2a10" emissiveIntensity={alarm * 0.8} flatShading side={THREE.DoubleSide} />
    </instancedMesh>
  );
};

const Hive: React.FC<{f: number}> = ({f}) => {
  const door = S.door(f), alarm = S.alarm(f);
  const comb = useMemo(() => {
    const sh = new THREE.Shape();
    sh.absellipse(0, 0, 1.55, 1.82, 0, Math.PI * 2, false, 0);
    return new THREE.ShapeGeometry(sh, 24);
  }, []);
  const holeA = 1.15;
  return (
    <group>
      {/* mitad de atrás del tronco */}
      <mesh position={[0, (YB + YT) / 2, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[R, R * 1.06, YT - YB, 11, 1, true, Math.PI / 2, Math.PI]} />
        <meshStandardMaterial color={C.bark} flatShading side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0, (Y0 + Y1) / 2, 0]} receiveShadow>
        <cylinderGeometry args={[RI, RI, Y1 - Y0, 11, 1, true, Math.PI / 2, Math.PI]} />
        <meshStandardMaterial color={C.barkIn} flatShading side={THREE.BackSide} />
      </mesh>
      {/* cara del corte: madera arriba y abajo del hueco, y bordes */}
      <mesh position={[0, (YB + Y0) / 2, 0.005]} receiveShadow>
        <planeGeometry args={[2 * R, Y0 - YB]} />
        <meshStandardMaterial color={C.wood} flatShading />
      </mesh>
      <mesh position={[0, (Y1 + YT) / 2, 0.005]}>
        <planeGeometry args={[2 * R, YT - Y1]} />
        <meshStandardMaterial color={C.wood} flatShading />
      </mesh>
      {[1, -1].map((sd) => (
        <mesh key={sd} position={[sd * (R + RI) / 2, (Y0 + Y1) / 2, 0.005]}>
          <planeGeometry args={[R - RI, Y1 - Y0]} />
          <meshStandardMaterial color={C.wood} />
        </mesh>
      ))}
      <mesh position={[0, Y0 + 0.001, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[RI, 12, 0, Math.PI]} />
        <meshStandardMaterial color={C.barkIn} flatShading />
      </mesh>
      <mesh position={[0, Y1 - 0.001, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <circleGeometry args={[RI, 12, Math.PI, Math.PI]} />
        <meshStandardMaterial color={C.barkIn} flatShading />
      </mesh>
      {/* panal */}
      <mesh geometry={comb} position={[0, 2.2, -0.58]} receiveShadow>
        <meshStandardMaterial color={C.cellIn} emissive="#ff2a10" emissiveIntensity={alarm * 0.5} flatShading />
      </mesh>
      <Cells alarm={alarm} />
      {/* mitad de adelante: puerta que se abre como maqueta */}
      <group position={[-R, 0, 0]} rotation={[0, -door * 2.0, 0]}>
        <group position={[R, 0, 0]}>
          <mesh position={[0, (YB + YT) / 2, 0]} castShadow>
            <cylinderGeometry args={[R, R * 1.06, YT - YB, 11, 1, true, -Math.PI / 2, Math.PI]} />
            <meshStandardMaterial color={C.bark} flatShading side={THREE.DoubleSide} />
          </mesh>
          <mesh position={[Math.sin(holeA) * (R + 0.02), 2.45, Math.cos(holeA) * (R + 0.02)]} rotation={[0, holeA, 0]}>
            <circleGeometry args={[0.24, 10]} />
            <meshBasicMaterial color="#120a04" />
          </mesh>
        </group>
      </group>
      {/* tapa de arriba */}
      <mesh position={[0, YT, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[R, 11]} />
        <meshStandardMaterial color={C.wood} flatShading />
      </mesh>
      {/* rama donde se posa el avispón */}
      <mesh position={[(R + 6.4) / 2, 1.3, PERCH[2]]} rotation={[0, 0, Math.PI / 2 + 0.04]} castShadow receiveShadow>
        <cylinderGeometry args={[0.2, 0.28, 6.4 - R + 0.4, 6]} />
        <meshStandardMaterial color={C.bark} flatShading />
      </mesh>
      {[[5.6, 1.55, 0.6, 0.5], [6.3, 1.2, 0.0, -0.4], [4.9, 1.05, -0.3, 0.9]].map(([x, y, z, r], i) => (
        <mesh key={i} position={[x, y, z]} rotation={[0.3, r, 0.5]} scale={[0.55, 0.06, 0.28]} castShadow>
          <icosahedronGeometry args={[1, 0]} />
          <meshStandardMaterial color={i % 2 ? C.leaf : C.leaf2} flatShading />
        </mesh>
      ))}
    </group>
  );
};

// ---------- escenario ----------
const Scenery: React.FC<{f: number; heat: number}> = ({f, heat}) => {
  const trees = useMemo(() => Array.from({length: 16}, (_, i) => ({
    x: (rnd(i, 7) - 0.5) * 60, z: -14 - rnd(i, 8) * 26, h: 12 + rnd(i, 9) * 10, r: 3 + rnd(i, 10) * 3,
  })), []);
  const bushes = useMemo(() => Array.from({length: 26}, (_, i) => {
    const a = rnd(i, 11) * Math.PI * 2, d = 3 + rnd(i, 12) * 11;
    return {p: [Math.cos(a) * d, YB + 0.3, Math.sin(a) * d - 2] as V3, s: 0.6 + rnd(i, 13) * 1.4, c: i % 3 ? C.leaf : C.leaf2};
  }), []);
  return (
    <group>
      <mesh position={[0, YB, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[60, 24]} />
        <meshStandardMaterial color={col(C.ground, '#4a2a12', heat * 0.5)} flatShading />
      </mesh>
      {trees.map((t, i) => (
        <group key={i} position={[t.x, YB, t.z]}>
          <mesh position={[0, t.h / 2, 0]}>
            <cylinderGeometry args={[0.5, 0.8, t.h, 6]} />
            <meshStandardMaterial color="#2a1c12" flatShading />
          </mesh>
          <mesh position={[0, t.h, 0]} scale={[t.r, t.r * 0.8, t.r]}>
            <icosahedronGeometry args={[1, 0]} />
            <meshStandardMaterial color={col(C.far, '#3a1608', heat * 0.6)} flatShading />
          </mesh>
        </group>
      ))}
      {bushes.map((b, i) => (
        <mesh key={i} position={b.p} scale={[b.s, b.s * 0.7, b.s]} castShadow>
          <icosahedronGeometry args={[1, 0]} />
          <meshStandardMaterial color={b.c} flatShading />
        </mesh>
      ))}
      {/* polvo flotando para dar profundidad */}
      {Array.from({length: 70}, (_, i) => {
        const p: V3 = [(rnd(i, 14) - 0.5) * 22, -2 + rnd(i, 15) * 11 + Math.sin(f / 40 + i) * 0.4, (rnd(i, 16) - 0.3) * 16];
        p[0] += Math.sin(f / 60 + i * 2) * 0.6;
        return (
          <mesh key={i} position={p} scale={0.03 + rnd(i, 17) * 0.04}>
            <icosahedronGeometry args={[1, 0]} />
            <meshBasicMaterial color={heat > 0.3 ? '#ffb070' : '#fff3c4'} transparent opacity={0.55} />
          </mesh>
        );
      })}
    </group>
  );
};

const Thumb: React.FC<{f: number}> = ({f}) => {
  const s = S.thumb(f);
  if (s <= 0.001) return null;
  const y = lerp(-4.5, 0, clamp(s, 0, 1.2));
  return (
    <group position={[PERCH[0] + 0.05, PERCH[1] - 1.2 + y, PERCH[2] + 1.25]} rotation={[0.15, 0, 0.05]}>
      <mesh rotation={[0, 0, Math.PI / 2]} castShadow>
        <capsuleGeometry args={[0.42, 1.35, 6, 12]} />
        <meshStandardMaterial color="#e7b08a" flatShading roughness={0.7} />
      </mesh>
      <mesh position={[0.78, 0.3, 0]} rotation={[0, 0, -0.35]} scale={[0.42, 0.06, 0.34]}>
        <icosahedronGeometry args={[1, 1]} />
        <meshStandardMaterial color="#f4cdb5" flatShading />
      </mesh>
      <mesh position={[-1.2, -0.25, 0]} scale={[0.9, 0.75, 0.7]}>
        <icosahedronGeometry args={[1, 1]} />
        <meshStandardMaterial color="#dda07c" flatShading />
      </mesh>
    </group>
  );
};

const Ruler: React.FC<{f: number}> = ({f}) => {
  const r = S.ruler(f);
  if (r <= 0.001) return null;
  const L = 1.95;
  return (
    <group position={[PERCH[0] - L / 2 + 0.1, PERCH[1] - 0.62, PERCH[2] + 0.7]}>
      <mesh position={[(L * r) / 2, 0, 0]} scale={[L * r, 1, 1]}>
        <boxGeometry args={[1, 0.07, 0.22]} />
        <meshStandardMaterial color="#ffd23f" emissive="#ffd23f" emissiveIntensity={0.25} />
      </mesh>
      {Array.from({length: 11}, (_, i) => (i / 10 <= r ? (
        <mesh key={i} position={[(i / 10) * L, 0.09 + (i % 5 === 0 ? 0.05 : 0), 0]}>
          <boxGeometry args={[0.025, i % 5 === 0 ? 0.24 : 0.14, 0.03]} />
          <meshStandardMaterial color="#ffd23f" />
        </mesh>
      ) : null))}
    </group>
  );
};

const Thermometer: React.FC<{f: number}> = ({f}) => {
  const s = S.thermoShow(f);
  if (s <= 0.001) return null;
  const heat = S.calor(f);
  const H = THERMO_H, liquid = lerp(0.9, H - 0.45, heat);
  return (
    <group position={THERMO} scale={clamp(s, 0, 1.3)}>
      <mesh position={[0, 0.12, 0]} castShadow>
        <boxGeometry args={[1.0, 0.24, 0.7]} />
        <meshStandardMaterial color="#2c3440" flatShading />
      </mesh>
      <mesh position={[0, 0.55, 0]}>
        <icosahedronGeometry args={[0.32, 1]} />
        <meshStandardMaterial color="#e5341c" emissive="#e5341c" emissiveIntensity={0.4} flatShading />
      </mesh>
      <mesh position={[0, 0.55 + liquid / 2, 0]}>
        <cylinderGeometry args={[0.1, 0.1, liquid, 8]} />
        <meshStandardMaterial color="#e5341c" emissive="#ff3a10" emissiveIntensity={0.3 + heat * 0.5} />
      </mesh>
      <mesh position={[0, 0.55 + H / 2, 0]}>
        <cylinderGeometry args={[0.19, 0.19, H, 12, 1, true]} />
        <meshStandardMaterial color="#dff1ff" transparent opacity={0.3} depthWrite={false} />
      </mesh>
      {Array.from({length: 12}, (_, i) => (
        <mesh key={i} position={[0.24, 0.55 + 0.9 + (i / 11) * (H - 1.35), 0.0]}>
          <boxGeometry args={[i % 5 === 0 ? 0.18 : 0.1, 0.025, 0.03]} />
          <meshStandardMaterial color="#ffffff" />
        </mesh>
      ))}
    </group>
  );
};

const Rings: React.FC<{f: number}> = ({f}) => {
  const v = S.vibrate(f) * (1 - S.cutaway(f) * 0.4);
  if (v <= 0.01) return null;
  const cp = camPos(poseAt(f));
  const q = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().lookAt(new THREE.Vector3(...cp), new THREE.Vector3(...CAV), new THREE.Vector3(0, 1, 0)));
  return (
    <>
      {[0, 1, 2].map((k) => {
        const a = ((f + k * 9) % 27) / 27;
        return (
          <mesh key={k} position={CAV} quaternion={q} scale={1.9 + a * 1.3}>
            <torusGeometry args={[1, 0.012, 4, 48]} />
            <meshBasicMaterial color="#fff2b0" transparent opacity={(1 - a) * 0.55 * v} depthWrite={false} />
          </mesh>
        );
      })}
    </>
  );
};

const Embers: React.FC<{f: number}> = ({f}) => {
  const h = S.calor(f);
  if (h <= 0.02) return null;
  return (
    <>
      {Array.from({length: 46}, (_, i) => {
        const u = ((f + rnd(i, 18) * 50) % 50) / 50;
        const p: V3 = [CAV[0] + (rnd(i, 19) - 0.5) * 3.4 + Math.sin(u * 6 + i) * 0.15, CAV[1] - 1.2 + u * 3.6, CAV[2] + (rnd(i, 20) - 0.5) * 2.4];
        return (
          <mesh key={i} position={p} scale={0.05 * (1 - u * 0.5)}>
            <icosahedronGeometry args={[1, 0]} />
            <meshBasicMaterial color={u < 0.5 ? '#ffd27a' : '#ff6a2a'} transparent opacity={h * Math.sin(u * Math.PI)} depthWrite={false} />
          </mesh>
        );
      })}
    </>
  );
};

export const World: React.FC = () => {
  const f = useCurrentFrame();
  const heat = S.calor(f);
  return (
    <>
      <CamRig />
      <hemisphereLight args={['#e8f6ff', '#3b4a2a', 1.0]} />
      <ambientLight intensity={0.35} />
      <directionalLight position={[7, 12, 9]} intensity={2.4} castShadow shadow-mapSize={[1024, 1024]}
        shadow-camera-left={-12} shadow-camera-right={12} shadow-camera-top={12} shadow-camera-bottom={-12} shadow-bias={-0.0004} />
      <directionalLight position={[-8, 4, -6]} intensity={0.6} color="#9fd0ff" />
      <pointLight position={[CAV[0], CAV[1], CAV[2] + 1.5]} intensity={heat * 25} distance={9} color="#ff6a20" />
      <Scenery f={f} heat={heat} />
      <Hive f={f} />
      <Bees f={f} />
      <Hornet f={f} />
      <Extras f={f} />
      <Attackers f={f} />
      <Thumb f={f} />
      <Ruler f={f} />
      <Thermometer f={f} />
      <Rings f={f} />
      <Embers f={f} />
    </>
  );
};
