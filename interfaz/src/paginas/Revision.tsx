import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, archivo, paginaVieja, type Escena, type VideoDetalle } from '../api';
import { Icono } from '../componentes/Icono';

// Revisión de un video en proceso: guion → imágenes → video. Mismas acciones que la página de
// siempre, con el diseño nuevo. Nada gasta sin decir cuánto antes, y pasar el máximo pide permiso.

const NOMBRE_PASO: Record<string, string> = {
  guion: 'Escribiendo el guion', imagenes: 'Haciendo las imágenes', video: 'Haciendo el video',
  regenerar: 'Regenerando una imagen', prueba: 'Probando las primeras 10 escenas', short: 'Haciendo el short vertical',
  ajustar: 'Buscando en Pexels y ajustando al presupuesto', animar: 'Animando una escena', voz: 'Grabando la voz',
};
const CON_PERMISO = ['imagenes', 'prueba', 'video', 'short'];

export function Revision() {
  const { slug = '' } = useParams();
  const ir = useNavigate();
  const [v, setV] = useState<VideoDetalle | null>(null);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');
  const [fps, setFps] = useState(() => { try { return +(localStorage.getItem('xandart_fps') || 60); } catch { return 60; } });

  const cargar = useCallback(async () => {
    try { setV(await api<VideoDetalle>(`/api/videos/${slug}`)); setError(''); }
    catch (e) { setError((e as Error).message); }
  }, [slug]);
  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => {                                     // mientras trabaja, se actualiza solo
    if (!v?.trabajo?.activo) return;
    const id = window.setTimeout(cargar, 2000);
    return () => window.clearTimeout(id);
  }, [v, cargar]);

  const accion = async (que: string, cuerpo: Record<string, unknown> = {}) => {
    setAviso('');
    try { setV(await api<VideoDetalle>(`/api/videos/${slug}/${que}`, { cuerpo })); }
    catch (e) {
      const m = (e as Error).message;
      if (/máximo|FRENO|tope/.test(m) && CON_PERMISO.includes(que.split('/')[0])
          && window.confirm(`${m}\n\n¿Das permiso para pasar el máximo en este video?`)) return accion(que, { ...cuerpo, permiso: true });
      setAviso(m);
    }
  };

  if (error && !v) return <div className="pagina"><p className="error">{error}</p><Link to="/videos">← Mis videos</Link></div>;
  if (!v) return <div className="pagina"><p className="tenue">Cargando…</p></div>;

  const t = v.trabajo;
  const trabajando = !!t?.activo;
  const guionOk = v.pasos.guionista === 'completo';
  const imgOk = v.pasos.assets === 'completo';
  const vidOk = !!v.video;
  const e = v.estimacion_imagenes;

  const aprobar = () => {
    if (!e) return;
    if (!e.pasa_maximo) return accion('imagenes');
    if (window.confirm(`Este video ya lleva ${e.gastado_texto} gastados. Las ${e.faltan} imágenes que faltan cuestan ≈ ${e.texto} `
      + `y el video quedaría en ≈ ${e.total_texto}, por encima del máximo de ${e.maximo_texto}.\n\n`
      + '¿Das permiso para pasar el máximo en este video?\n(Si no, cancela y usa «Usar Pexels y ajustar», que es gratis.)')) {
      return accion('imagenes', { permiso: true });
    }
  };
  const seguirConPermiso = (paso: string) => {
    if (!window.confirm(`Este video ya lleva ${v.costo} gastados.\n\n¿Das permiso para pasar el máximo en este video?`)) return;
    accion(paso, paso === 'video' ? { permiso: true, fps } : { permiso: true });
  };
  const elegirFps = (x: number) => { setFps(x); try { localStorage.setItem('xandart_fps', String(x)); } catch { /* sin almacenamiento */ } };

  const pasos = [
    { n: 1, nombre: 'Guion', hecho: guionOk, actual: !guionOk },
    { n: 2, nombre: 'Imágenes', hecho: imgOk, actual: guionOk && !imgOk },
    { n: 3, nombre: 'Video', hecho: vidOk, actual: imgOk && !vidOk },
  ];

  return (
    <div className="pagina revision">
      <div className="rev-cab">
        <Link to="/videos" className="tenue pequeno">← Mis videos</Link>
        <span className="crece" />
        {guionOk && !v.vertical && <a className="boton-borde pequeno" href={`/#mini/${slug}`}>Miniatura</a>}
        <span className="chip-gasto">Gastado: {v.costo}</span>
      </div>
      <h1 className="rev-titulo">{v.titulo}</h1>
      <ol className="rev-pasos">
        {pasos.map((p) => (
          <li key={p.n} className={`${p.hecho ? 'hecho' : ''} ${p.actual ? 'actual' : ''}`}>
            <i>{p.hecho ? <Icono nombre="ok" tam={14} /> : p.n}</i><span>{p.nombre}</span>
          </li>
        ))}
      </ol>

      {trabajando && t && (
        <section className="rev-tarjeta">
          <b>{NOMBRE_PASO[t.paso] ?? t.paso}</b>
          <div className="barra-progreso"><i style={{ width: `${Math.round(t.progreso * 100)}%` }} /></div>
          <span className="tenue pequeno">{t.mensaje} · {Math.floor(t.segundos / 60)} min {t.segundos % 60} s</span>
        </section>
      )}
      {!trabajando && t?.error && (
        <div className="rev-error">
          No se pudo terminar «{NOMBRE_PASO[t.paso] ?? t.paso}»: {t.error}
          {/máximo|FRENO|tope/.test(t.error) && CON_PERMISO.includes(t.paso) && (
            <div><button className="boton-borde pequeno" onClick={() => seguirConPermiso(t.paso)}>Dar permiso y seguir</button></div>
          )}
        </div>
      )}
      {aviso && <div className="rev-error">{aviso}</div>}

      {vidOk && !trabajando && (
        <section className="rev-tarjeta">
          <h2>Tu video está listo</h2>
          <video className="rev-video" controls preload="metadata" src={archivo(slug, v.video!)} />
          <div className="fila-botones">
            <button className="boton-primario" onClick={() => ir(`/videos/${slug}/editor`)}>Abrir en el editor</button>
            <a className="boton-borde" href={`${archivo(slug, v.video!)}?descargar=true`}>Descargar MP4</a>
            <a className="boton-borde" href={`${archivo(slug, 'render/final.srt')}?descargar=true`}>Subtítulos (SRT)</a>
            {v.puede_short && <button className="boton-borde" onClick={() => {
              if (window.confirm('Claude escribe un short vertical de unos 40 s con el nivel del villano, usando las mismas imágenes (solo se paga la voz, unos pocos pesos). ¿Lo hago?')) accion('short');
            }}>Sacar un short vertical</button>}
          </div>
          {v.divulgacion && <p className="rev-aviso">Este video tiene al presentador hecho con IA. Al subirlo a YouTube, en «Detalles», marca <b>«Contenido alterado o sintético: Sí»</b>. No afecta la monetización.</p>}
        </section>
      )}

      {guionOk && !trabajando && !imgOk && e && (
        <section className="rev-tarjeta">
          <h2>Revisa el guion</h2>
          <p className="tenue">Toca el texto de cualquier escena para cambiarlo. Cuando te guste, aprueba y se hacen las imágenes.</p>
          {e.pasa_maximo && <p className="rev-aviso">Ojo: este video ya lleva {e.gastado_texto} gastados. Las {e.faltan} imágenes que faltan (≈ {e.texto}) lo llevarían a ≈ {e.total_texto}, por encima del máximo de {e.maximo_texto}. Para no pasarte usa «Usar Pexels y ajustar»; si igual quieres todas, Xandart te pide permiso antes de gastar.</p>}
          {v.prueba && <PruebaHecha v={v} />}
          <div className="fila-botones">
            <button className={e.pasa_maximo ? 'boton-primario' : 'boton-borde'} onClick={() => {
              if (window.confirm('Xandart busca fotos y videos reales en Pexels (gratis) para las escenas que solo muestran al animal, y si aún pasa el máximo, algunas escenas reusan una imagen cercana. El texto del guion no cambia. ¿Seguir?')) accion('ajustar-imagenes');
            }}>Usar Pexels y ajustar al presupuesto (gratis)</button>
            <button className={e.pasa_maximo ? 'boton-borde' : 'boton-primario'} onClick={aprobar}>Aprobar y hacer las imágenes ({e.faltan} ≈ {e.texto})</button>
            {e.prueba > 0 && <button className="boton-borde" onClick={() => accion('prueba')}>Probar 10 escenas ({e.prueba} ≈ {e.prueba_texto})</button>}
            <button className="boton-icono pequeno" onClick={() => { if (window.confirm('¿Escribir otro guion desde cero?')) accion('guion'); }}>Escribir otro guion</button>
          </div>
        </section>
      )}

      {imgOk && !trabajando && !vidOk && e && (
        <section className="rev-tarjeta">
          <h2>Revisa las imágenes</h2>
          <p className="tenue">Si alguna no te gusta, dale «Regenerar». Cuando todo esté bien, haz el video.</p>
          <div className="fila-botones">
            <div className="alternar" role="group" aria-label="Fluidez">
              <button className={fps === 60 ? 'sel' : ''} onClick={() => elegirFps(60)}>60 cps</button>
              <button className={fps === 30 ? 'sel' : ''} onClick={() => elegirFps(30)}>30 cps (rápido)</button>
            </div>
            <button className="boton-primario" onClick={() => accion('video', { fps })}><Icono nombre="videos" tam={18} /> Hacer el video</button>
            {e.faltan > 0 && <button className="boton-borde" onClick={aprobar}>Completar imágenes que faltan ({e.faltan})</button>}
          </div>
        </section>
      )}

      {!guionOk && !trabajando && !t?.error && (
        <section className="rev-tarjeta"><p className="tenue">El guion todavía no está. <button className="boton-borde pequeno" onClick={() => accion('guion')}>Escribir el guion</button></p></section>
      )}

      {guionOk && <Escenas v={v} conImagenes={imgOk} bloqueado={trabajando} slug={slug} alRegenerar={(id, inst) => accion(`escenas/${id}/regenerar`, { instruccion: inst })} />}
      <p className="tenue pequeno" style={{ marginTop: 24 }}>¿Algo no está aquí? <a href={paginaVieja(slug)}>Ábrelo en la página de siempre</a>.</p>
    </div>
  );
}

function PruebaHecha({ v }: { v: VideoDetalle }) {
  const p = v.prueba!;
  return (
    <div className="rev-prueba">
      <b>Prueba real: primeras {p.escenas} escenas</b>
      {p.hoja && <a href={archivo(v.slug, p.hoja)} target="_blank" rel="noreferrer"><img src={`${archivo(v.slug, p.hoja)}?v=${Date.now() % 100000}`} alt="Hoja de contacto" /></a>}
      <div>Costo real de la prueba: <b>{p.costo_corrida}</b>{p.costo_medio_imagen && <> · por imagen: <b>{p.costo_medio_imagen}</b></>}</div>
      {p.proyeccion && <div>Todas las imágenes del video ({p.proyeccion.imagenes}): <b>≈ {p.proyeccion.texto}</b></div>}
    </div>
  );
}

function Escenas({ v, conImagenes, bloqueado, slug, alRegenerar }: {
  v: VideoDetalle; conImagenes: boolean; bloqueado: boolean; slug: string; alRegenerar: (id: number, instruccion: string) => void;
}) {
  const grupos: { seccion: string; escenas: Escena[] }[] = [];
  for (const e of v.escenas) {
    if (!grupos.length || grupos[grupos.length - 1].seccion !== e.seccion) grupos.push({ seccion: e.seccion, escenas: [] });
    grupos[grupos.length - 1].escenas.push(e);
  }
  const guardarTexto = async (e: Escena, texto: string) => {
    texto = texto.trim();
    if (!texto || texto === e.narracion) return;
    await api(`/api/videos/${slug}/escenas/${e.id}`, { metodo: 'PUT', cuerpo: { narracion: texto } }).catch(() => {});
    e.narracion = texto;
  };
  const version = Date.now() % 100000;
  return (
    <div className="rev-escenas">
      {grupos.map((g, k) => (
        <section key={k}>
          <h3 className="rev-seccion">{g.seccion}</h3>
          <div className="rev-rejilla">
            {g.escenas.map((e) => (
              <article key={e.id} className="rev-escena">
                <div className="rev-img">
                  {e.imagen ? <img loading="lazy" src={`${archivo(slug, e.imagen)}?v=${version}`} alt="" />
                    : <span>{e.accion === 'generar' ? (conImagenes ? 'sin imagen' : 'imagen pendiente') : e.accion === 'componer' ? 'tira de niveles' : 'reutiliza otra imagen'}</span>}
                  <em className="rev-num">{e.id}</em>
                </div>
                <div className="rev-texto" contentEditable={!conImagenes && !bloqueado} suppressContentEditableWarning
                  onBlur={(ev) => guardarTexto(e, ev.currentTarget.innerText)}>{e.narracion}</div>
                {e.medico && <span className="rev-medico">revisar dato de salud</span>}
                {conImagenes && e.puede_regenerar && !bloqueado && (
                  <button className="boton-icono pequeno" onClick={() => {
                    const inst = window.prompt('¿Qué quieres cambiar? (vacío = otra versión igual)', '');
                    if (inst !== null) alRegenerar(e.id, inst);
                  }}>Regenerar</button>
                )}
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
