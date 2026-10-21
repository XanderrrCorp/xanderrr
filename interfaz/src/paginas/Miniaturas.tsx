import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, archivo, type VideoLista } from '../api';
import { Costo } from '../componentes/Costo';
import { Esqueleto, Vacio } from '../componentes/Estados';
import { Icono } from '../componentes/Icono';

// Cada miniatura nace de un video: aquí eliges de cuál (se hace con su guion y sus personajes).
export function Miniaturas() {
  const [videos, setVideos] = useState<VideoLista[] | null>(null);
  useEffect(() => { api<VideoLista[]>('/api/v2/videos').then(setVideos).catch(() => setVideos([])); }, []);
  const conGuion = (videos ?? []).filter((v) => v.pasos.guionista === 'completo');
  return (
    <div className="pagina">
      <div className="seccion-cab" style={{ marginTop: 0 }}><h1>Miniaturas</h1><Costo accion="miniatura" /></div>
      <p className="tenue">Elige el video. La miniatura se arma con su guion: textos, personajes y fondo.</p>
      {videos === null ? <Esqueleto tarjetas={4} /> : conGuion.length === 0 ? (
        <Vacio icono="miniatura" titulo="Primero un video con guion" texto="Las miniaturas salen del guion del video."
          accion={<Link to="/producir" className="boton-primario"><Icono nombre="chispa" tam={16} />Crear un video</Link>} />
      ) : (
        <div className="rejilla-videos">
          {conGuion.map((v) => (
            <article key={v.slug} className="tarjeta-video">
              <Link to={`/videos/${v.slug}/miniatura`} className="tv-portada">
                {v.portada ? <img src={archivo(v.slug, v.portada)} alt="" loading="lazy" /> : <Icono nombre="miniatura" tam={30} />}
              </Link>
              <div className="tv-texto"><b title={v.titulo}>{v.titulo}</b>
                <Link to={`/videos/${v.slug}/miniatura`} className="pequeno">Hacer o ver su miniatura</Link></div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
