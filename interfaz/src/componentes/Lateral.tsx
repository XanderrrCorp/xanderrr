import { useEffect, useRef, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { Icono } from './Icono';
import { paginaVieja } from '../api';

// Menú lateral: una barra angosta con los grupos; cada grupo abre un panel con sus herramientas.
interface Herramienta { nombre: string; icono: string; ir: string; pronto?: boolean; externo?: boolean }
interface Grupo { clave: string; nombre: string; icono: string; secciones: { titulo: string; items: Herramienta[] }[] }

const GRUPOS: Grupo[] = [
  {
    clave: 'crear', nombre: 'Crear', icono: 'chispa', secciones: [
      { titulo: 'Producir', items: [
        { nombre: 'Video largo', icono: 'video', ir: '/' },
        { nombre: 'Short vertical', icono: 'short', ir: '/videos' },
        { nombre: 'Miniatura', icono: 'miniatura', ir: '/videos' },
        { nombre: 'Canal Tracy', icono: 'video', ir: '/tracy' },
        { nombre: 'Hazlo con Calma', icono: 'video', ir: '/calma' },
        { nombre: 'El Calvo Explica', icono: 'video', ir: '/explica' },
      ] },
      { titulo: 'Identidad', items: [
        { nombre: 'Personaje', icono: 'personaje', ir: '/pronto/personaje', pronto: true },
        { nombre: 'Estilo', icono: 'estilo', ir: '/pronto/estilo', pronto: true },
        { nombre: 'Formato', icono: 'formatos', ir: '/pronto/formato', pronto: true },
      ] },
    ],
  },
  {
    clave: 'recursos', nombre: 'Mis recursos', icono: 'videos', secciones: [
      { titulo: 'Lo tuyo', items: [
        { nombre: 'Mis videos', icono: 'videos', ir: '/videos' },
        { nombre: 'Canales', icono: 'canal', ir: '/canales' },
        { nombre: 'Personajes', icono: 'personaje', ir: '/pronto/personajes', pronto: true },
        { nombre: 'Estilos', icono: 'estilo', ir: '/pronto/estilos', pronto: true },
        { nombre: 'Sonidos', icono: 'sonidos', ir: '/#sonidos', externo: true },
      ] },
    ],
  },
  {
    clave: 'inspiracion', nombre: 'Inspiración', icono: 'explorar', secciones: [
      { titulo: 'Para empezar', items: [
        { nombre: 'Formatos', icono: 'formatos', ir: '/formatos' },
        { nombre: 'Ideas de videos', icono: 'ideas', ir: '/pronto/ideas', pronto: true },
      ] },
    ],
  },
];

export function Lateral({ admin, abierto, cerrar }: { admin: boolean; abierto: boolean; cerrar: () => void }) {
  const [panel, setPanel] = useState<string | null>(null);
  const caja = useRef<HTMLDivElement>(null);
  const ir = useNavigate();
  const lugar = useLocation();

  useEffect(() => { setPanel(null); cerrar(); }, [lugar.pathname]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const fuera = (e: MouseEvent) => { if (caja.current && !caja.current.contains(e.target as Node)) setPanel(null); };
    document.addEventListener('mousedown', fuera);
    return () => document.removeEventListener('mousedown', fuera);
  }, []);

  const abrir = (h: Herramienta) => (h.externo ? (window.location.href = h.ir) : ir(h.ir));
  const grupo = GRUPOS.find((g) => g.clave === panel);

  return (
    <div ref={caja} className={`lateral ${abierto ? 'abierto' : ''}`}>
      <nav className="riel" aria-label="Menú principal">
        <NavLink to="/" end className="riel-item"><span className="riel-ic"><Icono nombre="inicio" /></span>Inicio</NavLink>
        {GRUPOS.map((g) => (
          <button key={g.clave} className={`riel-item ${panel === g.clave ? 'activo' : ''} ${g.clave === 'crear' ? 'crear' : ''}`}
            onClick={() => setPanel(panel === g.clave ? null : g.clave)} aria-expanded={panel === g.clave}>
            <span className="riel-ic"><Icono nombre={g.icono} /></span>{g.nombre}
          </button>
        ))}
        <span className="crece" />
        <NavLink to="/planes" className="riel-item"><span className="riel-ic"><Icono nombre="planes" /></span>Planes</NavLink>
        {admin && <a href="/admin" className="riel-item"><span className="riel-ic"><Icono nombre="admin" /></span>Admin</a>}
        <a href={paginaVieja()} className="riel-item" title="Claves y ajustes (en la página de siempre)">
          <span className="riel-ic"><Icono nombre="ajustes" /></span>Ajustes</a>
      </nav>
      {grupo && (
        <div className="panel-grupo" role="menu">
          {grupo.secciones.map((s) => (
            <div key={s.titulo}>
              <h4>{s.titulo}</h4>
              <div className="tiles">
                {s.items.map((h) => (
                  <button key={h.nombre} className="tile" onClick={() => abrir(h)} role="menuitem">
                    <Icono nombre={h.icono} tam={22} />
                    <span>{h.nombre}</span>
                    {h.pronto && <em>pronto</em>}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
