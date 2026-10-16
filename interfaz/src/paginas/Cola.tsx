import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';

// Cola de la semana: pegas varios guiones de Tracy o varias ideas de Peligro Tropical y Xandart los hace uno detrás
// de otro, solo (déjalo de noche). Un video a la vez: el PC no se traba. Si cierras Xandart, sigue al abrirlo.

interface Item {
  id: string; tipo: 'tracy' | 'peligro' | 'explica'; slug: string; titulo: string; etiqueta?: string;
  estado: 'esperando' | 'haciendo' | 'listo' | 'error'; error: string | null; progreso?: number; mensaje?: string;
}
interface Estado { videos: Item[]; trabajando: boolean; esperando: number }

const NOMBRE_ESTADO: Record<Item['estado'], string> = {
  esperando: 'En espera', haciendo: 'Haciéndose', listo: 'Listo', error: 'Se detuvo',
};

export function Cola() {
  const [e, setE] = useState<Estado | null>(null);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<'tracy' | 'peligro' | 'explica'>('tracy');
  const [etiqueta, setEtiqueta] = useState('');
  const [temas, setTemas] = useState(9);
  const [guiones, setGuiones] = useState([{ titulo: '', guion: '' }]);
  const [ideas, setIdeas] = useState('');
  const [minutos, setMinutos] = useState(9);
  const [enviando, setEnviando] = useState(false);

  const cargar = useCallback(() => api<Estado>('/api/cola').then(setE).catch((x) => setError((x as Error).message)), []);
  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => {
    if (!e?.trabajando) return;
    const id = setInterval(cargar, 3000);
    return () => clearInterval(id);
  }, [e?.trabajando, cargar]);

  const accion = async (ruta: string, cuerpo: unknown = {}) => {
    setError('');
    try { setE(await api<Estado>(ruta, { cuerpo })); return true; } catch (x) { setError((x as Error).message); return false; }
  };

  const agregarTracy = async () => {
    setEnviando(true);
    const ok = await accion('/api/cola/tracy', { guiones: guiones.filter((g) => g.guion.trim().length >= 40), etiqueta });
    if (ok) setGuiones([{ titulo: '', guion: '' }]);
    setEnviando(false);
  };
  const agregarIdeas = async () => {
    const lista = ideas.split('\n').map((l) => l.trim()).filter(Boolean).map((l) => {
      const [tema, ...resto] = l.split('|');
      return { tema: tema.trim(), notas: resto.join('|').trim() };
    });
    setEnviando(true);
    const ok = tab === 'peligro' ? await accion('/api/cola/peligro', { ideas: lista, minutos })
      : await accion('/api/cola/explica', { ideas: lista, temas });
    if (ok) setIdeas('');
    setEnviando(false);
  };

  return (
    <div className="pagina">
      <h1>Cola de la semana</h1>
      <p className="tenue">Pega todos los videos de la semana y dale a «Agregar a la cola». Xandart los hace uno detrás
        de otro, solo: déjalo trabajando de noche. Un video a la vez, para que el PC no se trabe. Si cierras Xandart,
        sigue donde iba cuando lo vuelvas a abrir (lo pagado no se repite).</p>
      {error && <p className="error">{error}</p>}

      <div style={{ display: 'flex', gap: 8, margin: '12px 0' }}>
        <button className={tab === 'tracy' ? 'boton' : 'boton-borde'} onClick={() => setTab('tracy')}>Guiones de Tracy</button>
        <button className={tab === 'peligro' ? 'boton' : 'boton-borde'} onClick={() => setTab('peligro')}>Ideas de Peligro Tropical</button>
        <button className={tab === 'explica' ? 'boton' : 'boton-borde'} onClick={() => setTab('explica')}>Ideas de El Calvo Explica</button>
      </div>

      {tab === 'tracy' ? (
        <section className="rev-tarjeta">
          <label className="pequeno">¿Para qué canal de YouTube son? (para organizarte):{' '}
            <input list="canales-tracy" value={etiqueta} onChange={(ev) => setEtiqueta(ev.target.value)}
              placeholder="Ej.: Mentalidad Imparable" style={{ width: 280 }} /></label>
          <datalist id="canales-tracy">
            {[...new Set((e?.videos || []).filter((x) => x.tipo === 'tracy' && x.etiqueta).map((x) => x.etiqueta as string))]
              .map((n) => <option key={n} value={n} />)}
          </datalist>
          {guiones.map((g, k) => (
            <div key={k} style={{ marginBottom: 14 }}>
              <b>Video {k + 1}</b>
              <input placeholder="Título (opcional)" value={g.titulo} style={{ width: '100%', margin: '6px 0' }}
                onChange={(ev) => setGuiones(guiones.map((x, i) => i === k ? { ...x, titulo: ev.target.value } : x))} />
              <textarea placeholder="Pega aquí el guion completo" rows={6} value={g.guion} style={{ width: '100%' }}
                onChange={(ev) => setGuiones(guiones.map((x, i) => i === k ? { ...x, guion: ev.target.value } : x))} />
              {guiones.length > 1 && <button className="boton-borde pequeno"
                onClick={() => setGuiones(guiones.filter((_, i) => i !== k))}>Quitar este</button>}
            </div>
          ))}
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="boton-borde" onClick={() => setGuiones([...guiones, { titulo: '', guion: '' }])}>+ Otro guion</button>
            <button className="boton" disabled={enviando || !guiones.some((g) => g.guion.trim().length >= 40)}
              onClick={agregarTracy}>Agregar a la cola ({guiones.filter((g) => g.guion.trim().length >= 40).length})</button>
          </div>
        </section>
      ) : (
        <section className="rev-tarjeta">
          <p className="pequeno">Una idea por renglón. Si quieres, después de una barra «|» van las notas.<br />
            Ejemplo: <i>{tab === 'peligro' ? 'Las 6 serpientes más venenosas de Colombia | el villano es la cuatro narices'
              : 'Cosas raras que hace tu cuerpo cuando duermes | incluir el sobresalto al dormirse'}</i></p>
          <textarea rows={8} value={ideas} onChange={(ev) => setIdeas(ev.target.value)} style={{ width: '100%' }}
            placeholder={'Idea 1 | notas\nIdea 2\nIdea 3'} />
          {tab === 'peligro' ? <label className="pequeno">Minutos por video:{' '}
            <input type="number" min={4} max={25} value={minutos} style={{ width: 70 }}
              onChange={(ev) => setMinutos(Number(ev.target.value) || 9)} /></label>
            : <label className="pequeno">Temas por video:{' '}
            <input type="number" min={3} max={15} value={temas} style={{ width: 70 }}
              onChange={(ev) => setTemas(Number(ev.target.value) || 9)} /></label>}
          <p className="pequeno tenue">{tab === 'peligro'
            ? 'Cada video hace guion, imágenes y video sin parar a revisar. Respeta el máximo de gasto por video: si lo pasa, se detiene y te pregunta.'
            : 'Cada video hace guion, escenas (gratis, con Claude) y video. Solo se paga la voz.'}</p>
          <button className="boton" disabled={enviando || !ideas.trim()} onClick={agregarIdeas}>
            Agregar a la cola ({ideas.split('\n').filter((l) => l.trim()).length})</button>
        </section>
      )}

      <h2>En la cola {e && e.esperando > 0 && <span className="tenue pequeno">· {e.esperando} en espera</span>}</h2>
      {!e ? <p>Cargando…</p> : e.videos.length === 0 ? <p className="tenue">No hay videos en la cola.</p> : (
        <div style={{ display: 'grid', gap: 8 }}>
          {e.videos.map((x) => (
            <div key={x.id} className="rev-tarjeta" style={{ padding: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                <div>
                  <span className="pequeno tenue">{x.etiqueta || (x.tipo === 'tracy' ? 'Tracy' : x.tipo === 'peligro'
                    ? 'Peligro Tropical' : 'El Calvo Explica')} · </span>
                  <Link to={x.tipo === 'tracy' ? `/tracy/${x.slug}` : x.tipo === 'peligro' ? `/videos/${x.slug}` : '/explica'}>
                    <b>{x.titulo}</b></Link>
                </div>
                <span className={x.estado === 'error' ? 'error pequeno' : 'pequeno'}>{NOMBRE_ESTADO[x.estado]}</span>
              </div>
              {x.estado === 'haciendo' && (
                <>
                  <div className="barra-progreso"><i style={{ width: `${Math.round((x.progreso || 0) * 100)}%` }} /></div>
                  <div className="pequeno tenue">{x.mensaje}</div>
                </>
              )}
              {x.estado === 'error' && <div className="pequeno error">{x.error}</div>}
              <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                {x.estado === 'esperando' && <button className="boton-borde pequeno"
                  onClick={() => accion(`/api/cola/${x.id}/quitar`)}>Quitar</button>}
                {x.estado === 'error' && <>
                  <button className="boton-borde pequeno" onClick={() => accion(`/api/cola/${x.id}/reintentar`)}>Reintentar</button>
                  {/máximo|permiso|tope/i.test(x.error || '') && <button className="boton pequeno" onClick={() => {
                    if (window.confirm('¿Das permiso para que este video pase el máximo de gasto?'))
                      accion(`/api/cola/${x.id}/reintentar`, { permiso: true });
                  }}>Dar permiso y seguir</button>}
                  <button className="boton-borde pequeno" onClick={() => accion(`/api/cola/${x.id}/quitar`)}>Quitar</button>
                </>}
              </div>
            </div>
          ))}
          {e.videos.some((x) => x.estado === 'listo') &&
            <button className="boton-borde pequeno" onClick={() => accion('/api/cola/limpiar')}>Quitar los ya listos de la lista</button>}
        </div>
      )}
    </div>
  );
}
