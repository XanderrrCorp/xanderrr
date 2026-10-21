import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Check } from 'lucide-react';
import { api } from '../api';
import { ErrorAmable } from '../componentes/Estados';
import { Icono } from '../componentes/Icono';
import type { FilaPersonaje } from './Personajes';
import { imagenPersonaje } from './Personajes';

interface Opcion { id: string; nombre: string; descripcion?: string; publico?: boolean }

const PASOS = ['Nombre', 'Voz', 'Estilo', 'Personaje'];

// Tu primer canal en 4 pasos. Todo se puede cambiar después; el canal nace privado (solo tú lo ves).
export function CanalNuevo() {
  const ir = useNavigate();
  const [paso, setPaso] = useState(0);
  const [nombre, setNombre] = useState('');
  const [voces, setVoces] = useState<Opcion[]>([]);
  const [estilos, setEstilos] = useState<Opcion[]>([]);
  const [personajes, setPersonajes] = useState<FilaPersonaje[]>([]);
  const [voz, setVoz] = useState<string | null>(null);
  const [estilo, setEstilo] = useState<string | null>(null);
  const [personaje, setPersonaje] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api<Opcion[]>('/api/v2/recursos/voces').then(setVoces).catch(() => {});
    api<Opcion[]>('/api/v2/recursos/estilos').then((e) => { setEstilos(e); if (e[0]) setEstilo((x) => x ?? e[0].id); }).catch(() => {});
    api<FilaPersonaje[]>('/api/v2/personajes').then((p) => setPersonajes(p.filter((x) => x.paso === 'listo' || !x.asistente))).catch(() => {});
  }, []);

  const puede = paso === 0 ? nombre.trim().length >= 2 : paso === 2 ? !!estilo : true;
  async function crear() {
    setEnviando(true); setError('');
    try {
      await api('/api/v2/canales', { cuerpo: { nombre: nombre.trim(), voz_id: voz, estilo_id: estilo, personaje_id: personaje } });
      ir('/canales?nuevo=1');
    } catch (e) { setError((e as Error).message); } finally { setEnviando(false); }
  }

  return (
    <div className="pagina onb">
      <div className="onb-pasos" aria-hidden="true">{PASOS.map((p, i) => <div key={p} className={i <= paso ? 'on' : ''} />)}</div>
      <span className="tenue pequeno">Paso {paso + 1} de 4 · Tu canal</span>

      {paso === 0 && <>
        <h1>¿Cómo se llama tu canal?</h1>
        <p className="tenue">El nombre con el que lo reconoces aquí. Puedes cambiarlo después.</p>
        <input className="onb-input" autoFocus value={nombre} maxLength={60} placeholder="Ej.: Animales al límite"
          onChange={(e) => setNombre(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && puede) setPaso(1); }} />
      </>}

      {paso === 1 && <>
        <h1>¿Con qué voz habla?</h1>
        <p className="tenue">La voz que narra todos los videos del canal.</p>
        <div className="opciones">
          <Elegible sel={voz === null} onClick={() => setVoz(null)} icono="sonidos" titulo="La voz de Xandart" texto="La que viene configurada, en español" />
          {voces.map((v) => <Elegible key={v.id} sel={voz === v.id} onClick={() => setVoz(v.id)} icono="sonidos" titulo={v.nombre} texto={v.descripcion} />)}
        </div>
        {voces.length === 0 && <p className="tenue pequeno">Más voces llegan con «clonar voz».</p>}
      </>}

      {paso === 2 && <>
        <h1>¿Cómo se ven sus imágenes?</h1>
        <p className="tenue">El estilo visual del canal. Puedes duplicar uno y ajustarlo después.</p>
        <div className="opciones">
          {estilos.map((e) => <Elegible key={e.id} sel={estilo === e.id} onClick={() => setEstilo(e.id)} icono="estilo"
            titulo={e.nombre} texto={e.descripcion || (e.publico ? 'Catálogo de Xandart' : 'Tuyo')} />)}
        </div>
      </>}

      {paso === 3 && <>
        <h1>¿Tiene un personaje fijo?</h1>
        <p className="tenue">Un presentador o mascota que sale igual en todos los videos. Es opcional.</p>
        <div className="opciones">
          <Elegible sel={personaje === null} onClick={() => setPersonaje(null)} icono="personaje" titulo="Sin personaje propio" texto="Se usa el del estilo, si tiene" />
          {personajes.map((p) => (
            <Elegible key={p.id} sel={personaje === p.id} onClick={() => setPersonaje(p.id)} icono="personaje" titulo={p.nombre}
              texto={p.tipo === 'presentador' ? 'Presentador' : 'Mascota'} imagen={p.imagen ? imagenPersonaje(p.id, p.imagen) : undefined} />
          ))}
        </div>
        <button className="boton-borde pequeno" onClick={() => ir('/personajes/nuevo')}>Crear un personaje nuevo</button>
      </>}

      {error && <div style={{ marginTop: 16 }}><ErrorAmable texto={error} /></div>}
      <div className="onb-pie">
        <button className="boton-borde" onClick={() => (paso === 0 ? ir(-1) : setPaso(paso - 1))}><ArrowLeft size={16} />Atrás</button>
        {paso < 3
          ? <button className="boton-primario" disabled={!puede} onClick={() => setPaso(paso + 1)}>Siguiente: {PASOS[paso + 1].toLowerCase()}<ArrowRight size={16} /></button>
          : <button className="boton-primario" disabled={enviando} onClick={crear}><Check size={16} />{enviando ? 'Creando…' : 'Crear mi canal'}</button>}
      </div>
    </div>
  );
}

function Elegible({ sel, onClick, icono, titulo, texto, imagen }: {
  sel: boolean; onClick: () => void; icono: string; titulo: string; texto?: string; imagen?: string;
}) {
  return (
    <button className={`elegible ${sel ? 'sel' : ''}`} onClick={onClick} aria-pressed={sel}>
      <span className="elegible-ic">{imagen ? <img src={imagen} alt="" /> : <Icono nombre={icono} />}</span>
      <span><b>{titulo}</b>{texto && <span className="tenue pequeno">{texto}</span>}</span>
      {sel && <Check size={18} className="elegible-ok" />}
    </button>
  );
}
