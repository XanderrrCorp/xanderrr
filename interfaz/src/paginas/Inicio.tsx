import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, archivo, type Canal, type Formato, type VideoLista } from '../api';
import { CajaIdea } from '../componentes/CajaIdea';
import { ErrorAmable, Esqueleto, Vacio } from '../componentes/Estados';
import { Icono } from '../componentes/Icono';

// Portadas de las plantillas: color propio por formato (sin imágenes que pagar).
const TINTES = ['t1', 't2', 't3', 't4', 't5'];

export function Inicio() {
  const ir = useNavigate();
  const [videos, setVideos] = useState<VideoLista[] | null>(null);
  const [formatos, setFormatos] = useState<Formato[]>([]);
  const [canales, setCanales] = useState<Canal[] | null>(null);
  const [formato, setFormato] = useState<string | undefined>();
  const [errorCanales, setErrorCanales] = useState('');

  useEffect(() => {
    api<VideoLista[]>('/api/v2/videos').then(setVideos).catch(() => setVideos([]));
    api<Formato[]>('/api/v2/recursos/formatos').then(setFormatos).catch(() => {});
    // si no se pueden leer los canales NO se ofrece «crear tu canal»: se dice qué pasó
    api<Canal[]>('/api/v2/canales').then(setCanales).catch((e) => setErrorCanales(e.message));
  }, []);

  return (
    <div className="pagina">
      <div className="hola">
        <h1>¿Qué quieres crear hoy?</h1>
        <p className="tenue">Escribe una idea y Xandart hace el guion, las imágenes, la voz y el video. Tú apruebas cada paso.</p>
      </div>
      {errorCanales && <ErrorAmable titulo="No pudimos leer tus canales" texto={`${errorCanales} Si Xandart se está actualizando, espera a que termine la copia de seguridad.`} />}
      {canales !== null && canales.length === 0 && (
        <div className="aviso-canal">
          <Icono nombre="canal" />
          <div><b>Primero, tu canal</b><span className="tenue pequeno">En 4 pasos: nombre, voz, estilo y personaje. Así cada video sale con tu identidad.</span></div>
          <Link to="/canales/nuevo" className="boton-primario">Crear mi canal</Link>
        </div>
      )}
      <CajaIdea formatoInicial={formato} creado={(slug) => ir(`/producir/${slug}`)} />

      {formatos.length > 0 && (
        <>
          <div className="seccion-cab"><h2>Empieza rápido</h2><Link to="/formatos" className="tenue">Ver todas <Icono nombre="flecha" tam={14} /></Link></div>
          <div className="plantillas">
            {formatos.map((f, i) => (
              <button key={f.id} className={`plantilla ${formato === f.id ? 'sel' : ''}`}
                onClick={() => { setFormato(f.id); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
                <span className={`plantilla-img ${TINTES[i % TINTES.length]}`}><span>{f.datos.relacion_aspecto === '9:16' ? 'Short' : `${f.datos.duracion_min ?? 9} min`}</span></span>
                <span className="plantilla-txt"><b>{f.nombre}</b><span className="tenue pequeno">{f.descripcion || f.datos.idea_ejemplo || ' '}</span></span>
              </button>
            ))}
          </div>
        </>
      )}

      <div className="seccion-cab"><h2>Tus proyectos</h2>{videos && videos.length > 0 && <Link to="/videos" className="tenue">Ver todos <Icono nombre="flecha" tam={14} /></Link>}</div>
      {videos === null ? <Esqueleto tarjetas={4} /> : videos.length === 0 ? (
        <Vacio titulo="Todavía no tienes videos" texto="Escribe una idea arriba y en unos minutos tienes el primero." />
      ) : (
        <div className="rejilla-videos">
          {videos.slice(0, 8).map((v) => <TarjetaVideo key={v.slug} v={v} />)}
        </div>
      )}
    </div>
  );
}

const ESTADOS: Record<string, string> = {
  en_marcha: 'En marcha', listo: 'Listo', imagenes_listas: 'Imágenes listas', guion_listo: 'Guion listo', borrador: 'Borrador',
};

export function TarjetaVideo({ v, elegir, activo }: { v: VideoLista; elegir?: () => void; activo?: boolean }) {
  const ir = useNavigate();
  // en marcha: el storyboard en vivo; terminado: el editor; a medio hacer: la revisión
  const abrir = () => ir(v.estado === 'en_marcha' ? `/producir/${v.slug}` : v.video ? `/videos/${v.slug}/editor` : `/videos/${v.slug}`);
  return (
    <article className={`tarjeta-video ${activo ? 'activo' : ''}`}>
      <button className="tv-portada" onClick={elegir ?? abrir} aria-label={`Abrir ${v.titulo}`}>
        {v.portada ? <img src={archivo(v.slug, v.portada)} alt="" loading="lazy" /> : <Icono nombre="media" tam={30} />}
        <span className={`estado ${v.estado}`}>{ESTADOS[v.estado] ?? v.estado}</span>
      </button>
      <div className="tv-texto">
        <b title={v.titulo}>{v.titulo}</b>
        <span className="tenue pequeno">{v.minutos} min · {v.video
          ? <Link to={`/videos/${v.slug}/editor`}>editar</Link> : <Link to={`/videos/${v.slug}`}>abrir</Link>}</span>
      </div>
    </article>
  );
}
