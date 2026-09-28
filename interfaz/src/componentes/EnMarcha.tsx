import { useEffect, useState } from 'react';
import { api, archivo, paginaVieja, type VideoDetalle } from '../api';
import { Icono } from './Icono';

const PASOS: { clave: string[]; nombre: string }[] = [
  { clave: ['guionista'], nombre: 'Guion' },
  { clave: ['assets'], nombre: 'Imágenes' },
  { clave: ['voz', 'director_edicion'], nombre: 'Voz y edición' },
  { clave: ['export_final'], nombre: 'Video' },
];
const PASO_TRABAJO: Record<string, number> = { guion: 0, imagenes: 1, prueba: 1, ajustar: 1, regenerar: 1, video: 2, short: 2 };

// El video en marcha con su storyboard: cada escena aparece a medida que su imagen queda lista.
export function EnMarcha({ slug }: { slug: string | null }) {
  const [v, setV] = useState<VideoDetalle | null>(null);

  useEffect(() => {
    if (!slug) { setV(null); return; }
    let vivo = true;
    let espera: number | undefined;
    const traer = async () => {
      try {
        const d = await api<VideoDetalle>(`/api/videos/${slug}`);
        if (!vivo) return;
        setV(d);
        espera = window.setTimeout(traer, d.trabajo?.activo ? 2500 : 15000);
      } catch { espera = window.setTimeout(traer, 15000); }
    };
    traer();
    return () => { vivo = false; window.clearTimeout(espera); };
  }, [slug]);

  if (!slug || !v) {
    return (
      <aside className="en-marcha vacio">
        <Icono nombre="videos" tam={36} />
        <b>Aquí verás tu video en marcha</b>
        <span className="tenue">El guion, luego cada escena del storyboard a medida que su imagen queda lista.</span>
      </aside>
    );
  }

  const t = v.trabajo;
  const actual = t?.activo ? PASO_TRABAJO[t.paso] ?? -1 : -1;
  const hechas = v.escenas.filter((e) => e.imagen).length;
  const estado = (i: number) => {
    if (i === actual) return 'va';
    return PASOS[i].clave.every((k) => v.pasos[k] === 'completo') ? 'ok' : 'espera';
  };

  return (
    <aside className="en-marcha">
      <div className="em-cab">
        <div>
          <span className="tenue pequeno">{t?.activo ? 'En marcha' : 'Tu último video'}</span>
          <h3 title={v.titulo}>{v.titulo}</h3>
        </div>
        <a className="boton-borde pequeno" href={paginaVieja(v.slug)}>Revisar y aprobar <Icono nombre="flecha" tam={16} /></a>
      </div>
      <ol className="pasos">
        {PASOS.map((p, i) => (
          <li key={p.nombre} className={estado(i)}>
            <i>{estado(i) === 'ok' ? <Icono nombre="ok" tam={14} /> : i + 1}</i>{p.nombre}
          </li>
        ))}
      </ol>
      {t?.activo && (
        <div className="progreso">
          <div className="barra-progreso"><i style={{ width: `${Math.round(t.progreso * 100)}%` }} /></div>
          <span className="tenue pequeno">{t.mensaje}</span>
        </div>
      )}
      {t?.error && !t.activo && <p className="error pequeno">{t.error}</p>}
      {v.escenas.length > 0 ? (
        <>
          <div className="em-sub"><b>Storyboard</b><span className="tenue pequeno">{hechas} de {v.escenas.length} escenas con imagen</span></div>
          <div className="storyboard">
            {v.escenas.map((e) => (
              <figure key={e.id} className={e.imagen ? 'lista' : actual === 1 ? 'cargando' : ''} title={e.narracion}>
                {e.imagen ? <img src={archivo(v.slug, e.imagen)} alt="" loading="lazy" /> : <span>{e.id}</span>}
              </figure>
            ))}
          </div>
        </>
      ) : (
        <p className="tenue pequeno">El storyboard aparece cuando el guion esté listo.</p>
      )}
      {v.video && <a className="boton-primario ancho" href={archivo(v.slug, v.video) + '?descargar=true'}>Descargar el video</a>}
    </aside>
  );
}
