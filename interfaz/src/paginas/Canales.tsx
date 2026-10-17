import { useEffect, useState } from 'react';
import { api, type Canal } from '../api';
import { Icono } from '../componentes/Icono';

export function Canales() {
  const [canales, setCanales] = useState<Canal[] | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { api<Canal[]>('/api/v2/canales').then(setCanales).catch(() => setCanales([])); }, []);
  // llamados a comentar en el guion: si el canal no lo eligió, viene prendido solo en el estilo de Peligro Tropical
  const llamados = (c: Canal) => (typeof c.ajustes?.llamados_comentar === 'boolean'
    ? c.ajustes.llamados_comentar as boolean : c.estilo?.clave === 'enciclopedia_mascota');
  const cambiar = async (c: Canal, valor: boolean) => {
    setError('');
    try {
      const r = await api<{ ajustes: Record<string, unknown> }>(`/api/v2/canales/${c.id}/ajustes`,
        { cuerpo: { clave: 'llamados_comentar', valor }, metodo: 'PUT' });
      setCanales((cs) => (cs ?? []).map((x) => (x.id === c.id ? { ...x, ajustes: r.ajustes } : x)));
    } catch (e) { setError((e as Error).message); }
  };
  return (
    <div className="pagina">
      <div className="seccion-cab"><h1>Canales</h1></div>
      <p className="tenue">Cada canal guarda su formato, estilo, personaje, voz y plantilla de miniatura.</p>
      {error && <p className="error">{error}</p>}
      <div className="rejilla-canales">
        {(canales ?? []).map((c) => (
          <article key={c.id} className="tarjeta-canal">
            <span className="ic-canal">{c.nombre.slice(0, 1)}</span>
            <div><b>{c.nombre}</b><span className="tenue pequeno">{c.formato?.nombre ?? 'Sin formato'} · {c.videos} videos</span>
              <label className="pequeno" style={{ display: 'block', marginTop: 6 }} title="5 llamados a comentar dentro del guion y un comentario fijado">
                <input type="checkbox" checked={llamados(c)} onChange={(e) => cambiar(c, e.target.checked)} /> Llamados a comentar
              </label></div>
          </article>
        ))}
        <article className="tarjeta-canal nuevo" title="Llega con el asistente de canal">
          <Icono nombre="canal" /> Nuevo canal <em>pronto</em>
        </article>
      </div>
    </div>
  );
}
