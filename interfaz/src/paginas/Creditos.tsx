import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, miles, type MovimientoCredito } from '../api';
import { Esqueleto, ErrorAmable, Vacio } from '../componentes/Estados';

const TIPOS: Record<string, string> = {
  consumo: 'Usado', reserva: 'Apartado', liberacion: 'Devuelto (sobró)', devolucion: 'Devuelto', recarga: 'Recarga',
  bono: 'Regalo', ajuste: 'Ajuste', vencimiento: 'Vencido',
};

// En qué se gastó cada crédito, del más reciente al más viejo.
export function Creditos() {
  const [filas, setFilas] = useState<MovimientoCredito[] | null>(null);
  const [error, setError] = useState('');
  const cargar = () => api<MovimientoCredito[]>('/api/v2/creditos/historial').then(setFilas).catch((e) => { setError(e.message); setFilas([]); });
  useEffect(() => { cargar(); }, []);
  const verCosto = (filas ?? []).some((f) => f.costo_real_usd !== undefined);
  return (
    <div className="pagina">
      <div className="seccion-cab" style={{ marginTop: 0 }}><h1>Historial de créditos</h1>
        <Link to="/planes" className="boton-primario">Recargar</Link></div>
      <p className="tenue">En qué se usó cada crédito. Si algo falla, lo apartado vuelve solo y lo ves aquí como «Devuelto».</p>
      {error && <ErrorAmable texto={error} reintentar={cargar} />}
      {filas === null ? <Esqueleto filas={6} /> : filas.length === 0 ? (
        <Vacio icono="planes" titulo="Todavía no hay movimientos" texto="Cuando crees tu primer video, aquí verás en qué se usaron los créditos." />
      ) : (
        <div className="tabla-envoltura">
          <table className="tabla">
            <thead><tr><th>Fecha</th><th>Qué</th><th>Video</th><th className="num">Créditos</th>{verCosto && <th className="num">Costo real</th>}</tr></thead>
            <tbody>
              {filas.map((f, i) => (
                <tr key={i}>
                  <td className="tenue">{new Date(f.fecha).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })}</td>
                  <td><b>{TIPOS[f.tipo] ?? f.tipo}</b>{(f.que || f.nota) && <span className="tenue pequeno"> · {f.que || f.nota}</span>}</td>
                  <td className="tenue">{f.video ?? '—'}</td>
                  <td className={`num ${f.creditos >= 0 ? 'mas' : 'menos'}`}>{f.creditos >= 0 ? '+' : '−'}{miles(Math.abs(f.creditos))}</td>
                  {verCosto && <td className="num tenue">{f.costo_real_usd ? `$${f.costo_real_usd.toFixed(3)}` : ''}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
