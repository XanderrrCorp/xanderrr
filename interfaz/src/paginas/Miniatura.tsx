import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, archivo } from '../api';
import { Icono } from '../componentes/Icono';

// Miniatura de formato escala (2x3): Claude la planifica, se dibuja cada animal por separado y
// Xandart la arma con fuentes reales. Textos, orden, tamaño y posición no gastan: solo se rearma.

interface Ajuste { escala: number; dx: number; dy: number }
interface Celda { name: string; label: string; is_hero: boolean; archivo: string | null; variantes: string[]; ajuste: Ajuste }
interface Plan { cells: Celda[]; hero_text: string; hero_icon: string; hero_glow_color: string; hero_censor: boolean }
interface Referencia { archivo: string; activa: boolean }
interface Medidas { protagonista_vs_mayor?: number; protagonista_ok?: boolean; solape_max?: number; solape_ok?: boolean; icono_libre?: boolean; cabeza_sin_cortar?: boolean }
interface Ronda { resumen?: string; sujetos: Record<string, { ok: boolean; problemas: string[] }>; medidas?: Medidas }
interface EstadoMini {
  plan: Plan | null;
  mapa: { sujetos: { indice: number; caja: [number, number, number, number] }[]; medidas?: Medidas } | null;
  qa: { aprobada: boolean; rondas: Ronda[] } | null;
  miniatura: string | null; feed: string | null; carpeta: string; gastado: string; iconos: string[];
  estimacion: { texto: string; por_imagen_usd: number };
  plantilla: { canal: string; nombre: string; referencias: Referencia[] };
  trabajo: { paso: string; mensaje: string; progreso: number; activo: boolean; error: string | null; segundos: number } | null;
}

const PASOS: Record<string, string> = { miniatura: 'Haciendo la miniatura', regenerar: 'Regenerando un animal', variantes: 'Dibujando variantes' };

export function Miniatura() {
  const { slug = '' } = useParams();
  const [m, setM] = useState<EstadoMini | null>(null);
  const [sel, setSel] = useState(0);
  const [aviso, setAviso] = useState('');
  const [ver, setVer] = useState(() => Date.now());
  const [arrastrando, setArrastrando] = useState<number | null>(null);

  const url = (r: string) => `${archivo(slug, r)}?v=${ver}`;
  const cargar = useCallback(async () => {
    try {
      const d = await api<EstadoMini>(`/api/videos/${slug}/miniatura`);
      setM((antes) => { if (antes?.trabajo?.activo && !d.trabajo?.activo) setVer(Date.now()); return d; });
    } catch (e) { setAviso((e as Error).message); }
  }, [slug]);
  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => {
    if (!m?.trabajo?.activo) return;
    const id = window.setTimeout(cargar, 2000);
    return () => window.clearTimeout(id);
  }, [m, cargar]);

  const accion = async (ruta: string, cuerpo: unknown = {}, metodo = 'POST') => {
    setAviso('');
    try { setM(await api<EstadoMini>(`/api/videos/${slug}/miniatura${ruta}`, { metodo, cuerpo })); setVer(Date.now()); }
    catch (e) { setAviso((e as Error).message); }
  };
  const referencias = async (ruta: string, opciones: { metodo?: string; cuerpo?: unknown } = {}) => {
    try { await api(`/api/canales/${m!.plantilla.canal}/miniatura/referencias${ruta}`, opciones); setVer(Date.now()); cargar(); }
    catch (e) { setAviso((e as Error).message); }
  };
  const subirReferencia = async (f: File | undefined) => {
    if (!f || !m) return;
    const datos = new FormData(); datos.append('archivo', f);
    const r = await fetch(`/api/canales/${m.plantilla.canal}/miniatura/referencias`, { method: 'POST', body: datos });
    const v = await r.json().catch(() => ({}));
    if (!r.ok) setAviso((v as { detail?: string }).detail || `Error ${r.status}`);
    setVer(Date.now()); cargar();
  };

  if (!m) return <div className="pagina"><p className="tenue">{aviso || 'Cargando…'}</p></div>;
  const t = m.trabajo, p = m.plan, trabajando = !!t?.activo;
  const usd = m.estimacion.por_imagen_usd;

  const conPermiso = (paso: string) => {
    if (!window.confirm('Esto pasa el máximo por video. ¿Das permiso para seguir?')) return;
    if (paso === 'variantes') return accion('/variantes', { n: 2, permiso: true });
    if (paso === 'regenerar') return accion(`/sujetos/${sel}/regenerar`, { instruccion: '', permiso: true });
    accion('/producir', { permiso: true });
  };
  const soltar = (hacia: number) => {
    if (arrastrando === null || arrastrando === hacia) return;
    const orden = [0, 1, 2, 3, 4, 5];
    orden.splice(hacia, 0, orden.splice(arrastrando, 1)[0]);
    setArrastrando(null); setSel(hacia);
    accion('', { orden }, 'PUT');
  };

  return (
    <div className="pagina revision">
      <div className="rev-cab">
        <Link to={`/videos/${slug}`} className="tenue pequeno">← Volver al video</Link>
        <span className="crece" />
        <span className="chip-gasto">Miniaturas: {m.gastado}</span>
      </div>
      <h1 className="rev-titulo">Miniatura</h1>
      <p className="tenue">Claude la planifica, cada animal se dibuja por separado y Xandart la arma con fuentes reales: el orden y los textos siempre salen perfectos.</p>

      {trabajando && t && (
        <section className="rev-tarjeta">
          <b>{PASOS[t.paso] ?? t.paso}</b>
          <div className="barra-progreso"><i style={{ width: `${Math.round(t.progreso * 100)}%` }} /></div>
          <span className="tenue pequeno">{t.mensaje} · {Math.floor(t.segundos / 60)} min {t.segundos % 60} s</span>
        </section>
      )}
      {!trabajando && t?.error && (
        <div className="rev-error">No se pudo terminar: {t.error}
          {/máximo|permiso|FRENO|tope/.test(t.error) && <div><button className="boton-borde pequeno" onClick={() => conPermiso(t.paso)}>Dar permiso y seguir</button></div>}
        </div>
      )}
      {aviso && <div className="rev-error">{aviso}</div>}

      {!m.miniatura && !trabajando && (
        <section className="rev-tarjeta">
          <h2>Hacer la miniatura</h2>
          <p>{m.estimacion.texto}</p>
          <div className="fila-botones">
            <button className="boton-primario" onClick={() => { if (window.confirm(`${m.estimacion.texto}\n\n¿Producir la miniatura?`)) accion('/producir'); }}>
              <Icono nombre="miniatura" tam={18} /> Producir miniatura
            </button>
          </div>
        </section>
      )}

      {m.miniatura && p && (
        <section className="rev-tarjeta">
          <div className="mini-grande">
            <img src={url(m.miniatura)} alt="Miniatura" />
            {(m.mapa?.sujetos ?? []).map((s) => {
              const [x0, y0, x1, y1] = s.caja;
              return <button key={s.indice} className={`mini-caja ${s.indice === sel ? 'sel' : ''}`} title={p.cells[s.indice]?.name}
                style={{ left: `${x0 / 12.8}%`, top: `${y0 / 7.2}%`, width: `${(x1 - x0) / 12.8}%`, height: `${(y1 - y0) / 7.2}%` }}
                onClick={() => setSel(s.indice)} />;
            })}
          </div>
          <div className="mini-vistas">
            {m.feed && <div><span className="tenue pequeno">En el feed del celular</span><img className="mini-feed" src={url(m.feed)} alt="" /></div>}
            {m.feed && <div><span className="tenue pequeno">En videos sugeridos</span><img className="mini-sugerido" src={url(m.feed)} alt="" /></div>}
            <span className="crece" />
            <a className="boton-primario" href={`${archivo(slug, m.miniatura)}?descargar=true`}>Descargar JPG (1280×720)</a>
          </div>
          <p className="tenue pequeno">Toca un animal para editarlo. Arrastra las fichas para cambiar el orden (el primero es el protagonista).</p>
          <div className="mini-orden">
            {p.cells.map((c, i) => (
              <div key={i} className={`mini-ficha ${i === sel ? 'sel' : ''}`} draggable={!trabajando}
                onDragStart={() => setArrastrando(i)} onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); soltar(i); }}
                onClick={() => setSel(i)}>
                {c.archivo ? <img src={url(`${m.carpeta}/${c.archivo}`)} alt="" /> : <div className="sin-img">sin imagen</div>}
                <span>{i + 1}. {c.label}{c.is_hero ? ' ★' : ''}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {m.miniatura && p && p.cells[sel] && !trabajando && (
        <Panel key={`${sel}-${ver}`} m={m} p={p} i={sel} url={url} usd={usd} accion={accion} />
      )}

      {m.qa && <ControlCalidad m={m} />}

      <section className="rev-tarjeta">
        <h2>Plantilla del canal · {m.plantilla.nombre}</h2>
        <p className="tenue">Referencias de estilo: 3 a 6 animales sueltos recortados, <b>sin texto y sin cuadrículas</b> (si subes miniaturas completas, se copian la cuadrícula y los textos). En cada imagen se mandan como mucho 3.</p>
        <div className="mini-refs">
          {m.plantilla.referencias.length === 0 && <p className="tenue">Sin referencias todavía.</p>}
          {m.plantilla.referencias.map((r) => (
            <div key={r.archivo} className={`mini-ref ${r.activa ? '' : 'apagada'}`}>
              <img src={`/canales/${m.plantilla.canal}/referencias/${encodeURIComponent(r.archivo)}?v=${ver}`} alt="" />
              <div className="fila-botones">
                <label className="casilla"><input type="checkbox" checked={r.activa}
                  onChange={(e) => referencias(`/${encodeURIComponent(r.archivo)}`, { metodo: 'PUT', cuerpo: { activa: e.target.checked } })} /> usar</label>
                <span className="crece" />
                <button className="boton-icono pequeno" onClick={() => { if (window.confirm('¿Borrar esta referencia de estilo?')) referencias(`/${encodeURIComponent(r.archivo)}`, { metodo: 'DELETE' }); }}>Borrar</button>
              </div>
            </div>
          ))}
        </div>
        <label className="boton-borde pequeno subir">Subir referencia
          <input type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={(e) => subirReferencia(e.target.files?.[0])} />
        </label>
      </section>
    </div>
  );
}

function Panel({ m, p, i, url, usd, accion }: {
  m: EstadoMini; p: Plan; i: number; url: (r: string) => string; usd: number;
  accion: (ruta: string, cuerpo?: unknown, metodo?: string) => Promise<void>;
}) {
  const c = p.cells[i];
  const [heroe, setHeroe] = useState(p.hero_text);
  const [icono, setIcono] = useState(p.hero_icon);
  const [aura, setAura] = useState(p.hero_glow_color);
  const [censura, setCensura] = useState(p.hero_censor);
  const [etiqueta, setEtiqueta] = useState(c.label);
  const [escala, setEscala] = useState(c.ajuste.escala);
  const [instruccion, setInstruccion] = useState('');

  const cambios = () => ({
    ajustes: { [i]: { ...c.ajuste, escala } },
    ...(c.is_hero ? { hero_text: heroe, hero_icon: icono, hero_glow_color: aura.toUpperCase(), hero_censor: censura } : { labels: { [i]: etiqueta } }),
  });
  const mover = (dx: number, dy: number) => accion('', { ajustes: { [i]: { escala, dx: c.ajuste.dx + dx, dy: c.ajuste.dy + dy } } }, 'PUT');

  return (
    <section className="rev-tarjeta mini-panel">
      <h2>{i + 1}. {c.name} {c.is_hero && <span className="chip-gasto">protagonista</span>}</h2>
      {c.is_hero ? (
        <div className="mini-campos">
          <label className="campo">Texto del protagonista (2 a 5 palabras)<input value={heroe} maxLength={40} onChange={(e) => setHeroe(e.target.value)} /></label>
          <label className="campo">Ícono<select value={icono} onChange={(e) => setIcono(e.target.value)}>
            {[...new Set([p.hero_icon, ...m.iconos])].map((n) => <option key={n}>{n}</option>)}</select></label>
          <label className="campo">Color del aura<input type="color" value={aura} onChange={(e) => setAura(e.target.value)} /></label>
          <label className="casilla"><input type="checkbox" checked={censura} onChange={(e) => setCensura(e.target.checked)} /> Herida censurada (pixelada)</label>
        </div>
      ) : (
        <label className="campo">Etiqueta (máximo 20 letras)<input value={etiqueta} maxLength={20} onChange={(e) => setEtiqueta(e.target.value)} /></label>
      )}
      <label className="campo">Tamaño: {escala.toFixed(2)}
        <input type="range" min={0.4} max={2.5} step={0.05} value={escala} onChange={(e) => setEscala(+e.target.value)} /></label>
      <div className="fila-botones">
        <span className="tenue pequeno">Mover:</span>
        <button className="boton-borde pequeno" onClick={() => mover(0, -12)}>↑</button>
        <button className="boton-borde pequeno" onClick={() => mover(0, 12)}>↓</button>
        <button className="boton-borde pequeno" onClick={() => mover(-12, 0)}>←</button>
        <button className="boton-borde pequeno" onClick={() => mover(12, 0)}>→</button>
        <button className="boton-icono pequeno" onClick={() => accion('', { ajustes: { [i]: { escala: 1, dx: 0, dy: 0 } } }, 'PUT')}>Restablecer</button>
        <span className="crece" />
        <button className="boton-primario" onClick={() => accion('', cambios(), 'PUT')}>Aplicar cambios</button>
      </div>
      <p className="tenue pequeno">Textos, ícono, aura, orden, tamaño y posición no gastan nada: solo se vuelve a armar.</p>

      <h3 className="rev-seccion">Imagen</h3>
      <div className="mini-variantes">
        {c.variantes.map((v) => (
          <img key={v} className={v === c.archivo ? 'sel' : ''} src={url(`${m.carpeta}/${v}`)} alt="" title="Usar esta"
            onClick={() => v !== c.archivo && accion(`/sujetos/${i}/elegir`, { archivo: v })} />
        ))}
      </div>
      <label className="campo">¿Cómo debe verse? (opcional)
        <input value={instruccion} placeholder="Ej.: con la boca más abierta, de frente, más amenazante" onChange={(e) => setInstruccion(e.target.value)} /></label>
      <div className="fila-botones">
        <button className="boton-borde" onClick={() => accion(`/sujetos/${i}/regenerar`, { instruccion: instruccion.trim() })}>Regenerar (≈ {usd} USD)</button>
        {c.is_hero && <button className="boton-borde" onClick={() => {
          if (window.confirm(`Se dibujan 2 versiones más del protagonista (≈ ${usd} USD cada una). ¿Seguir?`)) accion('/variantes', { n: 2 });
        }}>Crear 2 variantes para elegir</button>}
        <button className="boton-icono pequeno" onClick={() => {
          if (window.confirm('Esta imagen se agrega a las referencias de estilo del canal. ¿Seguir?')) accion(`/sujetos/${i}/referencia`);
        }}>Usar como referencia de estilo</button>
      </div>
    </section>
  );
}

function ControlCalidad({ m }: { m: EstadoMini }) {
  const qa = m.qa!;
  const r = qa.rondas[qa.rondas.length - 1];
  if (!r) return null;
  const med = m.mapa?.medidas ?? r.medidas;
  const ok = (v?: boolean) => <span className={`mini-sello ${v ? 'bien' : 'revisar'}`}>{v ? 'bien' : 'revisar'}</span>;
  const malos = Object.entries(r.sujetos).filter(([, s]) => !s.ok || s.problemas.length);
  return (
    <section className="rev-tarjeta">
      <h2>Control de calidad <span className={`mini-sello ${qa.aprobada ? 'bien' : 'revisar'}`}>{qa.aprobada ? 'aprobada' : 'con observaciones'}</span></h2>
      {r.resumen && <p>{r.resumen}</p>}
      {malos.length ? <ul>{malos.map(([k, s]) => <li key={k}><b>{+k + 1}. {m.plan?.cells[+k]?.name}</b>: {s.problemas.join('; ') || 'revisar'}</li>)}</ul>
        : <p className="tenue">Sin problemas.</p>}
      {med && (
        <ul className="mini-medidas">
          <li>Protagonista: <b>{med.protagonista_vs_mayor ?? '—'}×</b> el más grande de los otros (mínimo 1,3×) {ok(med.protagonista_ok)}</li>
          <li>Encimado máximo entre dos: <b>{Math.round((med.solape_max || 0) * 100)} %</b> (máximo 5 %) {ok(med.solape_ok)}</li>
          <li>Ícono libre, sin tocar a nadie {ok(med.icono_libre)}</li>
          <li>Cabezas sin cortar por arriba {ok(med.cabeza_sin_cortar)}</li>
        </ul>
      )}
      <p className="tenue pequeno">{qa.rondas.length} ronda(s) de revisión · cada animal se regenera como mucho 2 veces.</p>
    </section>
  );
}
