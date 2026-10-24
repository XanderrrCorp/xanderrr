import { useEffect, useState } from 'react';
import { type VideoLista } from '../api';
import { TarjetaVideo, videosAlDia } from './Inicio';

export function MisVideos() {
  const [videos, setVideos] = useState<VideoLista[] | null>(null);
  const [error, setError] = useState('');
  useEffect(() => videosAlDia((l) => { setVideos(l); setError(''); }, (e) => { setError(e.message); setVideos((v) => v ?? []); }), []);
  return (
    <div className="pagina">
      <div className="seccion-cab"><h1>Mis videos</h1></div>
      <p className="tenue">Los shorts y las miniaturas se sacan desde cada video.</p>
      {error && <p className="error">No se pudieron leer tus videos: {error}</p>}
      {videos === null ? <p className="tenue">Cargando…</p> : videos.length === 0 ? (!error && <p className="tenue">Todavía no hay videos.</p>) : (
        <div className="rejilla-videos">{videos.map((v) => <TarjetaVideo key={v.slug} v={v} />)}</div>
      )}
    </div>
  );
}
