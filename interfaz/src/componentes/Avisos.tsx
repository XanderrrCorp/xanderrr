import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Bell, CircleAlert, CircleCheck } from 'lucide-react';
import { api, type Aviso } from '../api';

// Campana de avisos («tu video está listo»). Se revisa cada 20 s; lo nuevo aparece también como mensaje flotante.
export function Avisos() {
  const [lista, setLista] = useState<Aviso[]>([]);
  const [sinLeer, setSinLeer] = useState(0);
  const [abierto, setAbierto] = useState(false);
  const [flotante, setFlotante] = useState<Aviso | null>(null);
  const vistos = useRef<Set<string> | null>(null);
  const caja = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const traer = () => api<{ avisos: Aviso[]; sin_leer: number }>('/api/v2/avisos').then((r) => {
      if (vistos.current) {
        const nuevo = r.avisos.find((a) => !vistos.current!.has(a.id) && !a.leido);
        if (nuevo) setFlotante(nuevo);
      }
      vistos.current = new Set(r.avisos.map((a) => a.id));
      setLista(r.avisos); setSinLeer(r.sin_leer);
    }).catch(() => {});
    traer();
    const id = window.setInterval(traer, 20000);
    return () => window.clearInterval(id);
  }, []);
  useEffect(() => {
    if (!flotante) return;
    const id = window.setTimeout(() => setFlotante(null), 12000);
    return () => window.clearTimeout(id);
  }, [flotante]);
  useEffect(() => {
    const fuera = (e: MouseEvent) => { if (caja.current && !caja.current.contains(e.target as Node)) setAbierto(false); };
    document.addEventListener('mousedown', fuera);
    return () => document.removeEventListener('mousedown', fuera);
  }, []);

  const abrir = () => {
    setAbierto(!abierto);
    if (!abierto && sinLeer) api('/api/v2/avisos/leidos', { cuerpo: {} }).then(() => setSinLeer(0)).catch(() => {});
  };
  const Icono = ({ a }: { a: Aviso }) => (a.tipo === 'listo' ? <CircleCheck size={18} className="ic-ok" /> : <CircleAlert size={18} className="ic-mal" />);

  return (
    <div className="avisos" ref={caja}>
      <button className="boton-icono campana" onClick={abrir} aria-label={`Avisos${sinLeer ? `: ${sinLeer} sin leer` : ''}`} aria-expanded={abierto}>
        <Bell size={19} />{sinLeer > 0 && <span className="punto-aviso">{sinLeer}</span>}
      </button>
      {abierto && (
        <div className="panel-avisos" role="dialog" aria-label="Avisos">
          <b>Avisos</b>
          {lista.length === 0 ? <p className="tenue pequeno">Cuando un video termine, te avisamos aquí (y por correo si lo configuraste en Ajustes).</p>
            : lista.map((a) => (
              <a key={a.id} className="aviso-fila" href={a.enlace ?? '#'}>
                <Icono a={a} /><span><b>{a.titulo}</b><span className="tenue pequeno">{new Date(a.fecha * 1000).toLocaleString('es-CO')}</span></span>
              </a>
            ))}
        </div>
      )}
      {flotante && createPortal(
        <a className={`flotante ${flotante.tipo}`} href={flotante.enlace ?? '#'} role="status">
          <Icono a={flotante} /><span><b>{flotante.titulo}</b><span className="pequeno">{flotante.tipo === 'listo' ? 'Toca para verlo' : 'Toca para intentar otra vez'}</span></span>
        </a>, document.body,
      )}
    </div>
  );
}
