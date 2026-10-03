import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, archivo } from '../api';
import { Icono } from '../componentes/Icono';

// Plantilla «texto_izquierda_retrato_derecha»: Claude propone una opción por fórmula, cada una se arma
// como miniatura con el fondo de este video y se elige la mejor. Editar el texto no cambia el fondo.

export const LAYOUT_TEXTO = 'texto_izquierda_retrato_derecha';

interface Opcion { formula: number | null; texto: string; avisos: string[]; archivo?: string; editada?: boolean }
interface Config { canal: string; nombre: string; acento: string; acento_calido: string; paleta: string; rotulo: string; fuente_fondos: string }
interface EstadoTexto {
  layout: string; carpeta: string; opciones: Opcion[]; elegida: number | null; paleta: string; paleta_usada?: string; acento?: string;
  fondo: string | null; miniatura: string | null; config: Config; tiene_retrato: boolean; fondos_canal: string[];
  gastado: string; precio_fondo_usd: number; duracion?: string;
  trabajo: { paso: string; mensaje: string; progreso: number; activo: boolean; error: string | null; segundos: number } | null;
}

const FORMULAS: Record<number, string> = { 1: 'Enfócate en X / no en Y', 2: 'Vuélvete X / en [duración]', 3: 'De la X / a la Y', 4: 'Oblígate a X' };

export function MiniaturaTexto({ slug }: { slug: string }) {
  const [m, setM] = useState<EstadoTexto | null>(null);
  const [aviso, setAviso] = useState('');
  const [ver, setVer] = useState(() => Date.now());
  const [nuevo, setNuevo] = useState('');

  const url = (r: string) => `${archivo(slug, r)}?v=${ver}`;
  const cargar = useCallback(async () => {
    try {
      const d = await api<EstadoTexto>(`/api/videos/${slug}/miniatura`);
      setM((antes) => { if (antes?.trabajo?.activo && !d.trabajo?.activo) setVer(Date.now()); return d; });
    } catch (e) { setAviso((e as Error).message); }
  }, [slug]);
  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => {
    if (!m?.trabajo?.activo) return;
    const id = window.setTimeout(cargar, 2000);
    return () => window.clearTimeout(id);
  }, [m, cargar]);

  const accion = async (ruta: string, cuerpo: unknown = {}, metodo = 'POST') => {
    setAviso('');
    try { setM(await api<EstadoTexto>(`/api/videos/${slug}/miniatura${ruta}`, { metodo, cuerpo })); setVer(Date.now()); return true; }
    catch (e) { setAviso((e as Error).message); return false; }
  };

  if (!m) return <div className="pagina"><p className="tenue">{aviso || 'Cargando…'}</p></div>;
  const t = m.trabajo, trabajando = !!t?.activo;
  const canal = m.config.canal;

  return (
    <div className="pagina revision">
      <div className="rev-cab">
        <Link to={`/videos/${slug}`} className="tenue pequeno">← Volver al video</Link>
        <span className="crece" />
        <span className="chip-gasto">Miniaturas: {m.gastado}</span>
      </div>
      <h1 className="rev-titulo">Miniatura · {m.config.nombre}</h1>
      <p className="tenue">Texto grande a la izquierda y retrato a la derecha. Claude propone una opción por fórmula; edita el texto y se vuelve a armar con el mismo fondo, sin gastar.</p>

      {trabajando && t && (
        <section className="rev-tarjeta">
          <b>{t.paso === 'fondo' ? 'Cambiando el fondo' : 'Haciendo las opciones'}</b>
          <div className="barra-progreso"><i style={{ width: `${Math.round(t.progreso * 100)}%` }} /></div>
          <span className="tenue pequeno">{t.mensaje} · {Math.floor(t.segundos / 60)} min {t.segundos % 60} s</span>
        </section>
      )}
      {!trabajando && t?.error && <div className="rev-error">No se pudo terminar: {t.error}</div>}
      {aviso && <div className="rev-error">{aviso}</div>}
      {!m.tiene_retrato && <div className="rev-error">Este canal todavía no tiene retrato: súbelo abajo (PNG sin fondo) para que salga a la derecha.</div>}

      {m.opciones.length === 0 && !trabajando && (
        <section className="rev-tarjeta">
          <h2>Hacer las opciones</h2>
          <p>Claude escribe 4 textos (gratis, va por tu suscripción) y se arman con un fondo distinto al del video anterior
            {m.config.fuente_fondos === 'generar' ? ` (fondo nuevo generado ≈ ${m.precio_fondo_usd} USD)` : ' (rotado de la carpeta del canal: gratis)'}.</p>
          <button className="boton-primario" onClick={() => accion('/producir')}><Icono nombre="miniatura" tam={18} /> Producir opciones</button>
        </section>
      )}

      {m.opciones.length > 0 && (
        <section className="rev-tarjeta">
          <div className="fila-botones">
            <h2 className="crece">Elige una {m.duracion && <span className="tenue pequeno">· duración del video: {m.duracion}</span>}</h2>
            <label className="campo">Paleta
              <select value={m.paleta} disabled={trabajando} onChange={(e) => accion('/texto/paleta', { paleta: e.target.value }, 'PUT')}>
                <option value="auto">Automática ({m.paleta_usada === 'calida' ? 'amarilla' : 'turquesa'})</option>
                <option value="fria">Turquesa (fondos azules o morados)</option>
                <option value="calida">Amarilla (fondos negros o dorados)</option>
              </select></label>
          </div>
          <div className="mt-opciones">
            {m.opciones.map((o, i) => (
              <OpcionTexto key={`${i}-${ver}`} o={o} i={i} sel={m.elegida === i} url={url} trabajando={trabajando}
                elegir={() => accion(`/texto/elegir/${i}`)} guardar={(texto) => accion(`/texto/opciones/${i}`, { texto }, 'PUT')} />
            ))}
          </div>
          <div className="fila-botones">
            <input className="mt-nuevo" value={nuevo} placeholder="Otra opción a mano: OBLÍGATE A / *EMPEZAR* / HOY" onChange={(e) => setNuevo(e.target.value)} />
            <button className="boton-borde" disabled={!nuevo.trim() || trabajando} onClick={async () => { if (await accion('/texto/opciones', { texto: nuevo })) setNuevo(''); }}>Agregar</button>
          </div>
          <div className="fila-botones">
            {m.miniatura && <a className="boton-primario" href={`${archivo(slug, m.miniatura)}?descargar=true`}>Descargar la elegida (1280×720)</a>}
            <span className="crece" />
            <button className="boton-borde pequeno" disabled={trabajando} onClick={() => accion('/texto/fondo', { generar: false })}>Otro fondo de la carpeta (gratis)</button>
            <button className="boton-borde pequeno" disabled={trabajando} onClick={() => {
              if (window.confirm(`Se genera un fondo nuevo (≈ ${m.precio_fondo_usd} USD). ¿Seguir?`)) accion('/texto/fondo', { generar: true });
            }}>Generar fondo nuevo</button>
            <button className="boton-icono pequeno" disabled={trabajando} onClick={() => {
              if (window.confirm('Claude vuelve a escribir las 4 opciones (el fondo se queda). ¿Seguir?')) accion('/producir');
            }}>Pedir otras opciones</button>
          </div>
          <p className="tenue pequeno">Formato: líneas separadas con «/», la línea de color entre asteriscos. De 3 a 4 líneas, máximo 3 palabras por línea, siempre en mayúsculas.</p>
        </section>
      )}

      <ConfigCanal canal={canal} alCambiar={() => { setVer(Date.now()); cargar(); }} />
    </div>
  );
}

function OpcionTexto({ o, i, sel, url, trabajando, elegir, guardar }: {
  o: Opcion; i: number; sel: boolean; url: (r: string) => string; trabajando: boolean;
  elegir: () => void; guardar: (texto: string) => Promise<boolean>;
}) {
  const [texto, setTexto] = useState(o.texto);
  return (
    <div className={`mt-opcion ${sel ? 'sel' : ''}`}>
      <span className="tenue pequeno">{o.formula ? `${o.formula}. ${FORMULAS[o.formula]}` : `Escrita a mano`}{sel ? ' · elegida ★' : ''}</span>
      {o.archivo && <img src={url(`miniatura_texto/${o.archivo}`)} alt={`Opción ${i + 1}`} onClick={() => !trabajando && elegir()} />}
      <input value={texto} maxLength={200} onChange={(e) => setTexto(e.target.value)} />
      {o.avisos.length > 0 && <span className="mt-aviso">⚠ {o.avisos.join(' · ')}</span>}
      <div className="fila-botones">
        <button className="boton-borde pequeno" disabled={trabajando || texto === o.texto} onClick={() => guardar(texto)}>Volver a armar</button>
        <span className="crece" />
        <button className={sel ? 'boton-primario pequeno' : 'boton-borde pequeno'} disabled={trabajando} onClick={elegir}>{sel ? 'Elegida' : 'Elegir esta'}</button>
      </div>
    </div>
  );
}

interface ConfigCompleta extends Config { tiene_retrato: boolean; fondos: string[]; prompt_fondo: string }

function ConfigCanal({ canal, alCambiar }: { canal: string; alCambiar: () => void }) {
  const [c, setC] = useState<ConfigCompleta | null>(null);
  const [aviso, setAviso] = useState('');
  const [v, setV] = useState(() => Date.now());
  useEffect(() => { api<ConfigCompleta>(`/api/canales/${canal}/miniatura`).then(setC).catch((e) => setAviso(e.message)); }, [canal]);
  if (!c) return null;

  const guardar = async (cambios: Partial<ConfigCompleta>) => {
    setAviso('');
    try { setC(await api<ConfigCompleta>(`/api/canales/${canal}/miniatura/texto`, { metodo: 'PUT', cuerpo: cambios })); alCambiar(); }
    catch (e) { setAviso((e as Error).message); }
  };
  const subir = async (ruta: string, f: File | undefined) => {
    if (!f) return;
    const datos = new FormData(); datos.append('archivo', f);
    const r = await fetch(`/api/canales/${canal}/miniatura/${ruta}`, { method: 'POST', body: datos });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) { setAviso((d as { detail?: string }).detail || `Error ${r.status}`); return; }
    setC(d as ConfigCompleta); setV(Date.now()); alCambiar();
  };

  return (
    <section className="rev-tarjeta">
      <h2>Plantilla del canal · {c.nombre}</h2>
      {aviso && <div className="rev-error">{aviso}</div>}
      <div className="mt-config">
        <div className="mt-retrato">
          <span className="tenue pequeno">Retrato: cabeza y hombros, PNG sin fondo o foto con fondo blanco liso</span>
          {c.tiene_retrato ? <img src={`/canales/${canal}/miniatura/retrato.png?v=${v}`} alt="Retrato" /> : <div className="sin-img">sin retrato</div>}
          <label className="boton-borde pequeno subir">Subir retrato
            <input type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={(e) => subir('retrato', e.target.files?.[0])} /></label>
        </div>
        <div>
          <div className="mini-campos">
            <label className="campo">Turquesa (fondos azules o morados)<input type="color" defaultValue={c.acento} onBlur={(e) => guardar({ acento: e.target.value })} /></label>
            <label className="campo">Amarillo (fondos negros o dorados)<input type="color" defaultValue={c.acento_calido} onBlur={(e) => guardar({ acento_calido: e.target.value })} /></label>
            <label className="campo">Paleta del canal<select value={c.paleta} onChange={(e) => guardar({ paleta: e.target.value })}>
              <option value="auto">Automática según el fondo</option><option value="fria">Siempre turquesa</option><option value="calida">Siempre amarilla</option></select></label>
          </div>
          <label className="campo">Rótulo debajo del texto (opcional)<input defaultValue={c.rotulo} maxLength={60} onBlur={(e) => e.target.value !== c.rotulo && guardar({ rotulo: e.target.value })} /></label>
          <label className="campo">Fondos<select value={c.fuente_fondos} onChange={(e) => guardar({ fuente_fondos: e.target.value })}>
            <option value="carpeta">Rotar entre los fondos de la carpeta (gratis)</option>
            <option value="generar">Generar uno nuevo en cada video (cuesta una imagen)</option></select></label>
        </div>
      </div>
      <h3 className="rev-seccion">Fondos del canal ({c.fondos.length})</h3>
      <div className="mini-refs">
        {c.fondos.map((f) => <div key={f} className="mini-ref"><img className="mt-fondo" src={`/canales/${canal}/miniatura/fondos/${encodeURIComponent(f)}?v=${v}`} alt={f} /></div>)}
      </div>
      <label className="boton-borde pequeno subir">Subir fondo 16:9
        <input type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={(e) => subir('fondos', e.target.files?.[0])} /></label>
    </section>
  );
}
