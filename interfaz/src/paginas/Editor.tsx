import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, archivo, miles, reloj, type Cotizacion, type EscenaLinea, type LineaDeTiempo, type SubLinea } from '../api';
import { Icono } from '../componentes/Icono';

// Editor tipo CapCut: vista previa arriba, pistas abajo. Cada cambio se guarda solo en el servidor
// (ediciones.json, aparte de la edición automática) y «Exportar» rearma el video con los cambios.

const PASOS: Record<string, string> = { regenerar: 'Regenerando la imagen', animar: 'Animando la escena', voz: 'Grabando la voz',
  video: 'Exportando el video' };

type Arrastre = { tipo: 'corte'; escena: number; x0: number; t0: number; min: number; max: number }
  | { tipo: 'sub'; escena: number; indice: number; borde: 'ini' | 'fin'; x0: number; t0: number };

export function Editor() {
  const { slug = '' } = useParams();
  const [d, setD] = useState<LineaDeTiempo | null>(null);
  const [error, setError] = useState('');
  const [sel, setSel] = useState<number | null>(null);
  const [t, setT] = useState(0);
  const [pps, setPps] = useState(40);                     // píxeles por segundo (zoom)
  const [guardado, setGuardado] = useState<'ok' | 'guardando' | 'error'>('ok');
  const [arr, setArr] = useState<Arrastre | null>(null);
  const [fantasma, setFantasma] = useState<{ escena: number; inicio: number } | null>(null);
  const [subsLocal, setSubsLocal] = useState<Record<number, SubLinea[]>>({});
  const video = useRef<HTMLVideoElement>(null);
  const pista = useRef<HTMLDivElement>(null);
  const espera = useRef<number | undefined>(undefined);

  const cargar = useCallback(async () => {
    try { const x = await api<LineaDeTiempo>(`/api/videos/${slug}/editor`); setD(x); setError(''); return x; }
    catch (e) { setError((e as Error).message); return null; }
  }, [slug]);
  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => {                                        // mientras hay un trabajo, se sigue mirando
    if (!d?.trabajo?.activo) return;
    const id = window.setTimeout(cargar, 2500);
    return () => window.clearTimeout(id);
  }, [d, cargar]);

  const guardar = async (p: Promise<LineaDeTiempo>) => {
    setGuardado('guardando');
    try { setD(await p); setGuardado('ok'); } catch (e) { setGuardado('error'); setError((e as Error).message); }
  };

  const escena = d?.escenas.find((e) => e.id === sel) ?? null;
  const subsDe = (id: number) => subsLocal[id] ?? (d?.subtitulos.filter((s) => s.escena === id) ?? []);

  // --- tiempo y vista previa
  const ir = (s: number) => { if (video.current) video.current.currentTime = s; setT(s); };
  useEffect(() => {
    const v = video.current;
    if (!v) return;
    const f = () => setT(v.currentTime);
    v.addEventListener('timeupdate', f);
    return () => v.removeEventListener('timeupdate', f);
  }, [d?.video]);
  const aTiempo = (clientX: number) => {
    const r = pista.current!.getBoundingClientRect();
    return Math.max(0, Math.min(d!.duracion, (clientX - r.left + pista.current!.scrollLeft) / pps));
  };

  // --- arrastres (borde de escena = corte; bordes de subtítulo = sus tiempos)
  useEffect(() => {
    if (!arr) return;
    const mover = (ev: PointerEvent) => {
      const dt = (ev.clientX - arr.x0) / pps;
      if (arr.tipo === 'corte') {
        setFantasma({ escena: arr.escena, inicio: Math.round(Math.min(arr.max, Math.max(arr.min, arr.t0 + dt)) * 10) / 10 });
      } else {
        const lista = subsDe(arr.escena).map((s) => ({ ...s }));
        const s = lista[arr.indice];
        const nuevo = Math.round((arr.t0 + dt) * 10) / 10;
        if (arr.borde === 'ini') s.inicio = Math.min(nuevo, s.fin - 0.2); else s.fin = Math.max(nuevo, s.inicio + 0.2);
        setSubsLocal((x) => ({ ...x, [arr.escena]: lista }));
      }
    };
    const soltar = () => {
      if (arr.tipo === 'corte' && fantasmaRef.current) {
        const f = fantasmaRef.current;
        guardar(api(`/api/videos/${slug}/editor/escenas/${f.escena}/corte`, { metodo: 'PUT', cuerpo: { inicio: f.inicio } }));
      }
      if (arr.tipo === 'sub') guardarSubs(arr.escena);
      setArr(null); setFantasma(null);
    };
    window.addEventListener('pointermove', mover);
    window.addEventListener('pointerup', soltar, { once: true });
    return () => { window.removeEventListener('pointermove', mover); window.removeEventListener('pointerup', soltar); };
  }); // eslint-disable-line react-hooks/exhaustive-deps
  const fantasmaRef = useRef(fantasma);
  fantasmaRef.current = fantasma;

  const guardarSubs = (id: number, inmediato = false) => {
    window.clearTimeout(espera.current);
    const enviar = () => {
      const lista = subsLocalRef.current[id];
      if (!lista) return;
      guardar(api<LineaDeTiempo>(`/api/videos/${slug}/editor/escenas/${id}/subtitulos`, { metodo: 'PUT',
        cuerpo: { subtitulos: lista.map(({ inicio, fin, texto }) => ({ inicio, fin, texto })) } }))
        .then(() => setSubsLocal((x) => { const y = { ...x }; delete y[id]; return y; }));
    };
    if (inmediato) enviar(); else espera.current = window.setTimeout(enviar, 700);
  };
  const subsLocalRef = useRef(subsLocal);
  subsLocalRef.current = subsLocal;

  const escenas = useMemo(() => (d?.escenas ?? []).map((e, k, todas) => {
    if (fantasma && e.id === fantasma.escena) return { ...e, inicio: fantasma.inicio };
    if (fantasma && todas[k + 1]?.id === fantasma.escena) return { ...e, fin: fantasma.inicio };
    return e;
  }), [d, fantasma]);

  if (error && !d) return <div className="pagina"><p className="error">{error}</p><Link to="/videos">← Mis videos</Link></div>;
  if (!d) return <div className="pagina"><p className="tenue">Cargando el editor…</p></div>;

  const ancho = Math.max(d.duracion * pps, 600);
  const marcas = Array.from({ length: Math.ceil(d.duracion / (pps >= 60 ? 1 : pps >= 25 ? 5 : 10)) + 1 },
    (_, i) => i * (pps >= 60 ? 1 : pps >= 25 ? 5 : 10));
  const trabajando = !!d.trabajo?.activo;

  return (
    <div className="editor">
      <div className="ed-cab">
        <Link to="/videos" className="boton-icono" aria-label="Volver"><Icono nombre="flecha" /></Link>
        <h2 title={d.titulo}>{d.titulo}</h2>
        <span className={`guardado ${guardado}`}>
          {guardado === 'guardando' ? 'Guardando…' : guardado === 'error' ? 'No se guardó' : `Guardado${d.ediciones.version ? ` · v${d.ediciones.version}` : ''}`}
        </span>
        <span className="crece" />
        {d.ediciones.pendientes && !trabajando && <span className="pendiente">Hay cambios sin exportar</span>}
        <Exportar slug={slug} ocupado={trabajando} listo={() => cargar()} />
      </div>
      {trabajando && d.trabajo && (
        <div className="ed-trabajo">
          <b>{PASOS[d.trabajo.paso] ?? d.trabajo.paso}</b> · {d.trabajo.mensaje}
          <div className="barra-progreso"><i style={{ width: `${Math.round(d.trabajo.progreso * 100)}%` }} /></div>
        </div>
      )}
      {d.trabajo?.error && !trabajando && <p className="error">No se pudo terminar: {d.trabajo.error}</p>}

      <div className="ed-medio">
        <div className="ed-vista">
          {d.video ? <video ref={video} src={`${archivo(slug, d.video)}?v=${d.video_version}`} controls preload="metadata" />
            : <div className="sin-video">Todavía no hay video exportado</div>}
          <div className="ed-reloj">{reloj(t)} / {reloj(d.duracion)}</div>
        </div>
        <Panel slug={slug} escena={escena} subs={escena ? subsDe(escena.id) : []} ocupado={trabajando}
          alCambiarSubs={(lista) => { if (!escena) return; setSubsLocal((x) => ({ ...x, [escena.id]: lista })); guardarSubs(escena.id); }}
          alGuardar={guardar} alLanzar={() => cargar()} />
      </div>

      <div className="ed-zoom">
        <span className="tenue pequeno">Zoom</span>
        <input type="range" min={8} max={120} value={pps} onChange={(e) => setPps(+e.target.value)} />
        <span className="tenue pequeno">Arrastra el borde izquierdo de una escena para mover el corte · los bordes de un subtítulo para cambiar sus tiempos</span>
      </div>
      <div className="ed-pistas">
        <div className="ed-nombres">
          <span>Tiempo</span><span className="alta">Escenas</span><span>Voz</span><span>Música</span><span>Efectos</span><span className="media">Subtítulos</span>
        </div>
        <div className="ed-lineas" ref={pista} onPointerDown={(e) => {
          if ((e.target as HTMLElement).closest('[data-agarre]')) return;
          ir(aTiempo(e.clientX));
        }}>
          <div style={{ width: ancho, position: 'relative' }}>
            <div className="regla">{marcas.map((m) => <span key={m} style={{ left: m * pps }}>{reloj(m).replace('.0', '')}</span>)}</div>
            <div className="fila-pista alta">
              {escenas.map((e) => (
                <div key={e.id} className={`bloque escena-b ${sel === e.id ? 'sel' : ''} ${e.corte_movido ? 'movido' : ''}`}
                  style={{ left: e.inicio * pps, width: Math.max(2, (e.fin - e.inicio) * pps) }}
                  onPointerDown={() => setSel(e.id)} title={`Escena ${e.id}: ${e.narracion}`}>
                  <div className="miniatura" style={{ backgroundImage: `url(${archivo(slug, e.imagen)}?v=${d.ediciones.version})` }} />
                  {(e.animacion || e.video_real) && <span className="insignia">{e.animacion ? '▶ animada' : '▶ video'}</span>}
                  <span className="num">{e.id}</span>
                  {e.id !== d.escenas[0].id && (
                    <span className="agarre" data-agarre onPointerDown={(ev) => {
                      ev.stopPropagation();
                      const k = d.escenas.findIndex((x) => x.id === e.id);
                      setArr({ tipo: 'corte', escena: e.id, x0: ev.clientX, t0: e.inicio,
                        min: d.escenas[k - 1].inicio + 0.4, max: e.fin - 0.4 });
                    }} />
                  )}
                </div>
              ))}
            </div>
            <div className="fila-pista">
              {d.voz.map((v) => <div key={v.escena} className={`bloque voz-b ${sel === v.escena ? 'sel' : ''}`}
                style={{ left: v.inicio * pps, width: Math.max(2, (v.fin - v.inicio) * pps) }} onPointerDown={() => setSel(v.escena)} />)}
            </div>
            <div className="fila-pista">
              {d.musica.map((m, i) => <div key={i} className="bloque musica-b" style={{ left: m.inicio * pps, width: (m.fin - m.inicio) * pps }}
                title={m.nombre}><span>♪ {m.nombre}</span></div>)}
            </div>
            <div className="fila-pista">
              {d.sfx.map((s, i) => <div key={i} className="bloque sfx-b" style={{ left: s.inicio * pps, width: Math.max(6, s.dur * pps) }}
                title={s.tipo} />)}
            </div>
            <div className="fila-pista media">
              {d.escenas.flatMap((e) => subsDe(e.id).map((s, i) => (
                <div key={`${e.id}-${i}`} className={`bloque sub-b ${s.editado || subsLocal[e.id] ? 'editado' : ''} ${sel === e.id ? 'sel' : ''}`}
                  style={{ left: s.inicio * pps, width: Math.max(8, (s.fin - s.inicio) * pps) }} title={s.texto}
                  onPointerDown={() => setSel(e.id)}>
                  <span className="agarre-sub izq" data-agarre onPointerDown={(ev) => { ev.stopPropagation(); setSel(e.id);
                    setArr({ tipo: 'sub', escena: e.id, indice: i, borde: 'ini', x0: ev.clientX, t0: s.inicio }); }} />
                  <span className="txt">{s.texto}</span>
                  <span className="agarre-sub der" data-agarre onPointerDown={(ev) => { ev.stopPropagation(); setSel(e.id);
                    setArr({ tipo: 'sub', escena: e.id, indice: i, borde: 'fin', x0: ev.clientX, t0: s.fin }); }} />
                </div>
              )))}
            </div>
            <div className="cabezal" style={{ left: t * pps }} />
          </div>
        </div>
      </div>
    </div>
  );
}

function useCosto(accion: string, cantidad = 1) {
  const [c, setC] = useState<Cotizacion | null>(null);
  useEffect(() => { api<Cotizacion>('/api/v2/cotizar', { cuerpo: { accion, cantidad } }).then(setC).catch(() => setC(null)); }, [accion, cantidad]);
  if (!c) return '';
  return c.a_costo ? `≈ $${c.costo_real_usd?.toFixed(2) ?? ''} real` : `≈ ${miles(c.creditos)} créditos`;
}

function Panel({ slug, escena, subs, ocupado, alCambiarSubs, alGuardar, alLanzar }: {
  slug: string; escena: EscenaLinea | null; subs: SubLinea[]; ocupado: boolean;
  alCambiarSubs: (l: SubLinea[]) => void; alGuardar: (p: Promise<LineaDeTiempo>) => void; alLanzar: () => void;
}) {
  const [inst, setInst] = useState('');
  const [mov, setMov] = useState('');
  const [texto, setTexto] = useState('');
  const [msg, setMsg] = useState('');
  useEffect(() => { setInst(''); setMov(''); setTexto(escena?.narracion ?? ''); setMsg(''); }, [escena?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const cImg = useCosto('imagen_regenerada');
  const cAni = useCosto('animar_escena');
  const cVoz = useCosto('audio_regenerado');

  if (!escena) {
    return <aside className="ed-panel vacio"><Icono nombre="videos" tam={30} /><b>Toca una escena</b>
      <span className="tenue">Aquí podrás regenerar su imagen, animarla, cambiar su duración, su voz y sus subtítulos.</span></aside>;
  }
  const lanzar = async (ruta: string, cuerpo: unknown, aviso: string) => {
    setMsg('');
    try { await api(ruta, { cuerpo }); setMsg(aviso); alLanzar(); } catch (e) { setMsg((e as Error).message); }
  };
  const dur = escena.fin - escena.inicio;
  return (
    <aside className="ed-panel">
      <div className="ed-panel-cab">
        <b>Escena {escena.id}</b><span className="tenue pequeno">{escena.seccion} · {dur.toFixed(1)} s</span>
      </div>
      <img className="ed-img" src={`${archivo(slug, escena.imagen)}?v=${Date.now() % 100000}`} alt="" />
      {msg && <p className="aviso-ed">{msg}</p>}

      <details open>
        <summary>Regenerar imagen <span className="costo">{cImg}</span></summary>
        {escena.puede_regenerar ? (<>
          <textarea rows={2} value={inst} onChange={(e) => setInst(e.target.value)} placeholder="¿Cómo quieres que se vea? (vacío = otra versión igual)" />
          <button className="boton-borde" disabled={ocupado} onClick={() => lanzar(`/api/videos/${slug}/escenas/${escena.id}/regenerar`,
            { instruccion: inst }, 'Regenerando la imagen…')}>Regenerar imagen</button>
        </>) : <p className="tenue pequeno">Esta escena reutiliza otra imagen o es la tira de niveles: regenera la original.</p>}
      </details>

      <details>
        <summary>Animar <span className="costo">{cAni}</span></summary>
        {escena.modo === 'tira' ? <p className="tenue pequeno">La tira de niveles ya se mueve sola.</p> : (<>
          <textarea rows={2} value={mov} onChange={(e) => setMov(e.target.value)} placeholder="Movimiento (ej.: el alacrán levanta la cola despacio)" />
          <div className="fila-botones">
            <button className="boton-borde" disabled={ocupado} onClick={() => lanzar(`/api/videos/${slug}/escenas/${escena.id}/animar`,
              { instruccion: mov }, 'Animando: tarda unos minutos…')}>{escena.animacion ? 'Animar otra vez' : 'Animar escena'}</button>
            {escena.animacion && <button className="boton-icono pequeno" onClick={() =>
              alGuardar(api(`/api/videos/${slug}/editor/escenas/${escena.id}/animacion`, { metodo: 'DELETE' }))}>Volver a imagen fija</button>}
          </div>
        </>)}
      </details>

      <details>
        <summary>Duración</summary>
        <p className="tenue pequeno">Mueve el corte con la escena anterior (la voz no se corre). También puedes arrastrar su borde izquierdo abajo.</p>
        <div className="fila-botones">
          {[-0.5, -0.1, 0.1, 0.5].map((x) => (
            <button key={x} className="chip" onClick={() => alGuardar(api(`/api/videos/${slug}/editor/escenas/${escena.id}/corte`,
              { metodo: 'PUT', cuerpo: { inicio: Math.max(0, escena.inicio + x) } }))}>{x > 0 ? `+${x}` : x} s</button>
          ))}
          {escena.corte_movido && <button className="boton-icono pequeno" onClick={() =>
            alGuardar(api(`/api/videos/${slug}/editor/escenas/${escena.id}/corte`, { metodo: 'DELETE' }))}>Deshacer</button>}
        </div>
      </details>

      <details>
        <summary>Regenerar audio <span className="costo">{cVoz}</span></summary>
        <textarea rows={3} value={texto} onChange={(e) => setTexto(e.target.value)} />
        <button className="boton-borde" disabled={ocupado} onClick={() => lanzar(`/api/videos/${slug}/escenas/${escena.id}/voz`,
          { texto }, 'Grabando la voz de esta escena…')}>Regenerar audio</button>
      </details>

      <details open>
        <summary>Subtítulos</summary>
        {subs.map((s, i) => (
          <div key={i} className="sub-edicion">
            <input value={s.texto} onChange={(e) => alCambiarSubs(subs.map((x, j) => (j === i ? { ...x, texto: e.target.value } : x)))} />
            <span className="tenue pequeno">{reloj(s.inicio)} → {reloj(s.fin)}</span>
          </div>
        ))}
        {subs.some((s) => s.editado) && <button className="boton-icono pequeno" onClick={() =>
          alGuardar(api(`/api/videos/${slug}/editor/escenas/${escena.id}/subtitulos`, { metodo: 'DELETE' }))}>Volver a los automáticos</button>}
      </details>
    </aside>
  );
}

function Exportar({ slug, ocupado, listo }: { slug: string; ocupado: boolean; listo: () => void }) {
  const [fps, setFps] = useState(() => { try { return +(localStorage.getItem('xandart_fps') || 60); } catch { return 60; } });
  const [err, setErr] = useState('');
  return (
    <div className="exportar">
      <select value={fps} onChange={(e) => { setFps(+e.target.value); try { localStorage.setItem('xandart_fps', e.target.value); } catch { /* sin almacenamiento */ } }}>
        <option value={60}>60 cps</option><option value={30}>30 cps (más rápido)</option>
      </select>
      <button className="boton-primario" disabled={ocupado} onClick={async () => {
        setErr('');
        try { await api(`/api/videos/${slug}/video`, { cuerpo: { fps } }); listo(); } catch (e) { setErr((e as Error).message); }
      }}><Icono nombre="videos" tam={18} /> Exportar</button>
      {err && <span className="error pequeno">{err}</span>}
    </div>
  );
}
