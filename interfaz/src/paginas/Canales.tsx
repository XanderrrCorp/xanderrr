import { useEffect, useState } from 'react';
import { api, type Canal } from '../api';
import { Icono } from '../componentes/Icono';

export function Canales() {
  const [canales, setCanales] = useState<Canal[] | null>(null);
  useEffect(() => { api<Canal[]>('/api/v2/canales').then(setCanales).catch(() => setCanales([])); }, []);
  return (
    <div className="pagina">
      <div className="seccion-cab"><h1>Canales</h1></div>
      <p className="tenue">Cada canal guarda su formato, estilo, personaje, voz y plantilla de miniatura.</p>
      <div className="rejilla-canales">
        {(canales ?? []).map((c) => (
          <article key={c.id} className="tarjeta-canal">
            <span className="ic-canal">{c.nombre.slice(0, 1)}</span>
            <div><b>{c.nombre}</b><span className="tenue pequeno">{c.formato?.nombre ?? 'Sin formato'} · {c.videos} videos</span></div>
          </article>
        ))}
        <article className="tarjeta-canal nuevo" title="Llega con el asistente de canal">
          <Icono nombre="canal" /> Nuevo canal <em>pronto</em>
        </article>
      </div>
    </div>
  );
}
