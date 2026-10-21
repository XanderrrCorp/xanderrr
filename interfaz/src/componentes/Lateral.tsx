import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Ellipsis } from 'lucide-react';
import { Icono } from './Icono';
import { modulosEstudio, paginaVieja, type Cuenta, type ModuloEstudio } from '../api';

// Menú lateral (estilo Artbase): Home, Create, Assets e Inspire. En el celular se vuelve una barra abajo con lo
// principal y un botón «Más» que abre el menú completo.
interface Item { nombre: string; icono: string; ir: string; pronto?: boolean; fuera?: boolean }

const CREATE: Item[] = [
  { nombre: 'Producer', icono: 'chispa', ir: '/producir' },
  { nombre: 'Video', icono: 'video', ir: '/producir/video' },
  { nombre: 'Imagen', icono: 'imagen', ir: '/pronto/imagen', pronto: true },
  { nombre: 'Personaje', icono: 'personaje', ir: '/personajes/nuevo' },
  { nombre: 'Estilo', icono: 'estilo', ir: '/estilos/nuevo' },
  { nombre: 'Miniaturas', icono: 'miniatura', ir: '/miniaturas' },
];
const ASSETS: Item[] = [
  { nombre: 'Proyectos', icono: 'proyectos', ir: '/videos' },
  { nombre: 'Personajes', icono: 'personajes', ir: '/personajes' },
  { nombre: 'Estilos', icono: 'estilos', ir: '/estilos' },
  { nombre: 'Media', icono: 'media', ir: '/media' },
  { nombre: 'Canales', icono: 'canal', ir: '/canales' },
];


function Enlace({ i }: { i: Item }) {
  const contenido = <><Icono nombre={i.icono} tam={18} />{i.nombre}{i.pronto && <em>pronto</em>}</>;
  if (i.fuera) return <a className="lat-item" href={i.ir}>{contenido}</a>;
  return <NavLink to={i.ir} end className="lat-item">{contenido}</NavLink>;
}

export function Lateral({ cuenta }: { cuenta: Cuenta | null }) {
  const [abierto, setAbierto] = useState(false);
  const [estudio, setEstudio] = useState<ModuloEstudio[]>([]);       // tus módulos privados: solo los manda el servidor
  useEffect(() => { if (cuenta?.usuario.rol === 'owner') modulosEstudio().then(setEstudio); }, [cuenta?.usuario.rol]);
  const lugar = useLocation();
  useEffect(() => setAbierto(false), [lugar.pathname, lugar.search]);
  const nombre = cuenta?.usuario.nombre || cuenta?.usuario.email || '';
  const ROL: Record<string, string> = { owner: 'Owner', admin: 'Admin', beta: 'Beta' };

  return (
    <>
      <nav className={`lateral ${abierto ? 'abierto' : ''}`} aria-label="Menú principal">
        <NavLink to="/" className="marca"><i>X</i>Xandart</NavLink>
        <Enlace i={{ nombre: 'Home', icono: 'inicio', ir: '/' }} />
        <div className="lat-grupo">Create</div>
        {CREATE.map((i) => <Enlace key={i.nombre} i={i} />)}
        <div className="lat-grupo">Assets</div>
        {ASSETS.map((i) => <Enlace key={i.nombre} i={i} />)}
        <div className="lat-grupo">Inspire</div>
        <Enlace i={{ nombre: 'Inspire', icono: 'explorar', ir: '/formatos' }} />
        {estudio.length > 0 && <>
          <div className="lat-grupo">Tu estudio</div>
          {estudio.map((m) => <Enlace key={m.clave} i={{ nombre: m.menu, icono: m.clave === 'explica' ? 'personaje' : m.clave === 'cola' ? 'videos' : 'video', ir: m.ir }} />)}
        </>}
        <span className="crece" />
        <Enlace i={{ nombre: 'Planes y créditos', icono: 'planes', ir: '/planes' }} />
        <Enlace i={{ nombre: 'Historial de créditos', icono: 'videos', ir: '/creditos' }} />
        {cuenta?.usuario.admin && <Enlace i={{ nombre: 'Cuentas beta', icono: 'personajes', ir: '/cuentas' }} />}
        {cuenta?.usuario.admin && <Enlace i={{ nombre: 'Admin', icono: 'admin', ir: '/admin', fuera: true }} />}
        <Enlace i={{ nombre: 'Liberar espacio', icono: 'proyectos', ir: '/espacio' }} />
        <Enlace i={{ nombre: 'Ajustes', icono: 'ajustes', ir: paginaVieja(), fuera: true }} />
        {cuenta && (
          <NavLink to="/cuenta" className="lat-cuenta" title="Mi cuenta: cambiar contraseña o cerrar sesión">
            <span className="avatar">{nombre.slice(0, 1).toUpperCase()}</span>
            <div><b title={cuenta.usuario.email}>{nombre}</b><span className="tenue pequeno">{ROL[cuenta.usuario.rol] ?? cuenta.usuario.rol}</span></div>
          </NavLink>
        )}
      </nav>
      {abierto && <button className="lat-fondo" aria-label="Cerrar menú" onClick={() => setAbierto(false)} />}
      <nav className="barra-abajo" aria-label="Menú">
        <NavLink to="/" end><Icono nombre="inicio" />Home</NavLink>
        <NavLink to="/producir"><Icono nombre="chispa" />Producer</NavLink>
        <NavLink to="/videos"><Icono nombre="proyectos" />Proyectos</NavLink>
        <NavLink to="/formatos"><Icono nombre="explorar" />Inspire</NavLink>
        <button onClick={() => setAbierto(true)} aria-expanded={abierto}><Ellipsis size={20} />Más</button>
      </nav>
    </>
  );
}
