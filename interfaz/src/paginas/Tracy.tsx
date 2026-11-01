import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, archivo, type VideoDetalle } from '../api';

// Canal Tracy: pegas el guion y Xandart hace todo (voz, tiempos con Whisper, clips de Pexels y del
// seminario, subtítulos y música de fondo). Sin terminal.

interface EstadoTracy {
  canal: string; clip_base: string; clip_existe: boolean; musica: string; musica_existe: boolean;
  presentador: string; presentador_existe: boolean; escena_final_desde: number;
  proporcion_seminario: number; voz_id: string | null; whisper: boolean;
  velocidad: number; volumen_musica_db: number; seminario_s: number; barras_cine: boolean;
  humano: Humano;
}

// (01-11) «Edición humana»: cortes de duración variable, seminario solo en momentos de autoridad, movimiento,
// texto con intención, música por sección y revisión antes de exportar. Apagada = el video de siempre.
interface Humano {
  activo: boolean; fenix_max: number; revisar_antes: boolean; escena_final_desde: number; carpeta_musica: string;
  velocidad_cierre: number; suaves: number; color_calido: boolean; prueba_s: number;
}

interface Toma {
  id: number; tipo: 'stock' | 'seminario' | 'final'; seccion: string; rol: string | null; inicio: number; fin: number;
  duracion: number; texto: string; grande: string | null; keywords: string[]; movimiento: string | null;
  transicion: string | null; miniatura: string | null;
}
interface Reporte {
  clips: number; duracion_media_s: number; desviacion_s: number; variacion_pct: number; mas_corto_s: number;
  mas_largo_s: number; fenix_pct: number; stock_pct: number; escena_final_pct: number; stock_unicos: number;
  efectos: { movimientos: Record<string, number>; transiciones: Record<string, number>; textos_grandes: number;
    whoosh: number; riser: number; pausas_naturales: number };
}
interface Revision { pendiente: boolean; clips: Toma[]; reporte: Reporte | null }

type Que = 'seminario' | 'musica' | 'presentador';

const PASOS: Record<string, string> = {
  tracy: 'Empezando', voz: 'Grabando la voz y sacando los tiempos', visual: 'Eligiendo clips y armando el video',
  entrega: 'Guardando el video', revision: 'Listo para revisar',
};

async function subir(que: Que, f: File): Promise<EstadoTracy> {
  const datos = new FormData();
  datos.append('que', que);
  datos.append('archivo', f);
  const r = await fetch('/api/tracy/archivo', { method: 'POST', body: datos });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error((j as { detail?: string }).detail || `Error ${r.status}`);
  return j as EstadoTracy;
}

function Archivo({ titulo, ruta, existe, que, ayuda, alCambiar }: {
  titulo: string; ruta: string; existe: boolean; que: Que; ayuda: string;
  alCambiar: (e: EstadoTracy) => void;
}) {
  const entrada = useRef<HTMLInputElement>(null);
  const [subiendo, setSubiendo] = useState(false);
  const [msg, setMsg] = useState('');
  return (
    <div className="tr-archivo">
      <div>
        <b>{titulo}</b> <span className={existe ? 'tr-ok' : 'tr-falta'}>{existe ? 'listo' : 'no lo encuentro'}</span>
        <div className="tenue pequeno tr-ruta" title={ruta}>{ruta || '—'}</div>
        {!existe && <div className="tenue pequeno">{ayuda}</div>}
        {msg && <div className="error pequeno">{msg}</div>}
      </div>
      <input ref={entrada} type="file" hidden accept={que === 'seminario' ? 'video/*' : que === 'musica' ? 'audio/*' : 'image/*'}
        onChange={async (ev) => {
          const f = ev.target.files?.[0];
          if (!f) return;
          setSubiendo(true); setMsg('');
          try { alCambiar(await subir(que, f)); } catch (e) { setMsg((e as Error).message); }
          finally { setSubiendo(false); ev.target.value = ''; }
        }} />
      <button className="boton-borde pequeno" disabled={subiendo} onClick={() => entrada.current?.click()}>
        {subiendo ? 'Copiando…' : existe ? 'Cambiar' : 'Elegir archivo'}
      </button>
    </div>
  );
}

export function Tracy() {
  const ir = useNavigate();
  const [est, setEst] = useState<EstadoTracy | null>(null);
  const [guion, setGuion] = useState('');
  const [titulo, setTitulo] = useState('');
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);
  useEffect(() => { api<EstadoTracy>('/api/tracy').then(setEst).catch((e) => setError((e as Error).message)); }, []);

  const caracteres = guion.trim().length;
  const minutos = caracteres / 13.5 / 60;          // ~13,5 caracteres por segundo de voz
  const crear = async (prueba = false) => {
    setError(''); setEnviando(true);
    try {
      const v = await api<VideoDetalle>('/api/tracy/videos', { cuerpo: { guion, titulo, prueba } });
      ir(`/tracy/${v.slug}`);
    } catch (e) { setError((e as Error).message); } finally { setEnviando(false); }
  };
  const ajustar = async (cuerpo: Record<string, number | boolean>) => {
    try { setEst(await api<EstadoTracy>('/api/tracy/ajustes', { cuerpo })); }
    catch (e) { setError((e as Error).message); }
  };
  const ajustarHumano = async (cuerpo: Partial<Humano>) => {
    try { setEst(await api<EstadoTracy>('/api/tracy/humano', { cuerpo })); }
    catch (e) { setError((e as Error).message); }
  };

  return (
    <div className="pagina tracy">
      <h1>Canal Tracy</h1>
      <p className="tenue">Pega el guion y Xandart hace el resto: voz, clips de Pexels, tramos del seminario en blanco y
        negro, subtítulos amarillos, música de fondo suave y la escena final. Cada clip dura 30 segundos o menos.</p>

      {est && (
        <section className="rev-tarjeta">
          <h2>Archivos del canal</h2>
          <Archivo titulo="Video del seminario" que="seminario" ruta={est.clip_base} existe={est.clip_existe}
            ayuda="Déjalo en esa carpeta con ese nombre, o elígelo aquí." alCambiar={setEst} />
          <Archivo titulo="Música de fondo" que="musica" ruta={est.musica} existe={est.musica_existe}
            ayuda="Opcional: sin música, el video sale solo con la voz." alCambiar={setEst} />
          <Archivo titulo="Presentador de la escena final" que="presentador" ruta={est.presentador}
            existe={est.presentador_existe} ayuda="Una imagen (mejor PNG sin fondo). Va a la izquierda, en blanco y negro."
            alCambiar={setEst} />
          <label className="campo">Cada corte del seminario dura {Math.round(est.seminario_s)} s; después van 1, 2 o los
            clips de stock que hagan falta, y así se intercala hasta la escena final
            <input type="range" min={3} max={12} step={1} defaultValue={est.seminario_s}
              onMouseUp={(e) => ajustar({ seminario_s: +(e.target as HTMLInputElement).value })}
              onTouchEnd={(e) => ajustar({ seminario_s: +(e.target as HTMLInputElement).value })}
              onKeyUp={(e) => ajustar({ seminario_s: +(e.target as HTMLInputElement).value })} />
          </label>
          <label className="campo tr-check">
            <span><input type="checkbox" checked={est.barras_cine}
              onChange={(e) => ajustar({ barras_cine: e.target.checked })} /> Barras negras de cine arriba y abajo</span>
          </label>
          <label className="campo">
            {est.escena_final_desde >= 1 ? 'Sin escena final (clips hasta el final)'
              : `La escena final empieza en el ${Math.round(est.escena_final_desde * 100)} % del video`}
            <input type="range" min={0.1} max={1} step={0.05} defaultValue={est.escena_final_desde}
              onMouseUp={(e) => ajustar({ escena_final_desde: +(e.target as HTMLInputElement).value })}
              onTouchEnd={(e) => ajustar({ escena_final_desde: +(e.target as HTMLInputElement).value })}
              onKeyUp={(e) => ajustar({ escena_final_desde: +(e.target as HTMLInputElement).value })} />
            <span className="tenue pequeno">Fondo de naturaleza en blanco y negro con partículas, el presentador a un
              lado, el botón Suscríbete y las ondas de la voz.</span>
          </label>
          <label className="campo">Velocidad de la voz: {est.velocidad.toFixed(2).replace('.', ',')}× (1 = normal)
            <input type="range" min={0.8} max={1.3} step={0.05} defaultValue={est.velocidad}
              onMouseUp={(e) => ajustar({ velocidad: +(e.target as HTMLInputElement).value })}
              onTouchEnd={(e) => ajustar({ velocidad: +(e.target as HTMLInputElement).value })}
              onKeyUp={(e) => ajustar({ velocidad: +(e.target as HTMLInputElement).value })} />
          </label>
          <label className="campo">Volumen de la música: {Math.round((est.volumen_musica_db + 30) / 24 * 100)} %
            <input type="range" min={-30} max={-6} step={1} defaultValue={est.volumen_musica_db}
              onMouseUp={(e) => ajustar({ volumen_musica_db: +(e.target as HTMLInputElement).value })}
              onTouchEnd={(e) => ajustar({ volumen_musica_db: +(e.target as HTMLInputElement).value })}
              onKeyUp={(e) => ajustar({ volumen_musica_db: +(e.target as HTMLInputElement).value })} />
            <span className="tenue pequeno">Siempre por debajo de la voz; baja un poco sola cuando hablas.</span>
          </label>
          {!est.whisper && <p className="rev-aviso">Falta Whisper (los tiempos de la voz). Vuelve a correr «Instalar Xandart
            Nueva» y queda listo.</p>}
        </section>
      )}

      {est && <EdicionHumana h={est.humano} ajustar={ajustarHumano} />}

      <section className="rev-tarjeta">
        <h2>Nuevo video</h2>
        <label className="campo">Título (opcional; si no, la primera frase)
          <input value={titulo} onChange={(e) => setTitulo(e.target.value)} maxLength={120} />
        </label>
        <textarea className="tr-guion" value={guion} onChange={(e) => setGuion(e.target.value)}
          placeholder="Pega aquí el guion completo…" />
        <div className="fila-botones">
          <span className="tenue pequeno">{caracteres.toLocaleString('es-CO')} caracteres · ≈ {minutos.toFixed(1)} min de voz</span>
          <span className="crece" />
          {est?.humano.activo && (
            <button className="boton-borde" disabled={enviando || caracteres < 40 || !est?.clip_existe || !est?.whisper}
              title="Solo los primeros minutos del guion, para revisar la edición antes de hacer videos completos"
              onClick={() => crear(true)}>Probar {Math.round(est.humano.prueba_s / 60)} minutos</button>
          )}
          <button className="boton-primario" disabled={enviando || caracteres < 40 || !est?.clip_existe || !est?.whisper}
            onClick={() => crear(false)}>{enviando ? 'Empezando…' : 'Hacer el video'}</button>
        </div>
        {est && !est.clip_existe && <p className="tenue pequeno">Primero elige el video del seminario.</p>}
        {error && <div className="rev-error">{error}</div>}
      </section>
    </div>
  );
}

function EdicionHumana({ h, ajustar }: { h: Humano; ajustar: (c: Partial<Humano>) => void }) {
  const [carpeta, setCarpeta] = useState(h.carpeta_musica);
  return (
    <section className="rev-tarjeta">
      <h2>Edición humana</h2>
      <label className="campo tr-check">
        <span><input type="checkbox" checked={h.activo} onChange={(e) => ajustar({ activo: e.target.checked })} /> Usar la
          edición humana en los videos nuevos</span>
        <span className="tenue pequeno">Cortes de duración variable al final de cada frase, el seminario solo en los momentos
          de autoridad, movimiento suave, la palabra clave en amarillo, textos grandes en las reglas y el CTA, música por
          sección y una revisión antes de exportar. Apagada, el video sale como siempre.</span>
      </label>
      {h.activo && (<>
        <label className="campo">El seminario ocupa como mucho el {Math.round(h.fenix_max * 100)} % del video
          <input type="range" min={0.1} max={0.6} step={0.05} defaultValue={h.fenix_max}
            onMouseUp={(e) => ajustar({ fenix_max: +(e.target as HTMLInputElement).value })}
            onTouchEnd={(e) => ajustar({ fenix_max: +(e.target as HTMLInputElement).value })}
            onKeyUp={(e) => ajustar({ fenix_max: +(e.target as HTMLInputElement).value })} />
        </label>
        <label className="campo">
          {h.escena_final_desde >= 1 ? 'Sin escena final' : `Escena final desde el ${Math.round(h.escena_final_desde * 100)} % del video`}
          <input type="range" min={0.5} max={1} step={0.05} defaultValue={h.escena_final_desde}
            onMouseUp={(e) => ajustar({ escena_final_desde: +(e.target as HTMLInputElement).value })}
            onTouchEnd={(e) => ajustar({ escena_final_desde: +(e.target as HTMLInputElement).value })}
            onKeyUp={(e) => ajustar({ escena_final_desde: +(e.target as HTMLInputElement).value })} />
        </label>
        <label className="campo tr-check">
          <span><input type="checkbox" checked={h.revisar_antes} onChange={(e) => ajustar({ revisar_antes: e.target.checked })} />
            {' '}Detenerse para revisar antes de exportar</span>
        </label>
        <label className="campo tr-check">
          <span><input type="checkbox" checked={h.color_calido} onChange={(e) => ajustar({ color_calido: e.target.checked })} />
            {' '}Tono cálido parejo en todo el stock</span>
        </label>
        <label className="campo">Carpeta con la música por sección (opcional)
          <input value={carpeta} placeholder="C:\Users\USUARIO\Videos\musica tracy" onChange={(e) => setCarpeta(e.target.value)}
            onBlur={() => carpeta !== h.carpeta_musica && ajustar({ carpeta_musica: carpeta })} />
          <span className="tenue pequeno">Pistas con licencia cuyo nombre empiece por gancho, cuerpo, venta o cierre (por ejemplo
            «cuerpo 2.mp3»). Si falta alguna, se usa la música de siempre.</span>
        </label>
      </>)}
    </section>
  );
}

const SECCION: Record<string, string> = { gancho: 'Gancho', cuerpo: 'Cuerpo', venta: 'CTA y venta', cierre: 'Cierre' };

function RevisionTracy({ slug, r, alCambiar, exportar }: {
  slug: string; r: Revision; alCambiar: (r: Revision) => void; exportar: () => void;
}) {
  const [ocupado, setOcupado] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [soloClave, setSoloClave] = useState(true);
  const accion = async (id: number, a: string, texto?: string) => {
    setOcupado(id); setError('');
    try { alCambiar(await api<Revision>(`/api/tracy/videos/${slug}/revision/${id}`, { cuerpo: { accion: a, texto } })); }
    catch (e) { setError((e as Error).message); } finally { setOcupado(null); }
  };
  const tomas = soloClave ? r.clips.filter((x) => x.seccion !== 'cuerpo') : r.clips;
  const reloj = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  return (
    <section className="rev-tarjeta">
      <h2>Revisa antes de exportar</h2>
      <p className="tenue pequeno">Marcados: el gancho, el CTA y la venta, y el cierre. Puedes cambiar el clip, alargar o acortar una
        toma (siempre hasta el final de una frase) o cambiar el texto grande. Luego dale «Exportar».</p>
      <label className="tr-check pequeno"><input type="checkbox" checked={soloClave} onChange={(e) => setSoloClave(e.target.checked)} />
        {' '}Ver solo gancho, venta y cierre</label>
      {error && <div className="rev-error">{error}</div>}
      <div className="tr-tomas">
        {tomas.map((x) => (
          <div key={x.id} className={`tr-toma tr-${x.seccion}`}>
            {x.miniatura ? <img src={archivo(slug, x.miniatura)} alt="" /> : <div className="tr-sinmini" />}
            <div className="tr-toma-info">
              <div className="pequeno"><b>{SECCION[x.seccion] ?? x.seccion}</b> · {reloj(x.inicio)} · {x.duracion.toFixed(1)} s ·{' '}
                {x.tipo === 'seminario' ? 'Seminario' : x.tipo === 'final' ? 'Escena final' : 'Stock'}
                {x.rol && x.rol !== 'normal' ? ` · ${x.rol.replace('_', ' ')}` : ''}</div>
              <div className="pequeno tenue">{x.texto}</div>
              {x.tipo !== 'final' && (
                <label className="pequeno">Texto grande{' '}
                  <input defaultValue={x.grande ?? ''} placeholder="(ninguno)" maxLength={40}
                    onBlur={(e) => (e.target.value || null) !== x.grande && accion(x.id, 'texto', e.target.value)} />
                </label>
              )}
              {x.tipo !== 'final' && (
                <div className="fila-botones">
                  <button className="boton-borde pequeno" disabled={ocupado !== null} onClick={() => accion(x.id, 'otro_stock')}>Otro clip de stock</button>
                  {x.tipo !== 'seminario' && <button className="boton-borde pequeno" disabled={ocupado !== null} onClick={() => accion(x.id, 'seminario')}>Usar el seminario</button>}
                  <button className="boton-borde pequeno" disabled={ocupado !== null} onClick={() => accion(x.id, 'acortar')}>− Más corta</button>
                  <button className="boton-borde pequeno" disabled={ocupado !== null} onClick={() => accion(x.id, 'alargar')}>+ Más larga</button>
                  {ocupado === x.id && <span className="tenue pequeno">Cambiando…</span>}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="fila-botones"><span className="crece" />
        <button className="boton-primario" onClick={exportar}>Exportar el video</button></div>
    </section>
  );
}

function ReporteEdicion({ r }: { r: Reporte }) {
  const e = r.efectos;
  return (
    <section className="rev-tarjeta">
      <h2>Reporte de edición</h2>
      <ul className="pequeno">
        <li>{r.clips} tomas · duración media {r.duracion_media_s} s (de {r.mas_corto_s} a {r.mas_largo_s} s) · variación {r.variacion_pct} %</li>
        <li>Seminario {r.fenix_pct} % · stock {r.stock_pct} %{r.escena_final_pct ? ` · escena final ${r.escena_final_pct} %` : ''}</li>
        <li>{r.stock_unicos} clips de stock distintos</li>
        <li>Movimientos: {Object.entries(e.movimientos).map(([k, v]) => `${k.replace('_', ' ')} ${v}`).join(' · ')}</li>
        <li>Transiciones: {Object.entries(e.transiciones).map(([k, v]) => `${k} ${v}`).join(' · ')}</li>
        <li>Textos grandes {e.textos_grandes} · whoosh {e.whoosh} · subidas antes de revelación {e.riser} · pausas naturales {e.pausas_naturales}</li>
      </ul>
    </section>
  );
}

export function TracyVideo() {
  const { slug = '' } = useParams();
  const [v, setV] = useState<VideoDetalle | null>(null);
  const [rev, setRev] = useState<Revision | null>(null);
  const [error, setError] = useState('');
  const cargar = useCallback(async () => {
    try { setV(await api<VideoDetalle>(`/api/videos/${slug}`)); setError(''); }
    catch (e) { setError((e as Error).message); }
  }, [slug]);
  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => {
    if (v && !v.trabajo?.activo) api<Revision>(`/api/tracy/videos/${slug}/revision`).then(setRev).catch(() => setRev(null));
  }, [v, slug]);
  const exportar = async () => {
    setError('');
    try { setV(await api<VideoDetalle>(`/api/tracy/videos/${slug}/exportar`, { cuerpo: {} })); setRev(null); }
    catch (e) { setError((e as Error).message); }
  };
  useEffect(() => {
    if (!v?.trabajo?.activo) return;
    const id = window.setTimeout(cargar, 2000);
    return () => window.clearTimeout(id);
  }, [v, cargar]);
  const seguir = async (permiso = false) => {
    setError('');
    try { setV(await api<VideoDetalle>(`/api/tracy/videos/${slug}/seguir`, { cuerpo: { permiso } })); }
    catch (e) { setError((e as Error).message); }
  };

  if (error && !v) return <div className="pagina"><p className="error">{error}</p><Link to="/tracy">← Canal Tracy</Link></div>;
  if (!v) return <div className="pagina"><p className="tenue">Cargando…</p></div>;
  const t = v.trabajo;
  const trabajando = !!t?.activo;
  return (
    <div className="pagina revision">
      <div className="rev-cab">
        <Link to="/tracy" className="tenue pequeno">← Canal Tracy</Link>
        <span className="crece" />
        <Link className="boton-borde pequeno" to={`/videos/${slug}/miniatura`}>Miniatura</Link>
        <span className="chip-gasto">Gastado: {v.costo}</span>
      </div>
      <h1 className="rev-titulo">{v.titulo}</h1>
      {trabajando && t && (
        <section className="rev-tarjeta">
          <b>{PASOS[t.paso] ?? t.paso}</b>
          <div className="barra-progreso"><i style={{ width: `${Math.round(t.progreso * 100)}%` }} /></div>
          <span className="tenue pequeno">{t.mensaje} · {Math.floor(t.segundos / 60)} min {t.segundos % 60} s</span>
          {t.paso === 'voz' && <p className="tenue pequeno">La primera vez Whisper baja su modelo (unos 480 MB): ese paso tarda un rato más.</p>}
        </section>
      )}
      {!trabajando && t?.error && (
        <div className="rev-error">
          No se pudo terminar: {t.error}
          <div className="fila-botones">
            <button className="boton-borde pequeno" onClick={() => seguir(false)}>Seguir donde iba</button>
            {/máximo|FRENO|tope/.test(t.error) && (
              <button className="boton-borde pequeno" onClick={() => {
                if (window.confirm(`Este video ya lleva ${v.costo}.\n\n¿Das permiso para pasar el máximo?`)) seguir(true);
              }}>Dar permiso y seguir</button>
            )}
          </div>
          <div className="tenue pequeno">Lo que ya se hizo (voz, clips bajados) no se vuelve a pagar.</div>
        </div>
      )}
      {!trabajando && rev?.pendiente && <RevisionTracy slug={slug} r={rev} alCambiar={setRev} exportar={exportar} />}
      {!trabajando && !t && !v.video && !rev?.pendiente && (
        <div className="rev-tarjeta">
          <p>Este video quedó a medias.</p>
          <button className="boton-primario" onClick={() => seguir(false)}>Seguir donde iba</button>
        </div>
      )}
      {v.video && !trabajando && (
        <section className="rev-tarjeta">
          <h2>Tu video está listo</h2>
          <video className="rev-video" controls preload="metadata" src={archivo(slug, v.video)} />
          <div className="fila-botones">
            <a className="boton-primario" href={`${archivo(slug, v.video)}?descargar=true`}>Descargar MP4</a>
            <a className="boton-borde" href={`${archivo(slug, 'render/final.srt')}?descargar=true`}>Subtítulos (SRT)</a>
            <Link className="boton-borde" to={`/videos/${slug}/miniatura`}>Hacer la miniatura</Link>
          </div>
          <p className="tenue pequeno">También quedó una copia en tu carpeta de Videos → Xandart.</p>
          {rev?.reporte && <ReporteEdicion r={rev.reporte} />}
          <div className="fila-botones">
            <button className="boton-borde pequeno" onClick={() => {
              if (window.confirm('Se vuelve a armar con los ajustes de ahora (velocidad de la voz, música, escena final).\n\n'
                + 'Si cambiaste la velocidad de la voz, la voz se graba otra vez y se paga (unos pocos cientos de pesos). '
                + 'Los clips ya bajados no se vuelven a bajar.\n\n¿Seguir?')) seguir(false);
            }}>Volver a armar con los ajustes de ahora</button>
          </div>
        </section>
      )}
    </div>
  );
}
