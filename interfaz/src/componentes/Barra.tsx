import { Link } from 'react-router-dom';
import { Icono } from './Icono';
import { miles, type Cuenta } from '../api';

// Barra de arriba: marca a la izquierda y los créditos siempre visibles a la derecha.
export function Barra({ cuenta, menu }: { cuenta: Cuenta | null; menu: () => void }) {
  const s = cuenta?.saldo;
  return (
    <header className="barra">
      <button className="solo-movil boton-icono" onClick={menu} aria-label="Abrir menú"><Icono nombre="menu" /></button>
      <Link to="/" className="marca"><img src="/app/xandart.svg" alt="" width={30} height={30} /><span>xandart</span></Link>
      {cuenta?.usuario.a_costo && <span className="etiqueta">Dueño · a costo</span>}
      <span className="crece" />
      <Link to="/planes" className="boton-borde">Obtener créditos</Link>
      {cuenta?.usuario.a_costo ? (
        <a href="/admin" className="saldo" title="Tu cuenta paga el costo real de los proveedores">
          <i className="moneda" /><b>${cuenta.gasto_mes_usd.toFixed(2)}</b><small>real este mes</small>
        </a>
      ) : (
        <Link to="/planes" className={`saldo ${s?.bajo ? 'bajo' : ''}`}
          title={s ? `${miles(s.creditos)} créditos · alcanzan para unos ${s.minutos} minutos de video` : ''}>
          <i className="moneda" />
          <b>{s ? miles(s.creditos) : '…'}</b>
          {s && <small>≈ {s.minutos} min</small>}
        </Link>
      )}
      <span className="avatar" title={cuenta?.usuario.email}>{(cuenta?.usuario.nombre || 'X').slice(0, 1).toUpperCase()}</span>
    </header>
  );
}
