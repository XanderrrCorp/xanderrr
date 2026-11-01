// Felino grande low-poly (jaguar / leopardo / pantera): el mismo modelo, solo cambia el pelaje.
// Mira hacia +x. Mide ~3,2 de largo y ~2,2 de alto. Todo depende de las props (función pura del cuadro).
import React, {useLayoutEffect, useMemo, useRef} from 'react';
import * as THREE from 'three';
import {clamp, lerp, rnd, V3} from '../anim';

export type FelinoProps = {
  coat: string;            // color del pelaje
  spots: 'jaguar' | 'leopardo';
  spotBase: string;        // color de las manchas cuando se ven
  reveal?: number;         // 0..1: cuánto se ven las manchas en todo el cuerpo
  sweepX?: number | null;  // x local de la franja de luz que revela manchas
  walk?: number;           // fase de la caminata (radianes)
  walkAmt?: number;        // 0 = quieto, 1 = caminando
  yaw?: number; pitch?: number; jaw?: number; eyes?: number; tail?: number;
};

type Spot = {p: V3; n: V3; s: number};
const ellipsoid = (c: V3, r: V3, count: number, seed: number, s0: number, s1: number, minY = -0.3, out: Spot[] = []) => {
  let k = 0, tries = 0;
  while (k < count && tries < count * 40) {
    tries++;
    const u = rnd(seed * 1000 + tries, 1) * 2 - 1, th = rnd(seed * 1000 + tries, 2) * Math.PI * 2;
    const q = Math.sqrt(1 - u * u);
    const n: V3 = [q * Math.cos(th), u, q * Math.sin(th)];
    if (n[1] < minY) continue;
    const p: V3 = [c[0] + r[0] * n[0], c[1] + r[1] * n[1], c[2] + r[2] * n[2]];
    if (out.some((o) => Math.hypot(o.p[0] - p[0], o.p[1] - p[1], o.p[2] - p[2]) < s1 * 2.1)) continue;
    const nn: V3 = [n[0] / r[0], n[1] / r[1], n[2] / r[2]];
    const L = Math.hypot(...nn);
    out.push({p, n: [nn[0] / L, nn[1] / L, nn[2] / L], s: lerp(s0, s1, rnd(seed * 1000 + tries, 3))});
    k++;
  }
  return out;
};
const SPOTS = (big: boolean) => {
  const a = big ? 0.1 : 0.075, b = big ? 0.13 : 0.1;
  const out: Spot[] = [];
  ellipsoid([0, 1.3, 0], [1.35, 0.46, 0.42], big ? 40 : 54, 1, a, b, -0.3, out);
  ellipsoid([0.9, 1.38, 0], [0.5, 0.52, 0.44], big ? 9 : 12, 2, a * 0.8, b * 0.8, -0.1, out);
  ellipsoid([-0.95, 1.36, 0], [0.5, 0.5, 0.44], big ? 11 : 14, 3, a, b, -0.2, out);
  return out;
};
const SP = {jaguar: SPOTS(true), leopardo: SPOTS(false)};

const mat = (c: string | THREE.Color, extra: object = {}) => <meshStandardMaterial color={c} flatShading roughness={0.75} {...extra} />;

const Part: React.FC<{p: V3; s: V3; r?: V3; c: string; d?: number}> = ({p, s, r = [0, 0, 0], c, d = 1}) => (
  <mesh position={p} scale={s} rotation={r} castShadow>
    <icosahedronGeometry args={[1, d]} />
    {mat(c)}
  </mesh>
);

const Leg: React.FC<{at: V3; a: number; coat: string; front: boolean}> = ({at, a, coat, front}) => {
  const knee = front ? -Math.max(0, -Math.sin(a)) * 0.9 : Math.max(0, Math.sin(a)) * 0.9;
  return (
    <group position={at} rotation={[0, 0, Math.sin(a) * 0.45]}>
      <mesh position={[0, -0.3, 0]} scale={[0.16, 0.38, 0.14]} castShadow>
        <icosahedronGeometry args={[1, 1]} />
        {mat(coat)}
      </mesh>
      <group position={[0, -0.62, 0]} rotation={[0, 0, knee]}>
        <mesh position={[0, -0.25, 0]} castShadow>
          <cylinderGeometry args={[0.085, 0.07, 0.5, 6]} />
          {mat(coat)}
        </mesh>
        <mesh position={[0.06, -0.5, 0]} scale={[0.14, 0.07, 0.11]} castShadow>
          <icosahedronGeometry args={[1, 1]} />
          {mat(coat)}
        </mesh>
      </group>
    </group>
  );
};

export const Felino: React.FC<FelinoProps> = ({coat, spots, spotBase, reveal = 1, sweepX = null, walk = 0, walkAmt = 0, yaw = 0, pitch = 0, jaw = 0, eyes = 1, tail = 0}) => {
  const ros = useRef<THREE.InstancedMesh>(null!);
  const list = SP[spots];
  const K = spots === 'jaguar' ? 6 : 5; // manchitas por roseta (la 6.ª del jaguar es el punto del centro)
  useLayoutEffect(() => {
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), c = new THREE.Color();
    const z = new THREE.Vector3(0, 0, 1);
    list.forEach((s, i) => {
      const n = new THREE.Vector3(...s.n);
      q.setFromUnitVectors(z, n);
      const u = new THREE.Vector3(1, 0, 0).applyQuaternion(q), v = new THREE.Vector3(0, 1, 0).applyQuaternion(q);
      const band = sweepX === null ? 0 : Math.exp(-(((s.p[0] - sweepX) / 0.55) ** 2));
      c.set(coat).lerp(new THREE.Color(spotBase), clamp(Math.max(reveal, band)));
      for (let k = 0; k < K; k++) {
        const center = spots === 'jaguar' && k === 5;
        const ang = (k / 5) * Math.PI * 2 + i;
        const off = center ? 0 : s.s;
        const pos = new THREE.Vector3(...s.p).addScaledVector(n, 0.012).addScaledVector(u, Math.cos(ang) * off).addScaledVector(v, Math.sin(ang) * off);
        const sz = s.s * (center ? 0.3 : 0.42 + 0.12 * rnd(i * 7 + k, 9));
        m.compose(pos, q, new THREE.Vector3(sz * (center ? 1 : 1.25), sz, 1));
        ros.current.setMatrixAt(i * K + k, m);
        ros.current.setColorAt(i * K + k, c);
      }
    });
    ros.current.count = list.length * K;
    ros.current.instanceMatrix.needsUpdate = true;
    if (ros.current.instanceColor) ros.current.instanceColor.needsUpdate = true;
  }, [list, coat, spotBase, reveal, sweepX, spots, K]);

  const tailGeo = useMemo(() => {
    const sw = Math.round(tail * 20) / 20;
    const pts = [[-1.38, 1.45, 0], [-1.95, 1.18, 0.1 * sw], [-2.4, 0.8, 0.25 * sw], [-2.78, 0.62, 0.42 * sw], [-3.1, 0.78, 0.5 * sw], [-3.28, 1.05, 0.45 * sw]].map((p) => new THREE.Vector3(...(p as V3)));
    return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 20, 0.068, 6, false);
  }, [tail]);

  const amt = walkAmt;
  const legA = (ph: number) => (amt > 0 ? Math.sin(walk + ph) * amt : 0);
  const bob = amt * 0.05 * Math.sin(walk * 2);
  const eyeC = new THREE.Color('#ffd23f').multiplyScalar(0.4 + eyes * 1.6);
  return (
    <group position={[0, bob, 0]}>
      <Part p={[0, 1.3, 0]} s={[1.35, 0.46, 0.42]} c={coat} />
      <Part p={[0.9, 1.38, 0]} s={[0.5, 0.52, 0.44]} c={coat} />
      <Part p={[-0.95, 1.36, 0]} s={[0.5, 0.5, 0.44]} c={coat} />
      <Part p={[1.36, 1.62, 0]} s={[0.42, 0.3, 0.3]} r={[0, 0, 0.75]} c={coat} />
      <instancedMesh ref={ros} args={[undefined, undefined, 80 * 6]}>
        <circleGeometry args={[1, 6]} />
        <meshStandardMaterial color="#ffffff" roughness={0.9} side={THREE.DoubleSide} />
      </instancedMesh>
      <Leg at={[0.92, 1.2, 0.25]} a={legA(0)} coat={coat} front />
      <Leg at={[0.92, 1.2, -0.25]} a={legA(Math.PI)} coat={coat} front />
      <Leg at={[-0.98, 1.2, 0.25]} a={legA(Math.PI)} coat={coat} front={false} />
      <Leg at={[-0.98, 1.2, -0.25]} a={legA(0)} coat={coat} front={false} />
      <mesh geometry={tailGeo} castShadow>{mat(coat)}</mesh>
      {/* cabeza */}
      <group position={[1.6, 1.82, 0]} rotation={[0, yaw, pitch]}>
        <Part p={[0.2, 0.06, 0]} s={[0.4, 0.33, 0.36]} c={coat} />
        <Part p={[0.38, -0.06, 0.15]} s={[0.21, 0.18, 0.15]} c={coat} />
        <Part p={[0.38, -0.06, -0.15]} s={[0.21, 0.18, 0.15]} c={coat} />
        <Part p={[0.58, -0.08, 0]} s={[0.24, 0.14, 0.17]} c={coat} />
        <Part p={[0.8, -0.02, 0]} s={[0.05, 0.04, 0.075]} c="#120c0b" d={0} />
        {[1, -1].map((sd) => (
          <group key={sd}>
            <mesh position={[0.06, 0.29, sd * 0.25]} rotation={[sd * -0.55, 0, -0.1]} scale={[0.06, 0.1, 0.09]} castShadow>
              <icosahedronGeometry args={[1, 0]} />
              {mat(coat)}
            </mesh>
            <mesh position={[0.565, 0.13, sd * 0.14]} scale={[0.028, 0.045, 0.054]}>
              <icosahedronGeometry args={[1, 1]} />
              <meshStandardMaterial color={eyeC} emissive="#ffc21a" emissiveIntensity={eyes * 1.7} />
            </mesh>
            <mesh position={[0.598, 0.13, sd * 0.14]} scale={[0.01, 0.048, 0.015]}>
              <boxGeometry args={[1, 1, 1]} />
              <meshBasicMaterial color="#000" />
            </mesh>
            <mesh position={[0.64, -0.2, sd * 0.07]} rotation={[0, 0, Math.PI]}>
              <coneGeometry args={[0.025, 0.1 * (0.5 + jaw), 4]} />
              <meshStandardMaterial color="#f3ead8" />
            </mesh>
          </group>
        ))}
        <group position={[0.38, -0.17, 0]} rotation={[0, 0, -jaw * 0.8]}>
          <mesh position={[0.18, -0.03, 0]} scale={[0.22, 0.055, 0.14]} castShadow>
            <icosahedronGeometry args={[1, 1]} />
            {mat(coat)}
          </mesh>
          {jaw > 0.05 && (
            <mesh position={[0.18, 0.02, 0]} scale={[0.17, 0.025, 0.1]}>
              <icosahedronGeometry args={[1, 1]} />
              <meshStandardMaterial color="#8a2a2a" />
            </mesh>
          )}
        </group>
      </group>
    </group>
  );
};
