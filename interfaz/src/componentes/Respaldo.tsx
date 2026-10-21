import { useEffect, useState } from 'react';
import { ShieldCheck, ShieldAlert, X } from 'lucide-react';
import { api, type Respaldo as R } from '../api';

const gb = (b = 0) => (b > 2 ** 30 ? `${(b / 2 ** 30).toFixed(1)} GB` : `${Math.max(1, Math.round(b / 2 ** 20))} MB`);

// Al abrir Xandart: si la copia de seguridad de antes de actualizar salió bien y dónde quedó (o por qué no).
export function AvisoRespaldo() {
  const [r, setR] = useState<R | null>(null);
  useEffect(() => { api<R>('/api/v2/respaldo').then(setR).catch(() => {}); }, []);
  if (!r || r.estado === 'ninguna' || r.estado === 'movida' || (r.estado === 'ok' && r.visto)) return null;
  if (r.estado === 'error') {
    return (
      <div className="aviso-prep malo" role="alert">
        <ShieldAlert size={18} /> <b>No se pudo hacer la copia de seguridad, así que NO se actualizó nada.</b>{' '}
        Tus videos y proyectos siguen intactos. Motivo: {r.error} Cuando lo arregles, cierra y vuelve a abrir Xandart.
      </div>
    );
  }
  return (
    <div className="aviso-prep bueno" role="status">
      <ShieldCheck size={18} />
      <span><b>Copia de seguridad hecha bien</b> antes de actualizar Xandart ({gb(r.total_bytes)}
        {r.partes?.proyectos ? `, ${r.partes.proyectos.toLocaleString('es-CO')} archivos de tus proyectos` : ''}). Quedó en:{' '}
        <code className="ruta">{r.carpeta}</code></span>
      <button className="boton-icono" aria-label="Entendido" title="Entendido"
        onClick={() => api<R>('/api/v2/respaldo/visto', { cuerpo: {} }).then(setR).catch(() => setR(null))}><X size={16} /></button>
    </div>
  );
}
