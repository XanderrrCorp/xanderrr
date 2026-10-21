import { Link, useLocation } from 'react-router-dom';
import { Zap } from 'lucide-react';
import { miles, type Cuenta } from '../api';

const TITULOS: [RegExp, string][] = [
  [/^\/$/, 'Home'], [/^\/producir/, 'Producer'], [/^\/videos\/[^/]+\/editor/, 'Editor'], [/^\/videos\/[^/]+\/miniatura/, 'Miniatura'],
  [/^\/videos/, 'Proyectos'], [/^\/personajes/, 'Personajes'], [/^\/estilos/, 'Estilos'], [/^\/miniaturas/, 'Miniaturas'],
  [/^\/media/, 'Media'], [/^\/canales/, 'Canales'], [/^\/formatos/, 'Inspire'], [/^\/planes/, 'Planes y créditos'],
  [/^\/cola/, 'Cola de la semana'], [/^\/tracy/, 'Canal Tracy'], [/^\/explica/, 'El Calvo Explica'], [/^\/calma/, 'Hazlo con Calma'],
  [/^\/espacio/, 'Liberar espacio'],
];

// Barra de arriba: dónde estás y los créditos siempre a la vista, con el botón para recargar.
export function Barra({ cuenta }: { cuenta: Cuenta | null }) {
  const { pathname } = useLocation();
  const titulo = TITULOS.find(([r]) => r.test(pathname))?.[1] ?? '';
  const s = cuenta?.saldo;
  return (
    <header className="barra">
      <Link to="/" className="marca solo-movil"><i>X</i></Link>
      <span className="barra-titulo">{titulo}</span>
      <span className="crece" />
      {cuenta?.usuario.a_costo && (
        <span className="etiqueta" title="Tu cuenta paga el costo real de los proveedores, sin margen">
          A costo · ${cuenta.gasto_mes_usd.toFixed(2)} este mes</span>
      )}
      <div className={`saldo ${s?.bajo && !cuenta?.usuario.a_costo ? 'bajo' : ''}`}
        title={s ? `${miles(s.creditos)} créditos · alcanzan para unos ${s.minutos} minutos de video` : 'Cargando tu saldo'}>
        <Zap size={16} aria-hidden="true" />
        <b>{s ? miles(s.creditos) : '…'}</b><small>créditos</small>
        <Link to="/planes" className="boton-primario">Recargar</Link>
      </div>
    </header>
  );
}
