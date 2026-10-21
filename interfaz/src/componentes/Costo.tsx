import { useEffect, useState } from 'react';
import { Zap } from 'lucide-react';
import { api, miles, type Cotizacion } from '../api';

// Lo que cuesta una acción, junto a su botón, ANTES de darle (precio de la tabla de la administración).
export function Costo({ accion, cantidad = 1, alCotizar }: { accion: string; cantidad?: number; alCotizar?: (c: Cotizacion | null) => void }) {
  const [c, setC] = useState<Cotizacion | null>(null);
  useEffect(() => {
    let vivo = true;
    api<Cotizacion>('/api/v2/cotizar', { cuerpo: { accion, cantidad } })
      .then((x) => { if (vivo) { setC(x); alCotizar?.(x); } })
      .catch(() => { if (vivo) { setC(null); alCotizar?.(null); } });
    return () => { vivo = false; };
  }, [accion, cantidad]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!c) return null;
  const titulo = c.a_costo ? `A costo real. Un cliente pagaría ${miles(c.precio_cliente.creditos)} créditos.`
    : c.alcanza ? `Te quedan ${miles(c.saldo)} créditos` : `No te alcanza: tienes ${miles(c.saldo)} créditos`;
  return (
    <span className={`costo ${c.alcanza ? '' : 'no-alcanza'}`} title={titulo}>
      <Zap size={13} aria-hidden="true" />{miles(c.creditos)} créditos{c.alcanza ? '' : ' · no te alcanza'}
    </span>
  );
}
