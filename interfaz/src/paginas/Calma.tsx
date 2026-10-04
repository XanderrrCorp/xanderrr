import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';

// Hazlo con Calma: video de prueba animado por código (personaje en piezas, movimientos con rebote).
// Pegas el código de la voz del canal, eliges (o no) la música y Xandart hace voz, tiempos con Whisper y render.

interface Musica { ruta: string; nombre: string; animo: string }
interface Informe {
  render: { cuadros: number; segundos_cuadros: number; segundos_total: number };
  duracion: number; escenas: number; avisos_ritmo: string[]; confianza_whisper: number; video: string;
  musica: { nombre_original: string; golpes_s?: number; melodia?: number; de?: number; elegida?: string } | null;
  costo_voz_usd: number;
}
interface EstadoCalma {
  ajustes: { voz_id: string | null; velocidad: number; musica: string | null; volumen_musica_db: number; segundos: number };
  costo_voz: { caracteres: number; usd: number; cop: string };
  musicas: Musica[];
  informe: Informe | null;
  trabajo: { paso: string; progreso: number; mensaje: string; activo: boolean; error: string | null; registro: string[] } | null;
  video: boolean;
}

const PASOS: Record<string, string> = {
  calma: 'Empezando', voz: 'Grabando la voz', whisper: 'Sacando el tiempo de cada palabra',
  escenas: 'Atando cada pieza a su palabra', render: 'Dibujando los cuadros',
};

export function Calma() {
  const [est, setEst] = useState<EstadoCalma | null>(null);
  const [voz, setVoz] = useState('');
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const cargar = useCallback(async () => {
    try {
      const e = await api<EstadoCalma>('/api/calma');
      setEst(e);
      setVoz((v) => v || e.ajustes.voz_id || '');
      if (e.video) setVersion(Date.now());
    } catch (e) { setError((e as Error).message); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => {
    if (!est?.trabajo?.activo) return;
    const id = setInterval(cargar, 1500);
    return () => clearInterval(id);
  }, [est?.trabajo?.activo, cargar]);

  const ajustar = async (cuerpo: Record<string, string | number>) => {
    setError('');
    try { setEst(await api<EstadoCalma>('/api/calma/ajustes', { cuerpo })); } catch (e) { setError((e as Error).message); }
  };
  const hacer = async () => {
    setError('');
    try { setEst(await api<EstadoCalma>('/api/calma/prueba', { cuerpo: { permiso: false } })); }
    catch (e) { setError((e as Error).message); }
  };

  if (!est) return <div className="pagina"><h1>Hazlo con Calma</h1>{error && <p className="error">{error}</p>}</div>;
  const t = est.trabajo;
  const inf = est.informe;
  return (
    <div className="pagina tracy">
      <h1>Hazlo con Calma · prueba animada</h1>
      <p className="tenue">Video de 60 segundos sobre la garrapata, hecho 100 % con código: tu personaje por piezas, cada
        cosa entra cuando la voz dice su palabra, solo cortes secos y música de fondo bajita.</p>

      <section className="rev-tarjeta">
        <h2>Voz del canal</h2>
        <label className="campo">Código de la voz de Hazlo con Calma en MiniMax (el «voice id» de la voz que usas en
          los videos publicados)
          <input value={voz} onChange={(e) => setVoz(e.target.value)} placeholder="moss_audio_…"
            onBlur={() => voz.trim() !== (est.ajustes.voz_id || '') && ajustar({ voz_id: voz.trim() })} />
        </label>
        <label className="campo">Velocidad de la voz: {est.ajustes.velocidad.toFixed(2)}
          <input type="range" min={0.8} max={1.4} step={0.05} defaultValue={est.ajustes.velocidad}
            onMouseUp={(e) => ajustar({ velocidad: +(e.target as HTMLInputElement).value })}
            onTouchEnd={(e) => ajustar({ velocidad: +(e.target as HTMLInputElement).value })}
            onKeyUp={(e) => ajustar({ velocidad: +(e.target as HTMLInputElement).value })} />
        </label>
      </section>

      <section className="rev-tarjeta">
        <h2>Música de fondo</h2>
        <label className="campo">Pista
          <select value={est.ajustes.musica || ''} onChange={(e) => ajustar({ musica: e.target.value })}>
            <option value="">Que Xandart la elija (tensión, ritmo bajo, sin melodía que mande)</option>
            {est.musicas.map((m) => <option key={m.ruta} value={m.ruta}>{m.nombre} · {m.animo}</option>)}
          </select>
        </label>
        {est.musicas.length === 0 && <p className="tenue pequeno">Tu biblioteca no tiene música con licencia: el video
          saldría solo con la voz. Agrégala en Sonidos.</p>}
        <label className="campo">Volumen de la música: {Math.round(est.ajustes.volumen_musica_db)} dB (más negativo =
          más bajita)
          <input type="range" min={-36} max={-16} step={1} defaultValue={est.ajustes.volumen_musica_db}
            onMouseUp={(e) => ajustar({ volumen_musica_db: +(e.target as HTMLInputElement).value })}
            onTouchEnd={(e) => ajustar({ volumen_musica_db: +(e.target as HTMLInputElement).value })}
            onKeyUp={(e) => ajustar({ volumen_musica_db: +(e.target as HTMLInputElement).value })} />
        </label>
      </section>

      <section className="rev-tarjeta">
        <h2>Hacer el video de prueba</h2>
        <p>La voz cuesta unos <b>{est.costo_voz.cop}</b> ({est.costo_voz.caracteres} caracteres en MiniMax). Si ya se
          grabó antes con la misma voz y velocidad, no se vuelve a pagar.</p>
        <button className="boton" disabled={!!t?.activo || !est.ajustes.voz_id} onClick={hacer}>
          {t?.activo ? 'Trabajando…' : est.video ? 'Volver a hacerlo' : 'Hacer el video de prueba'}
        </button>
        {!est.ajustes.voz_id && <p className="tenue pequeno">Primero pega el código de la voz.</p>}
        {t && (
          <div>
            <div className="barra-progreso"><i style={{ width: `${Math.round(t.progreso * 100)}%` }} /></div>
            <div className="pequeno">{t.error ? <span className="error">Error: {t.error}</span>
              : `${PASOS[t.paso] || t.paso} · ${t.mensaje}`}</div>
          </div>
        )}
        {error && <p className="error">{error}</p>}
      </section>

      {est.video && (
        <section className="rev-tarjeta">
          <h2>Resultado</h2>
          <video src={`/api/calma/video?v=${version}`} controls style={{ width: '100%', borderRadius: 8 }} />
          {inf && (
            <ul className="pequeno">
              <li>Render: {Math.round(inf.duracion)} s de video en {Math.round(inf.render.segundos_total)} s
                ({inf.render.cuadros} cuadros)</li>
              <li>{inf.escenas} escenas · Whisper coincidió en el {Math.round(inf.confianza_whisper * 100)} % de las
                palabras</li>
              <li>Música: {inf.musica ? inf.musica.nombre_original : 'sin música'}</li>
              {inf.avisos_ritmo.length > 0 && <li>Avisos de ritmo: {inf.avisos_ritmo.join(' · ')}</li>}
              <li className="tenue">Guardado en: {inf.video}</li>
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
