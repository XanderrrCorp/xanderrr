import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, archivo, paginaVieja, type VideoLista } from '../api';
import { CajaIdea } from '../componentes/CajaIdea';
import { EnMarcha } from '../componentes/EnMarcha';
import { Icono } from '../componentes/Icono';

export function Inicio() {
  const [videos, setVideos] = useState<VideoLista[]>([]);
  const [slug, setSlug] = useState<string | null>(null);

  const cargar = () => api<VideoLista[]>('/api/v2/videos').then((l) => {
    setVideos(l);
    setSlug((s) => s ?? (l.find((v) => v.estado !== 'listo') ?? l[0])?.slug ?? null);
  }).catch(() => {});
  useEffect(() => { cargar(); }, []);

  return (
    <div className="pagina">
      <h1 className="titular">¿Qué video quieres <span className="acento">crear</span> hoy?</h1>
      <p className="bajada">Escribe la idea. Xandart hace el guion, las imágenes, la voz y la edición; tú apruebas cada paso.</p>
      <div className="hero">
        <CajaIdea creado={(s) => { setSlug(s); cargar(); }} />
        <EnMarcha slug={slug} />
      </div>
      {videos.length > 0 && (
        <>
          <div className="seccion-cab"><h2>Tus videos recientes</h2><Link to="/videos" className="tenue">Ver todos <Icono nombre="flecha" tam={14} /></Link></div>
          <div className="rejilla-videos">
            {videos.slice(0, 4).map((v) => <TarjetaVideo key={v.slug} v={v} elegir={() => setSlug(v.slug)} activo={v.slug === slug} />)}
          </div>
        </>
      )}
    </div>
  );
}

const ESTADOS: Record<string, string> = {
  en_marcha: 'En marcha', listo: 'Listo', imagenes_listas: 'Imágenes listas', guion_listo: 'Guion listo', borrador: 'Borrador',
};

export function TarjetaVideo({ v, elegir, activo }: { v: VideoLista; elegir?: () => void; activo?: boolean }) {
  return (
    <article className={`tarjeta-video ${activo ? 'activo' : ''}`}>
      <button className="tv-portada" onClick={elegir ?? (() => (window.location.href = paginaVieja(v.slug)))}>
        {v.portada ? <img src={archivo(v.slug, v.portada)} alt="" loading="lazy" /> : <Icono nombre="videos" tam={32} />}
        <span className={`estado ${v.estado}`}>{ESTADOS[v.estado] ?? v.estado}</span>
      </button>
      <div className="tv-texto">
        <b title={v.titulo}>{v.titulo}</b>
        <span className="tenue pequeno">{v.minutos} min · <a href={paginaVieja(v.slug)}>abrir</a></span>
      </div>
    </article>
  );
}
