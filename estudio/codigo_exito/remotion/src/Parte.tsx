// Código del Éxito híbrido: UNA parte del video (desde un [PROFESOR] hasta antes del siguiente). Bloques en una
// TransitionSeries con SIEMPRE la misma transición (fundido de 15 cuadros); cada bloque se alarga lo que dura la
// transición para que la imagen siga pegada a la voz. Encima de todo: viñeta + grano (stock, aura y Profesor del mismo
// mundo) y los subtítulos (Bebas Neue, al centro, en trozos cortos; los únicos del video).
import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, Sequence, continueRender, delayRender, interpolate, random, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { useAudioData, visualizeAudio } from "@remotion/media-utils";

export const T = 15; // cuadros de la transición fija
export const COLOR = { vino: "#5c1626", vinoOsc: "#220810", dorado: "#d6ac5c", crema: "#f4e8d2" };

export type Clip = { url: string; dur: number };
export type Bloque = {
  tipo: "profesor" | "stock" | "aura"; dur: number;               // segundos del bloque en la parte
  profesor?: string; stock?: Clip[];
  aura?: { respiros: { t: number; dur: number; url: string }[] };
};
export type PropsParte = { fps: number; bloques: Bloque[]; subtitulos: { texto: string; ini: number; fin: number }[]; audio?: string | null; inicio: number; cola: number };

const fuente = (() => {
  let lista = false;
  return () => {
    if (lista) return;
    lista = true;
    const h = delayRender("fuente");
    const f = new FontFace("Bebas Neue", `url(${staticFile("BebasNeue-Regular.ttf")})`);
    f.load().then((ff) => { (document.fonts as unknown as { add: (x: FontFace) => void }).add(ff); continueRender(h); }).catch(() => continueRender(h));
  };
})();

/** el color uniforme del stock: cálido vino / dorado / crema */
const Gradado: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill>
    <AbsoluteFill style={{ filter: "sepia(0.32) saturate(0.82) contrast(1.06) brightness(0.9)" }}>{children}</AbsoluteFill>
    <AbsoluteFill style={{ background: `linear-gradient(160deg, ${COLOR.dorado}55, ${COLOR.vino}88)`, mixBlendMode: "soft-light" }} />
    <AbsoluteFill style={{ background: `${COLOR.vino}22`, mixBlendMode: "multiply" }} />
  </AbsoluteFill>
);

const ClipStock: React.FC<{ c: Clip }> = ({ c }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const fase = ((f / fps) % 3.5) / 3.5;                            // golpe de zoom cada 3,5 s (más dopamina)
  const golpe = f / fps > 1 ? 0.03 * Math.exp(-fase * 6) * (1 - Math.exp(-fase * 40)) : 0;
  const z = interpolate(f, [0, c.dur * fps], [1.02, 1.12]) + golpe;  // ningún plano quieto
  return <AbsoluteFill style={{ transform: `scale(${z})` }}><OffthreadVideo src={c.url} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} /></AbsoluteFill>;
};

const Stock: React.FC<{ clips: Clip[] }> = ({ clips }) => {
  const { fps } = useVideoConfig();
  let desde = 0;
  return (
    <Gradado>
      {clips.map((c, i) => { const s = <Sequence key={i} from={Math.round(desde * fps)} durationInFrames={Math.max(1, Math.round(c.dur * fps) + (i < clips.length - 1 ? 0 : T))}><ClipStock c={c} /></Sequence>; desde += c.dur; return s; })}
    </Gradado>
  );
};

const Profesor: React.FC<{ url: string }> = ({ url }) => <OffthreadVideo src={url} muted style={{ width: "100%", height: "100%" }} />;

/** aura: fondo vino con luz dorada que respira y un anillo de barras que se mueve con la voz real */
const Aura: React.FC<{ audio?: string | null; desde: number; respiros: { t: number; dur: number; url: string }[] }> = ({ audio, desde, respiros }) => {
  const f = useCurrentFrame(); const { fps, width, height } = useVideoConfig();
  const datos = audio ? useAudioData(audio) : null; // eslint-disable-line react-hooks/rules-of-hooks
  const n = 64;
  const valores = datos ? visualizeAudio({ fps, frame: f + Math.round(desde * fps), audioData: datos, numberOfSamples: n, optimizeFor: "speed" }) : new Array(n).fill(0);
  const respira = 0.5 + 0.5 * Math.sin((f / fps) * 0.8);
  const cx = width / 2, cy = height / 2, r0 = 210;
  const fuerza = valores.reduce((a, b) => a + b, 0) / n;
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 48%, ${COLOR.vino} 0%, ${COLOR.vinoOsc} 72%)` }}>
      <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 50%, ${COLOR.dorado}${Math.round(40 + 50 * respira + 120 * fuerza).toString(16).padStart(2, "0")} 0%, transparent 38%)` }} />
      <svg width={width} height={height} style={{ position: "absolute" }}>
        {Array.from({ length: 40 }).map((_, i) => { // polvo dorado que sube despacio
          const x = random(`x${i}`) * width, v = 8 + random(`v${i}`) * 18, y = (height + 40) - ((f / fps) * v + random(`y${i}`) * height) % (height + 80);
          return <circle key={i} cx={x + 14 * Math.sin(f / 50 + i)} cy={y} r={1.4 + random(`r${i}`) * 2.4} fill={COLOR.crema} opacity={0.18 + 0.25 * random(`o${i}`)} />;
        })}
        {valores.map((v, i) => {
          const a = (i / n) * Math.PI * 2 - Math.PI / 2, largo = 18 + Math.min(1, v * 3.2) * 170;
          return <line key={i} x1={cx + Math.cos(a) * r0} y1={cy + Math.sin(a) * r0} x2={cx + Math.cos(a) * (r0 + largo)} y2={cy + Math.sin(a) * (r0 + largo)}
            stroke={COLOR.dorado} strokeWidth={9} strokeLinecap="round" opacity={0.85} />;
        })}
        <circle cx={cx} cy={cy} r={r0 - 14} fill="none" stroke={COLOR.crema} strokeOpacity={0.55} strokeWidth={3} />
        <circle cx={cx} cy={cy} r={(r0 - 40) * (0.96 + 0.06 * respira + 0.25 * fuerza)} fill={COLOR.dorado} fillOpacity={0.14} />
      </svg>
      {respiros.map((r, i) => (   // pedido del dueño: ningún aura de más de 2-3 min seguidos → un respiro de stock
        <Sequence key={i} from={Math.round(r.t * fps)} durationInFrames={Math.round(r.dur * fps)}>
          <Respiro url={r.url} dur={r.dur} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

const Respiro: React.FC<{ url: string; dur: number }> = ({ url, dur }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const o = interpolate(f, [0, T, dur * fps - T, dur * fps], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ opacity: o }}><Gradado><ClipStock c={{ url, dur }} /></Gradado></AbsoluteFill>;
};

/** viñeta + grano encima de TODO (pedido del dueño) */
const Pelicula: React.FC = () => {
  const f = useCurrentFrame(); const { width, height } = useVideoConfig();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 50%, transparent 55%, rgba(18,4,8,0.62) 100%)" }} />
      <svg width={width} height={height} style={{ position: "absolute", mixBlendMode: "overlay", opacity: 0.16 }}>
        <filter id="grano"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={f % 97} stitchTiles="stitch" /><feColorMatrix type="saturate" values="0" /></filter>
        <rect width="100%" height="100%" filter="url(#grano)" />
      </svg>
    </AbsoluteFill>
  );
};

/** subtítulos abajo, en una franja oscura (como los primeros videos): nunca tapan la tabla, la frase ni al Profesor */
const Subtitulos: React.FC<{ lista: PropsParte["subtitulos"] }> = ({ lista }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const t = f / fps;
  const s = lista.find((x) => t >= x.ini && t < x.fin);
  if (!s) return null;
  const k = spring({ frame: f - Math.round(s.ini * fps), fps, config: { damping: 14, stiffness: 240, mass: 0.5 } });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 58 }}>
      <div style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: 80, letterSpacing: 1.5, color: "#ffffff", textAlign: "center", maxWidth: 1400,
        padding: "6px 34px 2px", borderRadius: 18, background: "rgba(0,0,0,0.47)", transform: `translateY(${(1 - k) * 18}px) scale(${0.9 + 0.1 * k})`,
        WebkitTextStroke: "3px #000000", paintOrder: "stroke fill" }}>
        {s.texto.toUpperCase()}
      </div>
    </AbsoluteFill>
  );
};

export const Parte: React.FC<PropsParte> = (p) => {
  fuente();
  const { fps } = useVideoConfig();
  let desde = 0;
  return (
    <AbsoluteFill style={{ background: COLOR.vinoOsc }}>
      <TransitionSeries>
        {p.bloques.flatMap((b, i) => {
          const largo = Math.max(1, Math.round(b.dur * fps) + (i < p.bloques.length - 1 ? T : p.cola));
          const ini = desde; desde += b.dur;
          const contenido = b.tipo === "profesor" && b.profesor ? <Profesor url={b.profesor} />
            : b.tipo === "stock" && b.stock?.length ? <Stock clips={b.stock} />
            : <Aura audio={p.audio} desde={ini} respiros={b.aura?.respiros ?? []} />;
          const s = <TransitionSeries.Sequence key={`s${i}`} durationInFrames={largo}>{contenido}</TransitionSeries.Sequence>;
          return i === 0 ? [s] : [<TransitionSeries.Transition key={`t${i}`} presentation={fade()} timing={linearTiming({ durationInFrames: T })} />, s];
        })}
      </TransitionSeries>
      <Pelicula />
      <Subtitulos lista={p.subtitulos} />
    </AbsoluteFill>
  );
};
void Img;
