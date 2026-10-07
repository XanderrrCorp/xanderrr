import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';

// Videos nuevos de El Calvo Explica hechos por Xandart sola: escribes el tema → Claude escribe el guion (con su lista
// de dudas) → Claude arma las escenas y las revisa mirándolas → voz, Whisper, música y render.

interface Trabajo { paso: string; progreso: number; mensaje: string; activo: boolean; error: string | null }
interface Video {
  slug: string; titulo: string; temas: number; guion: string | null; dudas: string | null;
  guion_info: { avisos: string[] } | null; escenas: boolean; hojas: string[];
  escenas_info: { escenas: number; notas: string[] } | null; video: boolean; trabajo: Trabajo | null;
  costo_voz: { caracteres: number; cop: string } | null;
  informe: { duracion: number; tiempo_total_s: number; costos: Record<'guion' | 'voz' | 'imagenes', { cop: string }>;
             video: string } | null;
}

function Detalle({ slug }: { slug: string }) {
  const [v, setV] = useState<Video | null>(null);
  const [texto, setTexto] = useState('');
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const cargar = useCallback(async () => {
    try { const x = await api<Video>(`/api/explica/videos/${slug}`); setV(x); setVersion(Date.now()); }
    catch (e) { setError((e as Error).message); }
  }, [slug]);
  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => { if (v?.guion != null) setTexto(v.guion); }, [v?.guion]);
  useEffect(() => {
    if (!v?.trabajo?.activo) return;
    const id = setInterval(cargar, 2000);
    return () => clearInterval(id);
  }, [v?.trabajo?.activo, cargar]);
  const accion = async (ruta: string, cuerpo: unknown = {}, metodo?: string) => {
    setError('');
    try { setV(await api<Video>(`/api/explica/videos/${slug}${ruta}`, { cuerpo, metodo })); }
    catch (e) { setError((e as Error).message); }
  };
  if (!v) return <p>{error || 'Cargando…'}</p>;
  const ocupado = !!v.trabajo?.activo;
  return (
    <section className="rev-tarjeta">
      <h2>{v.titulo}</h2>
      {v.trabajo && (
        <div>
          <div className="barra-progreso"><i style={{ width: `${Math.round(v.trabajo.progreso * 100)}%` }} /></div>
          <div className="pequeno">{v.trabajo.error ? <span className="error">Error: {v.trabajo.error}</span> : v.trabajo.mensaje}</div>
        </div>
      )}
      {error && <p className="error">{error}</p>}

      <h3>1. Guion</h3>
      {v.guion == null ? <p className="tenue">Claude lo está escribiendo…</p> : (
        <>
          <textarea value={texto} onChange={(e) => setTexto(e.target.value)} rows={14} style={{ width: '100%' }} />
          {texto !== v.guion && <button className="boton-borde pequeno" onClick={() => accion('/guion', { texto }, 'PUT')}>
            Guardar cambios</button>}
          {!!v.guion_info?.avisos?.length && <p className="error pequeno">Revisor: {v.guion_info.avisos.join(' · ')}</p>}
          {v.dudas && <details open><summary><b>Dudas para revisar</b></summary>
            <pre className="pequeno" style={{ whiteSpace: 'pre-wrap' }}>{v.dudas}</pre></details>}
        </>
      )}

      <h3>2. Escenas</h3>
      <button className="boton" disabled={ocupado || v.guion == null} onClick={() => accion('/escenas')}>
        {v.escenas ? 'Volver a armar las escenas' : 'Armar las escenas (gratis)'}</button>
      {v.escenas_info && <p className="pequeno">{v.escenas_info.escenas} escenas
        {v.escenas_info.notas.length > 0 && ` · ${v.escenas_info.notas.length} nota(s): ${v.escenas_info.notas.slice(0, 3).join(' · ')}`}</p>}
      <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
        {v.hojas.map((h) => <img key={h} src={`/api/explica/videos/${slug}/hoja/${h}?v=${version}`} alt={h}
          style={{ width: '100%', border: '1px solid #ddd', borderRadius: 6 }} />)}
      </div>

      <h3>3. Video</h3>
      <p className="pequeno">Voz de Peligro Tropical, tiempos con Whisper, música tranquila de tu biblioteca.
        {v.costo_voz && <> La voz cuesta unos <b>{v.costo_voz.cop}</b> ({v.costo_voz.caracteres} caracteres).</>}</p>
      <button className="boton" disabled={ocupado || !v.escenas} onClick={() => accion('/video', { permiso: false })}>
        {v.video ? 'Volver a hacer el video' : 'Hacer el video'}</button>
      {v.video && <video src={`/api/explica/videos/${slug}/archivo?v=${version}`} controls
        style={{ width: '100%', borderRadius: 8, marginTop: 10 }} />}
      {v.informe && <p className="pequeno">Duración {Math.round(v.informe.duracion / 60 * 10) / 10} min · costo: guion{' '}
        {v.informe.costos.guion.cop}, voz {v.informe.costos.voz.cop}, imágenes {v.informe.costos.imagenes.cop} ·
        guardado en {v.informe.video}</p>}
    </section>
  );
}

export function ExplicaNuevo() {
  const [lista, setLista] = useState<{ slug: string; titulo: string; temas: number }[]>([]);
  const [titulo, setTitulo] = useState('');
  const [temas, setTemas] = useState(9);
  const [datos, setDatos] = useState('');
  const [elegido, setElegido] = useState<string | null>(null);
  const [error, setError] = useState('');
  const cargar = useCallback(() => { api<typeof lista>('/api/explica/videos').then(setLista).catch(() => {}); }, []);
  useEffect(() => { cargar(); }, [cargar]);
  const crear = async () => {
    setError('');
    try {
      const v = await api<{ slug: string }>('/api/explica/videos', { cuerpo: { titulo, temas, datos } });
      setElegido(v.slug); setTitulo(''); setDatos(''); cargar();
    } catch (e) { setError((e as Error).message); }
  };
  return (
    <>
      <section className="rev-tarjeta">
        <h2>Video nuevo (Xandart lo hace sola)</h2>
        <label className="campo">Tema del video
          <input value={titulo} onChange={(e) => setTitulo(e.target.value)}
            placeholder="Ej.: Cosas raras que hace tu cerebro cuando duermes" />
        </label>
        <label className="campo">Número de temas: {temas}
          <input type="range" min={6} max={12} value={temas} onChange={(e) => setTemas(+e.target.value)} />
        </label>
        <label className="campo">Datos que quieres usar (opcional: tu lista de casos y datos; si la pones, Claude usa solo esos)
          <textarea rows={4} value={datos} onChange={(e) => setDatos(e.target.value)} />
        </label>
        <button className="boton" disabled={titulo.trim().length < 4} onClick={crear}>Escribir el guion (gratis)</button>
        {error && <p className="error">{error}</p>}
        {lista.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <b>Tus videos:</b>{' '}
            {lista.map((x) => (
              <button key={x.slug} className={`boton-borde pequeno ${elegido === x.slug ? 'activo' : ''}`}
                style={{ margin: 4 }} onClick={() => setElegido(x.slug)}>{x.titulo}</button>
            ))}
          </div>
        )}
      </section>
      {elegido && <Detalle key={elegido} slug={elegido} />}
    </>
  );
}
