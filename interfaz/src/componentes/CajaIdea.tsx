import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, miles, type Canal, type Cotizacion, type Formato, type VideoDetalle } from '../api';
import { Icono } from './Icono';

// Formatos que vienen en camino (se muestran para que se sepa que llegan, sin poder elegirse).
const EN_CAMINO = ['Hombre de palo', 'Top X', 'Narración de historias', 'Personaje garabato', 'Videos para dormir'];

export function CajaIdea({ creado }: { creado: (slug: string) => void }) {
  const ir = useNavigate();
  const [formatos, setFormatos] = useState<Formato[]>([]);
  const [canales, setCanales] = useState<Canal[]>([]);
  const [formato, setFormato] = useState('');
  const [canal, setCanal] = useState('');
  const [minutos, setMinutos] = useState(9);
  const [modo, setModo] = useState<'auto' | 'personalizado'>('auto');
  const [idea, setIdea] = useState('');
  const [disfraz, setDisfraz] = useState(false);
  const [cot, setCot] = useState<Cotizacion | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api<Formato[]>('/api/v2/recursos/formatos').then((f) => { setFormatos(f); if (f[0]) setFormato(f[0].id); }).catch(() => {});
    api<Canal[]>('/api/v2/canales').then((c) => { setCanales(c); if (c[0]) setCanal(c[0].clave); }).catch(() => {});
  }, []);
  const f = formatos.find((x) => x.id === formato);
  const duraciones = f?.datos.duraciones_min ?? [6, 9, 11];
  useEffect(() => { if (f?.datos.duracion_min) setMinutos(f.datos.duracion_min); }, [formato]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    api<Cotizacion>('/api/v2/cotizar', { cuerpo: { accion: 'video_minuto', cantidad: minutos } }).then(setCot).catch(() => setCot(null));
  }, [minutos]);

  async function crear() {
    if (idea.trim().length < 3) { setError('Escribe la idea del video (por ejemplo, el tema y el giro).'); return; }
    setEnviando(true); setError('');
    try {
      const v = await api<VideoDetalle>('/api/videos', { cuerpo: { tema: idea.trim(), minutos, canal: canal || null, disfraz } });
      setIdea('');
      if (modo === 'personalizado') ir(`/videos/${v.slug}`);
      else creado(v.slug);
    } catch (e) { setError((e as Error).message); } finally { setEnviando(false); }
  }

  return (
    <section className="caja-idea">
      <div className="caja-fila">
        <label className="selector">
          <span>Formato</span>
          <select value={formato} onChange={(e) => setFormato(e.target.value)}>
            {formatos.map((x) => <option key={x.id} value={x.id}>{x.nombre}</option>)}
            <optgroup label="En camino">{EN_CAMINO.map((n) => <option key={n} disabled>{n} · pronto</option>)}</optgroup>
          </select>
        </label>
        <label className="selector">
          <span>Canal</span>
          <select value={canal} onChange={(e) => setCanal(e.target.value)}>
            {canales.map((c) => <option key={c.id} value={c.clave}>{c.nombre}</option>)}
          </select>
        </label>
        <div className="chips" role="group" aria-label="Duración">
          {duraciones.map((d) => (
            <button key={d} className={`chip ${minutos === d ? 'sel' : ''}`} onClick={() => setMinutos(d)}>{d} min</button>
          ))}
        </div>
        <span className="crece" />
        <div className="alternar" role="group" aria-label="Modo">
          <button className={modo === 'auto' ? 'sel' : ''} onClick={() => setModo('auto')}
            title="Xandart escribe el guion y te avisa cuando toca aprobar">Auto</button>
          <button className={modo === 'personalizado' ? 'sel' : ''} onClick={() => setModo('personalizado')}
            title="Abre el video para que ajustes el guion antes de las imágenes">Personalizado</button>
        </div>
      </div>
      <textarea value={idea} onChange={(e) => setIdea(e.target.value)} rows={4}
        placeholder={f?.datos.idea_ejemplo ? `Ej.: ${f.datos.idea_ejemplo}` : 'Escribe la idea del video…'}
        onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) crear(); }} />
      {error && <p className="error">{error}</p>}
      <div className="caja-pie">
        <label className="casilla" title="Una imagen extra (≈ $0.07): la mascota con un hoodie del animal del video. Solo en las escenas nuevas; las reacciones guardadas salen sin disfraz.">
          <input type="checkbox" checked={disfraz} onChange={(e) => setDisfraz(e.target.checked)} />
          Mascota disfrazada del animal
        </label>
        <span className="tenue">
          {cot ? (cot.a_costo
            ? <>A costo real ≈ {miles(cot.creditos)} créditos · un cliente pagaría {miles(cot.precio_cliente.creditos)}</>
            : <>Cuesta ≈ {miles(cot.creditos)} créditos{cot.alcanza ? '' : ' · no te alcanza el saldo'}</>) : ' '}
        </span>
        <button className="boton-primario" onClick={crear} disabled={enviando || (cot !== null && !cot.alcanza)}>
          <Icono nombre="chispa" tam={18} /> {enviando ? 'Creando…' : 'Crear video'}
        </button>
      </div>
    </section>
  );
}
