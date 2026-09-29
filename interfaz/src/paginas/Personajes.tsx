import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Icono } from '../componentes/Icono';

// Tus personajes y el primer paso del asistente: describirlo (o subir una referencia).

export interface FilaPersonaje { id: string; nombre: string; tipo: string; asistente: boolean; imagen: string | null; paso: string | null }
interface EstiloFila { clave: string; nombre: string; descripcion: string }

export const PASOS_PERSONAJE: Record<string, string> = {
  describir: 'Falta dibujar las variantes', elegir: 'Elige una variante', afinar: 'Falta la hoja de referencia',
  probar: 'Falta probarlo en escenas', listo: 'Listo',
};
export const imagenPersonaje = (id: string, archivo: string, v = 0) =>
  `/api/v2/personajes/${id}/archivos/${archivo.includes('/') ? archivo : `referencia/${archivo}`}${v ? `?v=${v}` : ''}`;

export function Personajes() {
  const ir = useNavigate();
  const [filas, setFilas] = useState<FilaPersonaje[] | null>(null);
  const [estilos, setEstilos] = useState<EstiloFila[]>([]);
  const [nombre, setNombre] = useState('');
  const [tipo, setTipo] = useState<'mascota' | 'presentador'>('mascota');
  const [estilo, setEstilo] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [ref, setRef] = useState<File | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api<FilaPersonaje[]>('/api/v2/personajes').then(setFilas).catch(() => setFilas([]));
    api<EstiloFila[]>('/api/v2/recursos/estilos').then((e) => { setEstilos(e); if (e[0]) setEstilo(e[0].clave); }).catch(() => {});
  }, []);

  async function crear() {
    if (!nombre.trim()) { setError('Ponle un nombre al personaje.'); return; }
    if (descripcion.trim().length < 5 && !ref) { setError('Describe el personaje o sube una imagen de referencia.'); return; }
    setEnviando(true); setError('');
    const datos = new FormData();
    datos.append('nombre', nombre.trim()); datos.append('estilo', estilo); datos.append('tipo', tipo);
    datos.append('descripcion', descripcion.trim());
    if (ref) datos.append('referencia', ref);
    try {
      const r = await fetch('/api/v2/personajes', { method: 'POST', body: datos });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error((d as { detail?: string }).detail || `Error ${r.status}`);
      ir(`/personajes/${(d as { id: string }).id}`);
    } catch (e) { setError((e as Error).message); } finally { setEnviando(false); }
  }

  return (
    <div className="pagina">
      <div className="seccion-cab"><h1>Personajes</h1></div>
      <p className="tenue">Un personaje fijo sale igual en todos los videos del canal: se dibuja una vez, se afina y queda con su hoja de referencia.</p>

      <section className="caja-idea personaje-nuevo">
        <h2>Nuevo personaje</h2>
        <div className="caja-fila">
          <label className="campo crece">Nombre<input value={nombre} maxLength={60} onChange={(e) => setNombre(e.target.value)} placeholder="Ej.: Sapiens" /></label>
          <label className="selector"><span>Estilo</span>
            <select value={estilo} onChange={(e) => setEstilo(e.target.value)}>
              {estilos.map((x) => <option key={x.clave} value={x.clave}>{x.nombre}</option>)}
            </select>
          </label>
          <div className="alternar" role="group" aria-label="Tipo">
            <button className={tipo === 'mascota' ? 'sel' : ''} onClick={() => setTipo('mascota')} title="Dibujo que acompaña las escenas">Mascota</button>
            <button className={tipo === 'presentador' ? 'sel' : ''} onClick={() => setTipo('presentador')} title="Persona que presenta el video">Presentador</button>
          </div>
        </div>
        <textarea rows={4} value={descripcion} onChange={(e) => setDescripcion(e.target.value)}
          placeholder="Descríbelo: qué es, cómo es su cara y su cuerpo, colores, ropa, algo que lo distinga. Ej.: un neandertal bajito y simpático, barba castaña, túnica de piel, lanza de madera, ojos grandes y curiosos." />
        {error && <p className="error">{error}</p>}
        <div className="caja-pie">
          <label className="boton-borde pequeno subir">{ref ? `Referencia: ${ref.name}` : 'Subir referencia (opcional)'}
            <input type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={(e) => setRef(e.target.files?.[0] ?? null)} />
          </label>
          <span className="tenue pequeno crece">Describirlo no cuesta. Luego cada imagen del asistente se cobra aparte y te lo digo antes.</span>
          <button className="boton-primario" onClick={crear} disabled={enviando}><Icono nombre="personaje" tam={18} /> {enviando ? 'Creando…' : 'Empezar'}</button>
        </div>
      </section>

      <div className="rejilla-personajes">
        {(filas ?? []).map((p) => {
          const tarjeta = (
            <>
              <div className="pj-img">{p.imagen ? <img src={imagenPersonaje(p.id, p.imagen)} alt="" /> : <Icono nombre="personaje" tam={34} />}</div>
              <b>{p.nombre}</b>
              <span className="tenue pequeno">{p.tipo === 'presentador' ? 'Presentador' : 'Mascota'} · {p.asistente ? PASOS_PERSONAJE[p.paso ?? ''] ?? '' : 'Viene del estilo'}</span>
            </>
          );
          return p.asistente
            ? <Link key={p.id} to={`/personajes/${p.id}`} className="tarjeta-personaje">{tarjeta}</Link>
            : <article key={p.id} className="tarjeta-personaje">{tarjeta}</article>;
        })}
      </div>
    </div>
  );
}
