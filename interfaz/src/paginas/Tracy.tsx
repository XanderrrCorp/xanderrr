import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, archivo, type VideoDetalle } from '../api';

// Canal Tracy: pegas el guion y Xandart hace todo (voz, tiempos con Whisper, clips de Pexels y del
// seminario, subtítulos y música de fondo). Sin terminal.

interface EstadoTracy {
  canal: string; clip_base: string; clip_existe: boolean; musica: string; musica_existe: boolean;
  presentador: string; presentador_existe: boolean; escena_final_desde: number;
  proporcion_seminario: number; voz_id: string | null; whisper: boolean;
  velocidad: number; volumen_musica_db: number; seminario_s: number; barras_cine: boolean;
}

type Que = 'seminario' | 'musica' | 'presentador';

const PASOS: Record<string, string> = {
  tracy: 'Empezando', voz: 'Grabando la voz y sacando los tiempos', visual: 'Eligiendo clips y armando el video',
  entrega: 'Guardando el video',
};

async function subir(que: Que, f: File): Promise<EstadoTracy> {
  const datos = new FormData();
  datos.append('que', que);
  datos.append('archivo', f);
  const r = await fetch('/api/tracy/archivo', { method: 'POST', body: datos });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error((j as { detail?: string }).detail || `Error ${r.status}`);
  return j as EstadoTracy;
}

function Archivo({ titulo, ruta, existe, que, ayuda, alCambiar }: {
  titulo: string; ruta: string; existe: boolean; que: Que; ayuda: string;
  alCambiar: (e: EstadoTracy) => void;
}) {
  const entrada = useRef<HTMLInputElement>(null);
  const [subiendo, setSubiendo] = useState(false);
  const [msg, setMsg] = useState('');
  return (
    <div className="tr-archivo">
      <div>
        <b>{titulo}</b> <span className={existe ? 'tr-ok' : 'tr-falta'}>{existe ? 'listo' : 'no lo encuentro'}</span>
        <div className="tenue pequeno tr-ruta" title={ruta}>{ruta || '—'}</div>
        {!existe && <div className="tenue pequeno">{ayuda}</div>}
        {msg && <div className="error pequeno">{msg}</div>}
      </div>
      <input ref={entrada} type="file" hidden accept={que === 'seminario' ? 'video/*' : que === 'musica' ? 'audio/*' : 'image/*'}
        onChange={async (ev) => {
          const f = ev.target.files?.[0];
          if (!f) return;
          setSubiendo(true); setMsg('');
          try { alCambiar(await subir(que, f)); } catch (e) { setMsg((e as Error).message); }
          finally { setSubiendo(false); ev.target.value = ''; }
        }} />
      <button className="boton-borde pequeno" disabled={subiendo} onClick={() => entrada.current?.click()}>
        {subiendo ? 'Copiando…' : existe ? 'Cambiar' : 'Elegir archivo'}
      </button>
    </div>
  );
}

export function Tracy() {
  const ir = useNavigate();
  const [est, setEst] = useState<EstadoTracy | null>(null);
  const [guion, setGuion] = useState('');
  const [titulo, setTitulo] = useState('');
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);
  useEffect(() => { api<EstadoTracy>('/api/tracy').then(setEst).catch((e) => setError((e as Error).message)); }, []);

  const caracteres = guion.trim().length;
  const minutos = caracteres / 13.5 / 60;          // ~13,5 caracteres por segundo de voz
  const crear = async () => {
    setError(''); setEnviando(true);
    try {
      const v = await api<VideoDetalle>('/api/tracy/videos', { cuerpo: { guion, titulo } });
      ir(`/tracy/${v.slug}`);
    } catch (e) { setError((e as Error).message); } finally { setEnviando(false); }
  };
  const ajustar = async (cuerpo: Record<string, number | boolean>) => {
    try { setEst(await api<EstadoTracy>('/api/tracy/ajustes', { cuerpo })); }
    catch (e) { setError((e as Error).message); }
  };

  return (
    <div className="pagina tracy">
      <h1>Canal Tracy</h1>
      <p className="tenue">Pega el guion y Xandart hace el resto: voz, clips de Pexels, tramos del seminario en blanco y
        negro, subtítulos amarillos, música de fondo suave y la escena final. Cada clip dura 30 segundos o menos.</p>

      {est && (
        <section className="rev-tarjeta">
          <h2>Archivos del canal</h2>
          <Archivo titulo="Video del seminario" que="seminario" ruta={est.clip_base} existe={est.clip_existe}
            ayuda="Déjalo en esa carpeta con ese nombre, o elígelo aquí." alCambiar={setEst} />
          <Archivo titulo="Música de fondo" que="musica" ruta={est.musica} existe={est.musica_existe}
            ayuda="Opcional: sin música, el video sale solo con la voz." alCambiar={setEst} />
          <Archivo titulo="Presentador de la escena final" que="presentador" ruta={est.presentador}
            existe={est.presentador_existe} ayuda="Una imagen (mejor PNG sin fondo). Va a la izquierda, en blanco y negro."
            alCambiar={setEst} />
          <label className="campo">Cada corte del seminario dura {Math.round(est.seminario_s)} s; después van 1, 2 o los
            clips de stock que hagan falta, y así se intercala hasta la escena final
            <input type="range" min={3} max={12} step={1} defaultValue={est.seminario_s}
              onMouseUp={(e) => ajustar({ seminario_s: +(e.target as HTMLInputElement).value })}
              onTouchEnd={(e) => ajustar({ seminario_s: +(e.target as HTMLInputElement).value })}
              onKeyUp={(e) => ajustar({ seminario_s: +(e.target as HTMLInputElement).value })} />
          </label>
          <label className="campo tr-check">
            <span><input type="checkbox" checked={est.barras_cine}
              onChange={(e) => ajustar({ barras_cine: e.target.checked })} /> Barras negras de cine arriba y abajo</span>
          </label>
          <label className="campo">
            {est.escena_final_desde >= 1 ? 'Sin escena final (clips hasta el final)'
              : `La escena final empieza en el ${Math.round(est.escena_final_desde * 100)} % del video`}
            <input type="range" min={0.1} max={1} step={0.05} defaultValue={est.escena_final_desde}
              onMouseUp={(e) => ajustar({ escena_final_desde: +(e.target as HTMLInputElement).value })}
              onTouchEnd={(e) => ajustar({ escena_final_desde: +(e.target as HTMLInputElement).value })}
              onKeyUp={(e) => ajustar({ escena_final_desde: +(e.target as HTMLInputElement).value })} />
            <span className="tenue pequeno">Fondo de naturaleza en blanco y negro con partículas, el presentador a un
              lado, el botón Suscríbete y las ondas de la voz.</span>
          </label>
          <label className="campo">Velocidad de la voz: {est.velocidad.toFixed(2).replace('.', ',')}× (1 = normal)
            <input type="range" min={0.8} max={1.3} step={0.05} defaultValue={est.velocidad}
              onMouseUp={(e) => ajustar({ velocidad: +(e.target as HTMLInputElement).value })}
              onTouchEnd={(e) => ajustar({ velocidad: +(e.target as HTMLInputElement).value })}
              onKeyUp={(e) => ajustar({ velocidad: +(e.target as HTMLInputElement).value })} />
          </label>
          <label className="campo">Volumen de la música: {Math.round((est.volumen_musica_db + 30) / 24 * 100)} %
            <input type="range" min={-30} max={-6} step={1} defaultValue={est.volumen_musica_db}
              onMouseUp={(e) => ajustar({ volumen_musica_db: +(e.target as HTMLInputElement).value })}
              onTouchEnd={(e) => ajustar({ volumen_musica_db: +(e.target as HTMLInputElement).value })}
              onKeyUp={(e) => ajustar({ volumen_musica_db: +(e.target as HTMLInputElement).value })} />
            <span className="tenue pequeno">Siempre por debajo de la voz; baja un poco sola cuando hablas.</span>
          </label>
          {!est.whisper && <p className="rev-aviso">Falta Whisper (los tiempos de la voz). Vuelve a correr «Instalar Xandart
            Nueva» y queda listo.</p>}
        </section>
      )}

      <section className="rev-tarjeta">
        <h2>Nuevo video</h2>
        <label className="campo">Título (opcional; si no, la primera frase)
          <input value={titulo} onChange={(e) => setTitulo(e.target.value)} maxLength={120} />
        </label>
        <textarea className="tr-guion" value={guion} onChange={(e) => setGuion(e.target.value)}
          placeholder="Pega aquí el guion completo…" />
        <div className="fila-botones">
          <span className="tenue pequeno">{caracteres.toLocaleString('es-CO')} caracteres · ≈ {minutos.toFixed(1)} min de voz</span>
          <span className="crece" />
          <button className="boton-primario" disabled={enviando || caracteres < 40 || !est?.clip_existe || !est?.whisper}
            onClick={crear}>{enviando ? 'Empezando…' : 'Hacer el video'}</button>
        </div>
        {est && !est.clip_existe && <p className="tenue pequeno">Primero elige el video del seminario.</p>}
        {error && <div className="rev-error">{error}</div>}
      </section>
    </div>
  );
}

export function TracyVideo() {
  const { slug = '' } = useParams();
  const [v, setV] = useState<VideoDetalle | null>(null);
  const [error, setError] = useState('');
  const cargar = useCallback(async () => {
    try { setV(await api<VideoDetalle>(`/api/videos/${slug}`)); setError(''); }
    catch (e) { setError((e as Error).message); }
  }, [slug]);
  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => {
    if (!v?.trabajo?.activo) return;
    const id = window.setTimeout(cargar, 2000);
    return () => window.clearTimeout(id);
  }, [v, cargar]);
  const seguir = async (permiso = false) => {
    setError('');
    try { setV(await api<VideoDetalle>(`/api/tracy/videos/${slug}/seguir`, { cuerpo: { permiso } })); }
    catch (e) { setError((e as Error).message); }
  };

  if (error && !v) return <div className="pagina"><p className="error">{error}</p><Link to="/tracy">← Canal Tracy</Link></div>;
  if (!v) return <div className="pagina"><p className="tenue">Cargando…</p></div>;
  const t = v.trabajo;
  const trabajando = !!t?.activo;
  return (
    <div className="pagina revision">
      <div className="rev-cab">
        <Link to="/tracy" className="tenue pequeno">← Canal Tracy</Link>
        <span className="crece" />
        <span className="chip-gasto">Gastado: {v.costo}</span>
      </div>
      <h1 className="rev-titulo">{v.titulo}</h1>
      {trabajando && t && (
        <section className="rev-tarjeta">
          <b>{PASOS[t.paso] ?? t.paso}</b>
          <div className="barra-progreso"><i style={{ width: `${Math.round(t.progreso * 100)}%` }} /></div>
          <span className="tenue pequeno">{t.mensaje} · {Math.floor(t.segundos / 60)} min {t.segundos % 60} s</span>
          {t.paso === 'voz' && <p className="tenue pequeno">La primera vez Whisper baja su modelo (unos 480 MB): ese paso tarda un rato más.</p>}
        </section>
      )}
      {!trabajando && t?.error && (
        <div className="rev-error">
          No se pudo terminar: {t.error}
          <div className="fila-botones">
            <button className="boton-borde pequeno" onClick={() => seguir(false)}>Seguir donde iba</button>
            {/máximo|FRENO|tope/.test(t.error) && (
              <button className="boton-borde pequeno" onClick={() => {
                if (window.confirm(`Este video ya lleva ${v.costo}.\n\n¿Das permiso para pasar el máximo?`)) seguir(true);
              }}>Dar permiso y seguir</button>
            )}
          </div>
          <div className="tenue pequeno">Lo que ya se hizo (voz, clips bajados) no se vuelve a pagar.</div>
        </div>
      )}
      {!trabajando && !t && !v.video && (
        <div className="rev-tarjeta">
          <p>Este video quedó a medias.</p>
          <button className="boton-primario" onClick={() => seguir(false)}>Seguir donde iba</button>
        </div>
      )}
      {v.video && !trabajando && (
        <section className="rev-tarjeta">
          <h2>Tu video está listo</h2>
          <video className="rev-video" controls preload="metadata" src={archivo(slug, v.video)} />
          <div className="fila-botones">
            <a className="boton-primario" href={`${archivo(slug, v.video)}?descargar=true`}>Descargar MP4</a>
            <a className="boton-borde" href={`${archivo(slug, 'render/final.srt')}?descargar=true`}>Subtítulos (SRT)</a>
          </div>
          <p className="tenue pequeno">También quedó una copia en tu carpeta de Videos → Xandart.</p>
          <div className="fila-botones">
            <button className="boton-borde pequeno" onClick={() => {
              if (window.confirm('Se vuelve a armar con los ajustes de ahora (velocidad de la voz, música, escena final).\n\n'
                + 'Si cambiaste la velocidad de la voz, la voz se graba otra vez y se paga (unos pocos cientos de pesos). '
                + 'Los clips ya bajados no se vuelven a bajar.\n\n¿Seguir?')) seguir(false);
            }}>Volver a armar con los ajustes de ahora</button>
          </div>
        </section>
      )}
    </div>
  );
}
