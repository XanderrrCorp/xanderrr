import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';

// El Calvo Explica (nombre provisional): «TODAS las X explicadas en N minutos». Por ahora: las 3 ilustraciones de
// muestra para aprobar el estilo (Google, con el personaje como referencia). Lo demás llega en los pasos siguientes.

interface EstadoExplica {
  canal: { clave: string; nombre: string };
  costo_muestras: { usd?: number; cop?: string; proveedor?: string; modelo?: string; error?: string };
  muestras: { archivos: string[]; costo_total: string; proveedor: string; modelo: string } | null;
  trabajo: { paso: string; progreso: number; mensaje: string; activo: boolean; error: string | null } | null;
}

export function Explica() {
  const [est, setEst] = useState<EstadoExplica | null>(null);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const cargar = useCallback(async () => {
    try { const e = await api<EstadoExplica>('/api/explica'); setEst(e); setVersion(Date.now()); }
    catch (e) { setError((e as Error).message); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => {
    if (!est?.trabajo?.activo) return;
    const id = setInterval(cargar, 2000);
    return () => clearInterval(id);
  }, [est?.trabajo?.activo, cargar]);

  const generar = async () => {
    setError('');
    try { setEst(await api<EstadoExplica>('/api/explica/muestras', { cuerpo: { permiso: false } })); }
    catch (e) { setError((e as Error).message); }
  };

  if (!est) return <div className="pagina"><h1>El Calvo Explica</h1>{error && <p className="error">{error}</p>}</div>;
  const t = est.trabajo;
  const c = est.costo_muestras;
  return (
    <div className="pagina tracy">
      <h1>{est.canal.nombre}</h1>
      <p className="tenue">TODAS las X explicadas en N minutos. Fondo blanco, tu personaje y animación por código.</p>
      <section className="rev-tarjeta">
        <h2>Ilustraciones de muestra</h2>
        <p>Tres tipos de papá (sofá, «pregúntale a tu mamá», parrillero) para ver si el personaje se mantiene. Se generan con Google
          ({c.modelo || '—'}) y la imagen del personaje como referencia.</p>
        {c.error ? <p className="error pequeno">{c.error}</p>
          : <p>Costo de las 3: <b>unos {c.cop}</b>.</p>}
        <button className="boton" disabled={!!t?.activo} onClick={generar}>
          {t?.activo ? 'Generando…' : est.muestras ? `Volver a generar (unos ${c.cop})` : `Generar las 3 muestras (unos ${c.cop})`}
        </button>
        {t && (
          <div>
            <div className="barra-progreso"><i style={{ width: `${Math.round(t.progreso * 100)}%` }} /></div>
            <div className="pequeno">{t.error ? <span className="error">Error: {t.error}</span> : t.mensaje}</div>
          </div>
        )}
        {error && <p className="error">{error}</p>}
      </section>
      {est.muestras && (
        <section className="rev-tarjeta">
          <h2>Resultado · costo real {est.muestras.costo_total}</h2>
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
            {est.muestras.archivos.map((a) => (
              <img key={a} src={`/api/explica/muestras/${a}?v=${version}`} alt={a}
                style={{ width: '100%', borderRadius: 8, border: '1px solid var(--borde, #ddd)' }} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
