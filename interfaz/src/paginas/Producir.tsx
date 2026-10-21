import { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, type VideoLista } from '../api';
import { CajaIdea } from '../componentes/CajaIdea';
import { EnMarcha } from '../componentes/EnMarcha';

// Producer: la idea entra arriba y abajo se ve la producción en vivo (pasos, % total, tiempo que falta y storyboard).
export function Producir({ personalizado = false }: { personalizado?: boolean }) {
  const { slug } = useParams();
  const [buscar] = useSearchParams();
  const ir = useNavigate();
  const [activo, setActivo] = useState<string | null>(null);

  useEffect(() => {
    if (slug) return;
    api<VideoLista[]>('/api/v2/videos').then((l) => setActivo(l.find((v) => v.estado === 'en_marcha')?.slug ?? null)).catch(() => {});
  }, [slug]);

  if (slug) return <div className="pagina"><EnMarcha slug={slug} grande /></div>;
  return (
    <div className="pagina">
      <div className="hola">
        <h1>{personalizado ? 'Video paso a paso' : 'Producer'}</h1>
        <p className="tenue">{personalizado
          ? 'Escribes la idea, revisas el guion y apruebas antes de que se hagan las imágenes.'
          : 'Escribe la idea y Xandart lo hace todo; aquí ves cada escena a medida que queda lista.'}</p>
      </div>
      <CajaIdea personalizado={personalizado} formatoInicial={buscar.get('formato') ?? undefined}
        creado={(s) => ir(`/producir/${s}`)} />
      <div style={{ marginTop: 22 }}><EnMarcha slug={activo} grande /></div>
    </div>
  );
}
