import type { ReactNode } from 'react';
import { CircleAlert, RotateCcw } from 'lucide-react';
import { Icono } from './Icono';

// Estados de las pantallas: vacío (con su ilustración y qué hacer), cargando (esqueleto) y error en palabras normales.

export function Vacio({ icono = 'videos', titulo, texto, accion }: { icono?: string; titulo: string; texto?: string; accion?: ReactNode }) {
  return (
    <div className="vacio">
      <div className="vacio-ilus" aria-hidden="true"><i /><i><Icono nombre={icono} tam={26} /></i></div>
      <h3>{titulo}</h3>
      {texto && <p className="tenue">{texto}</p>}
      {accion}
    </div>
  );
}

export function Esqueleto({ filas = 3, tarjetas = 0 }: { filas?: number; tarjetas?: number }) {
  if (tarjetas) {
    return (
      <div className="rejilla-videos" aria-busy="true" aria-label="Cargando">
        {Array.from({ length: tarjetas }, (_, i) => (
          <div key={i} className="tarjeta-video"><div className="esq" style={{ aspectRatio: '16 / 9' }} />
            <div style={{ padding: 12 }}><div className="esq" style={{ height: 14, width: '70%' }} />
              <div className="esq" style={{ height: 11, width: '40%', marginTop: 8 }} /></div></div>
        ))}
      </div>
    );
  }
  return (
    <div aria-busy="true" aria-label="Cargando" style={{ display: 'grid', gap: 10 }}>
      {Array.from({ length: filas }, (_, i) => <div key={i} className="esq" style={{ height: 16, width: `${90 - i * 15}%` }} />)}
    </div>
  );
}

export function Girando({ texto }: { texto?: string }) {
  return <span className="girando" role="status"><span className="giro" />{texto}</span>;
}

export function ErrorAmable({ titulo = 'No se pudo completar', texto, reintentar }: { titulo?: string; texto: string; reintentar?: () => void }) {
  return (
    <div className="aviso-error" role="alert">
      <CircleAlert size={20} aria-hidden="true" />
      <div>
        <b>{titulo}</b>
        <div className="tenue pequeno">{texto}</div>
        {reintentar && <button className="boton-borde pequeno" style={{ marginTop: 10 }} onClick={reintentar}>
          <RotateCcw size={14} /> Intentar otra vez</button>}
      </div>
    </div>
  );
}
