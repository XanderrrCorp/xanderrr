import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';

// El Calvo Explica (nombre provisional): «TODAS las X explicadas en N minutos». Por ahora: las 3 ilustraciones de
// muestra para aprobar el estilo (Google, con el personaje como referencia). Lo demás llega en los pasos siguientes.

interface EstadoExplica {
  canal: { clave: string; nombre: string };
  costo_muestras: { usd?: number; cop?: string; proveedor?: string; modelo?: string; error?: string };
  muestras: { archivos: string[]; costo_total: string; proveedor: string; modelo: string } | null;
  trabajo: Trabajo | null;
  video: {
    video: boolean; titulo: string; costo_voz: { caracteres: number; cop: string }; trabajo: Trabajo | null;
    informe: { duracion: number; tiempo_total_s: number; costos: Record<'guion' | 'voz' | 'imagenes', { cop: string }>;
               musica: { nombre_original: string } | null; video: string } | null;
  };
  tema_prueba: {
    video: boolean; costo_voz: { caracteres: number; cop: string }; trabajo: Trabajo | null;
    informe: { duracion: number; tiempo_total_s: number; render: { segundos_total: number; procesos: number };
               costos: Record<'guion' | 'voz' | 'imagenes', { cop: string }>; avisos_guion: string[];
               avisos_ritmo: string[]; musica: { nombre_original: string } | null; video: string } | null;
  };
}
interface Trabajo { paso: string; progreso: number; mensaje: string; activo: boolean; error: string | null }

export function Explica() {
  const [est, setEst] = useState<EstadoExplica | null>(null);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const cargar = useCallback(async () => {
    try { const e = await api<EstadoExplica>('/api/explica'); setEst(e); setVersion(Date.now()); }
    catch (e) { setError((e as Error).message); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => {
    if (!est?.trabajo?.activo && !est?.tema_prueba.trabajo?.activo && !est?.video.trabajo?.activo) return;
    const id = setInterval(cargar, 2000);
    return () => clearInterval(id);
  }, [est?.trabajo?.activo, est?.tema_prueba.trabajo?.activo, est?.video.trabajo?.activo, cargar]);

  const hacerVideo = async () => {
    setError('');
    try { setEst(await api<EstadoExplica>('/api/explica/video', { cuerpo: { permiso: false } })); }
    catch (e) { setError((e as Error).message); }
  };
  const hacerTema = async () => {
    setError('');
    try { setEst(await api<EstadoExplica>('/api/explica/tema-prueba', { cuerpo: { permiso: false } })); }
    catch (e) { setError((e as Error).message); }
  };
  const generar = async () => {
    setError('');
    try { setEst(await api<EstadoExplica>('/api/explica/muestras', { cuerpo: { permiso: false } })); }
    catch (e) { setError((e as Error).message); }
  };

  if (!est) return <div className="pagina"><h1>El Calvo Explica</h1>{error && <p className="error">{error}</p>}</div>;
  const t = est.trabajo;
  const c = est.costo_muestras;
  return (
    <div className="pagina tracy">
      <h1>{est.canal.nombre}</h1>
      <p className="tenue">TODAS las X explicadas en N minutos. Fondo blanco, tu personaje y animación por código.</p>
      <section className="rev-tarjeta">
        <h2>Ilustraciones de muestra</h2>
        <p>Tres escenas del primer video (muñeca en primer plano, piel de gallina, dentista) para ver si el personaje
          se mantiene. Se generan con Google ({c.modelo || '—'}) con la
          imagen del personaje como referencia.</p>
        {c.error ? <p className="error pequeno">{c.error}</p>
          : <p>Costo de las 3: <b>unos {c.cop}</b>.</p>}
        <button className="boton" disabled={!!t?.activo} onClick={generar}>
          {t?.activo ? 'Generando…' : est.muestras ? `Volver a generar (unos ${c.cop})` : `Generar las 3 muestras (unos ${c.cop})`}
        </button>
        {t && (
          <div>
            <div className="barra-progreso"><i style={{ width: `${Math.round(t.progreso * 100)}%` }} /></div>
            <div className="pequeno">{t.error ? <span className="error">Error: {t.error}</span> : t.mensaje}</div>
          </div>
        )}
        {error && <p className="error">{error}</p>}
      </section>
      <section className="rev-tarjeta">
        <h2>Video completo: {est.video.titulo}</h2>
        <p>Los 12 temas con voz, tiempos de cada palabra, animación y música tranquila. La voz cuesta unos{' '}
          <b>{est.video.costo_voz.cop}</b> ({est.video.costo_voz.caracteres} caracteres); lo ya grabado no se vuelve a pagar.</p>
        <button className="boton" disabled={!!est.video.trabajo?.activo} onClick={hacerVideo}>
          {est.video.trabajo?.activo ? 'Trabajando…' : est.video.video ? 'Volver a hacerlo' : 'Hacer el video completo'}
        </button>
        {est.video.trabajo && (
          <div>
            <div className="barra-progreso"><i style={{ width: `${Math.round(est.video.trabajo.progreso * 100)}%` }} /></div>
            <div className="pequeno">{est.video.trabajo.error ? <span className="error">Error: {est.video.trabajo.error}</span>
              : est.video.trabajo.mensaje}</div>
          </div>
        )}
        {est.video.video && (
          <video src={`/api/explica/video/archivo?v=${version}`} controls style={{ width: '100%', borderRadius: 8, marginTop: 10 }} />
        )}
        {est.video.informe && (
          <ul className="pequeno">
            <li>Duración {Math.round(est.video.informe.duracion / 60 * 10) / 10} min · tiempo total{' '}
              {Math.round(est.video.informe.tiempo_total_s / 60)} min</li>
            <li>Costo real: guion {est.video.informe.costos.guion.cop} · voz {est.video.informe.costos.voz.cop} ·
              imágenes {est.video.informe.costos.imagenes.cop}</li>
            <li>Música: {est.video.informe.musica ? est.video.informe.musica.nombre_original : 'sin música'}</li>
            <li className="tenue">Guardado en: {est.video.informe.video}</li>
          </ul>
        )}
      </section>
      <section className="rev-tarjeta">
        <h2>Tema de prueba con voz</h2>
        <p>«Músculo de la muñeca», el tema 1 de «Partes de tu cuerpo que YA NO SIRVEN para nada»: voz de Peligro
          Tropical, tiempos de cada palabra con Whisper, animación y música tranquila. La voz cuesta unos{' '}
          <b>{est.tema_prueba.costo_voz.cop}</b>; si ya se grabó, no se vuelve a pagar.</p>
        <button className="boton" disabled={!!est.tema_prueba.trabajo?.activo} onClick={hacerTema}>
          {est.tema_prueba.trabajo?.activo ? 'Trabajando…' : est.tema_prueba.video ? 'Volver a hacerlo' : 'Hacer el tema de prueba'}
        </button>
        {est.tema_prueba.trabajo && (
          <div>
            <div className="barra-progreso"><i style={{ width: `${Math.round(est.tema_prueba.trabajo.progreso * 100)}%` }} /></div>
            <div className="pequeno">{est.tema_prueba.trabajo.error ? <span className="error">Error: {est.tema_prueba.trabajo.error}</span>
              : est.tema_prueba.trabajo.mensaje}</div>
          </div>
        )}
        {est.tema_prueba.video && (
          <video src={`/api/explica/tema-prueba/video?v=${version}`} controls style={{ width: '100%', borderRadius: 8, marginTop: 10 }} />
        )}
        {est.tema_prueba.informe && (() => {
          const inf = est.tema_prueba.informe;
          return (
            <ul className="pequeno">
              <li>Duración {Math.round(inf.duracion)} s · tiempo total {Math.round(inf.tiempo_total_s)} s (render
                {' '}{Math.round(inf.render.segundos_total)} s, {inf.render.procesos} a la vez)</li>
              <li>Costo real: guion {inf.costos.guion.cop} · voz {inf.costos.voz.cop} · imágenes {inf.costos.imagenes.cop}</li>
              <li>Música: {inf.musica ? inf.musica.nombre_original : 'sin música'}</li>
              {inf.avisos_guion.length > 0 && <li>Guion: {inf.avisos_guion.join(' · ')}</li>}
              {inf.avisos_ritmo.length > 0 && <li>Ritmo: {inf.avisos_ritmo.join(' · ')}</li>}
              <li className="tenue">Guardado en: {inf.video}</li>
            </ul>
          );
        })()}
      </section>
      {est.muestras && (
        <section className="rev-tarjeta">
          <h2>Resultado · costo real {est.muestras.costo_total}</h2>
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
            {est.muestras.archivos.map((a) => (
              <img key={a} src={`/api/explica/muestras/${a}?v=${version}`} alt={a}
                style={{ width: '100%', borderRadius: 8, border: '1px solid var(--borde, #ddd)' }} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
