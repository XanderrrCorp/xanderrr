import { useEffect, useState } from 'react';
import { api, type VideoLista } from '../api';
import { TarjetaVideo } from './Inicio';

export function MisVideos() {
  const [videos, setVideos] = useState<VideoLista[] | null>(null);
  useEffect(() => { api<VideoLista[]>('/api/v2/videos').then(setVideos).catch(() => setVideos([])); }, []);
  return (
    <div className="pagina">
      <div className="seccion-cab"><h1>Mis videos</h1></div>
      <p className="tenue">Los shorts y las miniaturas se sacan desde cada video.</p>
      {videos === null ? <p className="tenue">Cargando…</p> : videos.length === 0 ? <p className="tenue">Todavía no hay videos.</p> : (
        <div className="rejilla-videos">{videos.map((v) => <TarjetaVideo key={v.slug} v={v} />)}</div>
      )}
    </div>
  );
}
