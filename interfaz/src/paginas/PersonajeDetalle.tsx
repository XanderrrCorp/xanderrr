import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Check } from 'lucide-react';
import { api } from '../api';
import { Costo } from '../componentes/Costo';
import { minutosTexto } from '../componentes/EnMarcha';
import { Esqueleto, ErrorAmable, Girando } from '../componentes/Estados';
import { imagenPersonaje } from './Personajes';

interface Imagen { archivo: string; nota: string }
interface Detalle {
  id: string; nombre: string; tipo: string; estilo: string; descripcion: string; paso: string;
  variantes: Imagen[]; elegida: string | null; hoja: Record<string, string>; pruebas: Imagen[];
  imagenes_por_paso: Record<string, number>; gastado_usd: number; poses_hechas: string[];
  canales: { id: string; nombre: string; asignado: boolean }[];
  trabajo: { nombre: string; mensaje: string; progreso: number; activo: boolean; error: string | null; segundos: number } | null;
}

const PASOS = [['elegir', 'Variantes'], ['afinar', 'Elegida'], ['probar', 'Hoja de referencia'], ['listo', 'Probado']];
const ORDEN = ['describir', 'elegir', 'afinar', 'probar', 'listo'];

// El asistente de personaje: dibujar variantes → elegir una → afinarla → hoja de referencia → probar en escenas.
export function PersonajeDetalle() {
  const { id = '' } = useParams();
  const [p, setP] = useState<Detalle | null>(null);
  const [error, setError] = useState('');
  const [instruccion, setInstruccion] = useState('');
  const [v, setV] = useState(0);

  useEffect(() => {
    let vivo = true;
    let espera: number | undefined;
    const traer = async () => {
      try {
        const d = await api<Detalle>(`/api/v2/personajes/${id}`);
        if (!vivo) return;
        setP(d); setV((x) => x + (d.trabajo?.activo ? 0 : 1));
        if (d.trabajo?.activo) espera = window.setTimeout(traer, 2500);
      } catch (e) { if (vivo) setError((e as Error).message); }
    };
    traer();
    return () => { vivo = false; window.clearTimeout(espera); };
  }, [id, p?.trabajo?.activo]); // eslint-disable-line react-hooks/exhaustive-deps

  async function hacer(ruta: string, cuerpo: unknown = {}) {
    setError('');
    try { setP(await api<Detalle>(`/api/v2/personajes/${id}/${ruta}`, { cuerpo })); } catch (e) { setError((e as Error).message); }
  }

  if (!p) return <div className="pagina">{error ? <ErrorAmable texto={error} /> : <Esqueleto filas={6} />}</div>;
  const t = p.trabajo;
  const ocupado = !!t?.activo;
  const img = (a: string) => imagenPersonaje(p.id, a, v);
  const n = p.imagenes_por_paso;
  const pasoI = ORDEN.indexOf(p.paso);

  return (
    <div className="pagina">
      <Link to="/personajes" className="tenue pequeno">← Personajes</Link>
      <div className="seccion-cab" style={{ marginTop: 6 }}><h1>{p.nombre}</h1>
        <span className="etiqueta">{p.tipo === 'presentador' ? 'Presentador' : 'Mascota'}</span></div>
      <ol className="pasos">
        {PASOS.map(([clave, nombre], i) => {
          const hecho = pasoI > ORDEN.indexOf(clave) || p.paso === 'listo';
          return <li key={clave} className={hecho ? 'ok' : ORDEN[pasoI] === clave ? 'va' : ''}>
            <i>{hecho ? <Check size={13} strokeWidth={3} /> : i + 1}</i>{nombre}</li>;
        })}
      </ol>
      {ocupado && (
        <div className="rev-tarjeta" style={{ marginTop: 14 }}>
          <Girando texto={`${t!.nombre}… ${t!.mensaje}`} />
          <div className="barra-progreso" style={{ marginTop: 10 }}><i style={{ width: `${Math.round(t!.progreso * 100)}%` }} /></div>
          {t!.progreso > 0.05 && <span className="tenue pequeno">Faltan {minutosTexto(t!.segundos / t!.progreso * (1 - t!.progreso))} (estimado)</span>}
        </div>
      )}
      {t?.error && !ocupado && <ErrorAmable titulo="El último paso no terminó" texto={t.error} />}
      {error && <ErrorAmable texto={error} />}

      {/* 1. variantes */}
      <section className="rev-tarjeta" style={{ marginTop: 14 }}>
        <h2>Variantes</h2>
        <p className="tenue pequeno">{p.descripcion}</p>
        {p.variantes.length > 0 && (
          <div className="pj-variantes">
            {p.variantes.map((x) => (
              <button key={x.archivo} className={`pj-variante ${p.elegida === x.archivo ? 'sel' : ''}`} disabled={ocupado}
                onClick={() => hacer('elegir', { archivo: x.archivo })} title="Elegir esta">
                <img src={img(x.archivo)} alt="" loading="lazy" />
                {p.elegida === x.archivo && <span className="sb-ok"><Check size={12} strokeWidth={3} /></span>}
              </button>
            ))}
          </div>
        )}
        <div className="fila-botones">
          <button className={p.variantes.length ? 'boton-borde' : 'boton-primario'} disabled={ocupado} onClick={() => hacer('variantes', { n: 3 })}>
            {p.variantes.length ? 'Dibujar 3 más' : 'Dibujar 3 variantes'}</button>
          <Costo accion="personaje_imagen" cantidad={n.variantes ?? 3} />
          {p.variantes.length > 0 && !p.elegida && <span className="tenue pequeno">Toca la que más te guste para elegirla.</span>}
        </div>
      </section>

      {/* 2. afinar y hoja */}
      {p.elegida && (
        <section className="rev-tarjeta">
          <h2>Afinar y hoja de referencia</h2>
          <textarea className="campo-texto" rows={2} value={instruccion} onChange={(e) => setInstruccion(e.target.value)}
            placeholder="¿Qué le cambiarías? Ej.: ojos más grandes, sin sombrero, la camisa roja" />
          <div className="fila-botones">
            <button className="boton-borde" disabled={ocupado || instruccion.trim().length < 3}
              onClick={() => { hacer('afinar', { instruccion }); setInstruccion(''); }}>Afinar</button>
            <Costo accion="personaje_imagen" cantidad={n.afinar ?? 1} />
            <span className="crece" />
            <button className="boton-primario" disabled={ocupado} onClick={() => hacer('hoja')}>
              {p.hoja.hoja ? 'Rehacer la hoja' : 'Hacer la hoja de referencia'}</button>
            <Costo accion="personaje_imagen" cantidad={n.hoja ?? 3} />
          </div>
          {Object.keys(p.hoja).length > 0 && (
            <div className="pj-variantes">
              {Object.entries(p.hoja).map(([vista, a]) => (
                <figure key={vista} className="pj-variante"><img src={img(a)} alt={vista} loading="lazy" />
                  <figcaption className="tenue pequeno">{vista.replace('_', ' ')}</figcaption></figure>
              ))}
            </div>
          )}
        </section>
      )}

      {/* 3. probar y usar */}
      {p.hoja.hoja && (
        <section className="rev-tarjeta">
          <h2>Probar en escenas</h2>
          <div className="fila-botones">
            <button className={p.pruebas.length ? 'boton-borde' : 'boton-primario'} disabled={ocupado} onClick={() => hacer('probar')}>
              {p.pruebas.length ? 'Probar otra vez' : 'Probar en 3 escenas'}</button>
            <Costo accion="personaje_imagen" cantidad={n.probar ?? 3} />
          </div>
          {p.pruebas.length > 0 && (
            <div className="pj-variantes ancho">{p.pruebas.map((x) => <figure key={x.archivo} className="pj-variante"><img src={img(x.archivo)} alt="" loading="lazy" /></figure>)}</div>
          )}
          <h3 style={{ marginTop: 18 }}>Sus poses para el canal</h3>
          <p className="tenue pequeno">Señalando con susto, sorpresa y asco: salen en el like, junto a las fotos y al final
            del video. Sin ellas, esos momentos quedan sin el personaje.</p>
          <div className="fila-botones">
            {p.poses_hechas.length >= (n.poses ?? 3) ? <span className="ok-texto"><Check size={16} /> Poses listas</span> : <>
              <button className="boton-primario" disabled={ocupado} onClick={() => hacer('poses')}>Hacer sus poses</button>
              <Costo accion="personaje_imagen" cantidad={(n.poses ?? 3) - p.poses_hechas.length} />
            </>}
          </div>
          {p.poses_hechas.length > 0 && (
            <div className="pj-variantes">{p.poses_hechas.map((x) => (
              <figure key={x} className="pj-variante"><img src={img(`imagenes/pose_${x}.png`)} alt={x} loading="lazy" />
                <figcaption className="tenue pequeno">{x.replace('_', ' ')}</figcaption></figure>))}</div>
          )}
          {p.canales.length > 0 && (
            <>
              <h3 style={{ marginTop: 18 }}>Usarlo en un canal</h3>
              <div className="fila-botones">
                {p.canales.map((c) => (
                  <label key={c.id} className="casilla">
                    <input type="checkbox" checked={c.asignado} disabled={ocupado}
                      onChange={(e) => hacer('canal', { canal_id: c.id, usar: e.target.checked })} />{c.nombre}
                  </label>
                ))}
              </div>
            </>
          )}
        </section>
      )}
      <p className="tenue pequeno">Gastado en este personaje: ${p.gastado_usd.toFixed(2)}</p>
    </div>
  );
}
