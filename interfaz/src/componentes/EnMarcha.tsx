import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Check } from 'lucide-react';
import { api, archivo, type VideoDetalle } from '../api';
import { Icono } from './Icono';
import { Esqueleto, ErrorAmable, Vacio } from './Estados';

const PASOS: { clave: string[]; nombre: string; icono: string; peso: number }[] = [
  { clave: ['guionista'], nombre: 'Guion', icono: 'ideas', peso: 0.1 },
  { clave: ['assets'], nombre: 'Imágenes', icono: 'imagen', peso: 0.45 },
  { clave: ['voz', 'director_edicion'], nombre: 'Voz y edición', icono: 'sonidos', peso: 0.15 },
  { clave: ['export_final'], nombre: 'Video', icono: 'media', peso: 0.3 },
];
const PASO_TRABAJO: Record<string, number> = { guion: 0, imagenes: 1, prueba: 1, ajustar: 1, regenerar: 1, video: 2, short: 2 };

export function minutosTexto(s: number): string {
  if (s < 60) return 'menos de 1 minuto';
  const m = Math.round(s / 60);
  return m < 60 ? `unos ${m} min` : `unas ${Math.floor(m / 60)} h ${m % 60} min`;
}

/** Progreso total del video (0-1) y segundos que faltan, con el ritmo del paso que va (es una estimación). */
export function progresoTotal(v: VideoDetalle): { total: number; faltan: number | null } {
  const t = v.trabajo;
  const actual = t?.activo ? PASO_TRABAJO[t.paso] ?? -1 : -1;
  let total = 0;
  PASOS.forEach((p, i) => {
    if (i === actual) total += p.peso * (t?.progreso ?? 0);
    else if (p.clave.every((k) => v.pasos[k] === 'completo')) total += p.peso;
  });
  let faltan: number | null = null;
  if (t?.activo && actual >= 0 && t.progreso > 0.03 && t.segundos > 15) {
    const porUnidad = t.segundos / (PASOS[actual].peso * t.progreso);     // segundos por «unidad» de video
    faltan = Math.max(0, (1 - total) * porUnidad);
  }
  return { total: Math.min(1, total), faltan };
}

// El video en marcha con su storyboard en vivo: cada escena aparece con ✓ cuando su imagen queda lista.
export function EnMarcha({ slug, grande = false }: { slug: string | null; grande?: boolean }) {
  const [v, setV] = useState<VideoDetalle | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    setV(null); setError('');
    if (!slug) return;
    let vivo = true;
    let espera: number | undefined;
    const traer = async () => {
      try {
        const d = await api<VideoDetalle>(`/api/videos/${slug}`);
        if (!vivo) return;
        setV(d); setError('');
        espera = window.setTimeout(traer, d.trabajo?.activo ? 2500 : 15000);
      } catch (e) { if (vivo) setError((e as Error).message); espera = window.setTimeout(traer, 15000); }
    };
    traer();
    return () => { vivo = false; window.clearTimeout(espera); };
  }, [slug]);

  if (!slug) {
    return (
      <aside className="en-marcha">
        <Vacio icono="media" titulo="Aquí verás tu video en marcha"
          texto="Primero el guion; después cada escena del storyboard, marcada con ✓ a medida que su imagen queda lista." />
      </aside>
    );
  }
  if (!v) {
    return <aside className="en-marcha">{error ? <ErrorAmable texto={error} /> : <Esqueleto filas={4} />}</aside>;
  }

  const t = v.trabajo;
  const actual = t?.activo ? PASO_TRABAJO[t.paso] ?? -1 : -1;
  const hechas = v.escenas.filter((e) => e.imagen).length;
  const { total, faltan } = progresoTotal(v);
  const estado = (i: number) => {
    if (i === actual) return 'va';
    return PASOS[i].clave.every((k) => v.pasos[k] === 'completo') ? 'ok' : 'espera';
  };

  return (
    <aside className={`en-marcha ${grande ? 'grande' : ''}`}>
      <div className="em-cab">
        <div>
          <span className="tenue pequeno">{t?.activo ? 'En marcha' : v.video ? 'Terminado' : 'Tu último video'} · {v.minutos} min</span>
          {grande ? <h1 title={v.titulo}>{v.titulo}</h1> : <h3 title={v.titulo}>{v.titulo}</h3>}
        </div>
        <Link className="boton-borde pequeno" to={`/videos/${v.slug}`}>Revisar y aprobar <Icono nombre="flecha" tam={16} /></Link>
      </div>
      <ol className="pasos">
        {PASOS.map((p, i) => (
          <li key={p.nombre} className={estado(i)}>
            <i>{estado(i) === 'ok' ? <Check size={13} strokeWidth={3} /> : i + 1}</i>
            {p.nombre}{i === 1 && v.escenas.length > 0 ? ` ${hechas} de ${v.escenas.length}` : ''}
          </li>
        ))}
      </ol>
      <div className="progreso">
        <div className="progreso-cifras">
          <b>{Math.round(total * 100)}%</b>
          <span className="tenue pequeno">
            {t?.activo ? (faltan !== null ? `Faltan ${minutosTexto(faltan)} (estimado)` : 'Calculando cuánto falta…')
              : v.video ? 'Listo' : 'En pausa: sigue desde «Revisar y aprobar»'}
          </span>
        </div>
        <div className="barra-progreso"><i style={{ width: `${Math.round(total * 100)}%` }} /></div>
        {t?.activo && <span className="tenue pequeno">{t.mensaje}</span>}
      </div>
      {t?.error && !t.activo && <ErrorAmable titulo="El último paso no terminó" texto={t.error} />}
      {v.escenas.length > 0 ? (
        <>
          <div className="em-sub"><b>Storyboard</b><span className="tenue pequeno">{hechas} de {v.escenas.length} escenas listas</span></div>
          <div className={`storyboard ${grande ? 'grande' : ''}`}>
            {v.escenas.map((e) => {
              const clase = e.imagen ? 'lista' : actual === 1 ? 'cargando' : '';
              return (
                <figure key={e.id} className={clase} title={e.narracion}>
                  {e.imagen ? <img src={archivo(v.slug, e.imagen)} alt="" loading="lazy" /> : <span className="sb-vacia" />}
                  <span className="sb-num">{e.id}</span>
                  {e.imagen && <span className="sb-ok" aria-label="lista"><Check size={12} strokeWidth={3} /></span>}
                  {!e.imagen && actual === 1 && <span className="giro sb-giro" aria-hidden="true" />}
                  {grande && <figcaption>{e.narracion}</figcaption>}
                </figure>
              );
            })}
          </div>
        </>
      ) : (
        <p className="tenue pequeno">El storyboard aparece cuando el guion esté listo.</p>
      )}
      {v.video && (
        <div className="em-acciones">
          <Link className="boton-primario" to={`/videos/${v.slug}/editor`}>Abrir en el editor</Link>
          <a className="boton-borde" href={archivo(v.slug, v.video) + '?descargar=true'}>Descargar</a>
        </div>
      )}
    </aside>
  );
}
