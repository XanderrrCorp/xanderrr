import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';

// Código del Éxito (videos largos): pegas el guion con sus etiquetas [PROFESOR], [STOCK: palabras en inglés] y [AURA].
// Xandart hace la voz, Claude arma las escenas del Profesor, baja los clips de Pexels (sin repetir ninguno), arma todo
// con el mismo color, viñeta y grano, música suave y subtítulos, y te deja el video con sus capítulos.

interface Faltan { carpeta: string; profesor: boolean; efectos: boolean; musica: number; node: boolean; pexels: boolean; rhubarb: boolean }
interface Resumen { slug: string; titulo: string; estado: 'nuevo' | 'haciendo' | 'listo' | 'error'; mensaje: string; final: boolean }
interface Costo { bloques: number; partes: number; letras: number; minutos: number; costo_voz: string; por_tipo: Record<string, number> }
interface Detalle extends Resumen { costo: Costo; log: string[]; error: string | null; capitulos: string; bloques_txt: string; creditos: string; trabajando: boolean }

const EJEMPLO = `[PROFESOR]
Hay una razón por la que casi nadie termina lo que empieza...

[STOCK: man staring at laptop, messy desk]
Piensa en la última vez que quisiste empezar algo importante...

[AURA]
Cierra los ojos un momento. Respira profundo...`;

const ESTADO: Record<Resumen['estado'], string> = { nuevo: 'Sin empezar', haciendo: 'Haciéndose', listo: 'Listo', error: 'Se detuvo' };

export function CodigoExito() {
  const [faltan, setFaltan] = useState<Faltan | null>(null);
  const [videos, setVideos] = useState<Resumen[]>([]);
  const [titulo, setTitulo] = useState('');
  const [guion, setGuion] = useState('');
  const [abierto, setAbierto] = useState<Detalle | null>(null);
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);

  const cargar = useCallback(() => api<{ faltan: Faltan; videos: Resumen[] }>('/api/codigo-exito')
    .then((r) => { setFaltan(r.faltan); setVideos(r.videos); }).catch((x) => setError((x as Error).message)), []);
  const abrir = useCallback((slug: string) => api<Detalle>(`/api/codigo-exito/videos/${slug}`).then(setAbierto)
    .catch((x) => setError((x as Error).message)), []);
  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => {
    if (!abierto || !(abierto.trabajando || abierto.estado === 'haciendo')) return;
    const id = setInterval(() => { abrir(abierto.slug); cargar(); }, 3000);
    return () => clearInterval(id);
  }, [abierto, abrir, cargar]);

  const crear = async () => {
    setError(''); setEnviando(true);
    try {
      const r = await api<Resumen>('/api/codigo-exito/videos', { cuerpo: { titulo, guion } });
      setTitulo(''); setGuion(''); await cargar(); await abrir(r.slug);
    } catch (x) { setError((x as Error).message); }
    setEnviando(false);
  };
  const hacer = async (slug: string) => {
    setError('');
    try { setAbierto(await api<Detalle>(`/api/codigo-exito/videos/${slug}/hacer`, { cuerpo: { permiso: true } })); cargar(); }
    catch (x) { setError((x as Error).message); }
  };
  const carpeta = (que: string) => api('/api/codigo-exito/abrir', { cuerpo: { que } }).catch(() => undefined);

  const avisos = faltan ? [
    !faltan.profesor && 'Faltan las capas del Profesor: copia sus PNG (cabeza_base, cuerpo, bocas…) en la carpeta «profesor».',
    !faltan.pexels && 'Falta tu clave de Pexels (Ajustes): sin ella los bloques de stock salen como aura.',
    !faltan.node && 'Falta Node.js en este PC (lo usa Remotion para armar el video). Instálalo desde nodejs.org (LTS).',
    !faltan.efectos && 'Sin tus efectos de sonido: copia whoosh.wav, pop.wav, clic.wav… en la carpeta «sfx» (si no, va sin efectos).',
    faltan.musica === 0 && 'Sin música en la carpeta «musica»: se usa una música suave hecha por código.',
  ].filter(Boolean) as string[] : [];

  return (
    <div className="pagina">
      <h1>Código del Éxito</h1>
      <p className="tenue">Pega el guion con sus etiquetas: <b>[PROFESOR]</b> (gancho, cada regla y los llamados),
        <b> [STOCK: palabras en inglés]</b> (clips de Pexels) y <b>[AURA]</b> (pasajes de reflexión). Xandart hace la voz,
        las escenas del Profesor, el stock (sin repetir ningún clip), la música y los subtítulos.</p>
      {error && <p className="error">{error}</p>}

      {avisos.length > 0 && (
        <section className="rev-tarjeta">
          <b>Antes de hacer el video</b>
          <ul className="pequeno">{avisos.map((a) => <li key={a}>{a}</li>)}</ul>
          <p className="pequeno tenue">Carpeta: {faltan?.carpeta}{' '}
            <button className="boton-borde pequeno" onClick={() => carpeta('recursos')}>Abrir carpeta</button></p>
        </section>
      )}

      <section className="rev-tarjeta">
        <input placeholder="Título del video" value={titulo} onChange={(e) => setTitulo(e.target.value)} style={{ width: '100%', marginBottom: 8 }} />
        <textarea rows={12} value={guion} onChange={(e) => setGuion(e.target.value)} placeholder={EJEMPLO} style={{ width: '100%' }} />
        <button className="boton" disabled={enviando || titulo.trim().length < 3 || guion.trim().length < 40} onClick={crear}>
          Guardar guion y ver el costo</button>
      </section>

      {abierto && (
        <section className="rev-tarjeta">
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
            <h2 style={{ margin: 0 }}>{abierto.titulo}</h2>
            <span className={abierto.estado === 'error' ? 'error pequeno' : 'pequeno'}>{ESTADO[abierto.estado]}</span>
          </div>
          <p className="pequeno">{abierto.costo.bloques} bloques ({abierto.costo.por_tipo.profesor} del Profesor,
            {' '}{abierto.costo.por_tipo.stock} de stock, {abierto.costo.por_tipo.aura} de aura) · unos {abierto.costo.minutos} min ·
            {' '}voz: <b>{abierto.costo.costo_voz}</b> (las escenas, el stock y la música no cuestan)</p>
          {abierto.estado !== 'haciendo' && !abierto.trabajando && (
            <button className="boton" onClick={() => hacer(abierto.slug)}>
              {abierto.estado === 'listo' ? 'Volver a hacerlo (lo hecho no se repite)' : abierto.estado === 'error' ? 'Seguir donde iba' : `Hacer el video (${abierto.costo.costo_voz})`}</button>
          )}
          {abierto.error && <p className="error pequeno">{abierto.error}</p>}
          {(abierto.trabajando || abierto.estado === 'haciendo') && <p className="pequeno">Haciéndose… puedes cerrar esta página; sigue solo.</p>}
          {abierto.log.length > 0 && <pre className="pequeno" style={{ maxHeight: 220, overflow: 'auto', whiteSpace: 'pre-wrap' }}>{abierto.log.join('\n')}</pre>}
          {abierto.final && <>
            <video src={`/api/codigo-exito/videos/${abierto.slug}/final.mp4`} controls style={{ width: '100%', borderRadius: 12 }} />
            <p className="pequeno">También quedó en tu carpeta de Videos{' '}
              <button className="boton-borde pequeno" onClick={() => carpeta('videos')}>Abrir</button></p>
          </>}
          {abierto.capitulos && <><b>Capítulos (para la descripción)</b>
            <pre className="pequeno" style={{ whiteSpace: 'pre-wrap' }}>{abierto.capitulos}</pre>
            <button className="boton-borde pequeno" onClick={() => navigator.clipboard.writeText(abierto.capitulos)}>Copiar</button></>}
          {abierto.creditos && <details><summary className="pequeno">Clips de Pexels usados</summary>
            <pre className="pequeno" style={{ whiteSpace: 'pre-wrap' }}>{abierto.creditos}</pre></details>}
          <p className="pequeno tenue">Al subirlo: marca en YouTube que tiene contenido hecho con IA (voz y animación).</p>
        </section>
      )}

      <h2>Tus videos</h2>
      {videos.length === 0 ? <p className="tenue">Todavía no hay videos.</p> : (
        <div style={{ display: 'grid', gap: 8 }}>
          {videos.map((v) => (
            <button key={v.slug} className="rev-tarjeta" style={{ textAlign: 'left', padding: 12, cursor: 'pointer' }} onClick={() => abrir(v.slug)}>
              <b>{v.titulo}</b> <span className="pequeno tenue">· {ESTADO[v.estado]}</span>
              {v.mensaje && <div className="pequeno tenue">{v.mensaje}</div>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
