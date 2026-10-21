import { useState } from 'react';
import { createPortal } from 'react-dom';
import { useLocation } from 'react-router-dom';
import { CircleHelp, X } from 'lucide-react';
import { api, ultimoError } from '../api';

// Ayuda corta de cada pantalla + «Reportar problema» (adjunta solo la pantalla, el último error y los trabajos que
// fallaron; nunca claves).
const AYUDA: [RegExp, string, string[]][] = [
  [/^\/$/, 'Home', ['Escribe la idea del video y dale «Crear video». El costo en créditos sale junto al botón antes de crear.',
    '«Automático»: Xandart hace todo y te avisa. «Paso a paso»: revisas el guion antes de las imágenes.',
    'Las plantillas de «Empieza rápido» eligen por ti la forma del video.']],
  [/^\/producir/, 'Producer', ['Aquí ves tu video haciéndose: cada escena se marca con ✓ cuando su imagen está lista.',
    'Arriba sale el porcentaje total y cuánto falta (es un cálculo aproximado).',
    'Puedes cerrar esta pantalla: el video sigue y te avisamos con la campana cuando termine.']],
  [/^\/videos\/[^/]+\/editor/, 'Editor', ['Toca una escena en la línea de tiempo para cambiar su imagen, su texto o su duración.',
    'Cada cambio se guarda solo. Cuando termines, dale «Exportar» para rearmar el video.']],
  [/^\/videos\/[^/]+\/miniatura/, 'Miniatura', ['La miniatura sale del guion del video. Elige la opción que más te guste o pide cambios con palabras.']],
  [/^\/videos\/[^/]+/, 'Revisar el video', ['Lee el guion: toca el texto de cualquier escena para cambiarlo.',
    'Puedes cambiar la duración: se reescribe el guion. El costo del video completo sale antes de producir.',
    'Si una escena no salió, dale «Reintentar esta escena».']],
  [/^\/videos/, 'Proyectos', ['Todos tus videos. Toca uno para seguir donde lo dejaste: nada se pierde.']],
  [/^\/canales/, 'Canales', ['Cada canal guarda su voz, su estilo y su personaje, para que todos sus videos se vean iguales.']],
  [/^\/personajes/, 'Personajes', ['Describe a tu personaje, elige la versión que más te guste y haz su hoja de referencia: así sale igual en todos los videos.']],
  [/^\/estilos/, 'Estilos', ['El estilo decide cómo se ven las imágenes. Duplica uno del catálogo para tener tu propia copia.']],
  [/^\/creditos/, 'Créditos', ['Cada fila dice en qué se usaron tus créditos. Si algo falla, los créditos vuelven solos y lo ves aquí.']],
  [/^\/planes/, 'Planes y créditos', ['Los créditos se gastan al crear videos, imágenes y miniaturas. Siempre ves el costo antes de cada botón.']],
];

export function Ayuda() {
  const { pathname } = useLocation();
  const [abierta, setAbierta] = useState(false);
  const [texto, setTexto] = useState('');
  const [estado, setEstado] = useState<'' | 'enviando' | 'hecho' | 'error'>('');
  const [titulo, puntos] = (AYUDA.find(([r]) => r.test(pathname)) ?? [null, 'Xandart', ['Escribe una idea en Home y Xandart hace el video.']]).slice(1) as [string, string[]];

  async function reportar() {
    setEstado('enviando');
    try {
      await api('/api/v2/reportes', { cuerpo: { texto, ruta: pathname, error: ultimoError.texto, navegador: navigator.userAgent } });
      setEstado('hecho'); setTexto('');
    } catch { setEstado('error'); }
  }

  return (
    <>
      <button className="boton-icono" onClick={() => { setAbierta(true); setEstado(''); }} aria-label="Ayuda"><CircleHelp size={19} /></button>
      {abierta && createPortal(
        <div className="cajon-fondo" onClick={() => setAbierta(false)}>
          <aside className="cajon" role="dialog" aria-label="Ayuda" onClick={(e) => e.stopPropagation()}>
            <div className="cajon-cab"><h3>Ayuda · {titulo}</h3>
              <button className="boton-icono" onClick={() => setAbierta(false)} aria-label="Cerrar"><X size={18} /></button></div>
            <ul className="ayuda-puntos">{puntos.map((p) => <li key={p}>{p}</li>)}</ul>
            <h3 style={{ marginTop: 22 }}>¿Algo no funciona?</h3>
            <p className="tenue pequeno">Cuéntanos qué pasó. Adjuntamos solo la pantalla donde estás y el último error, para revisarlo rápido.</p>
            <textarea className="campo-texto" rows={4} value={texto} onChange={(e) => setTexto(e.target.value)}
              placeholder="Ej.: le di «Crear video» y se quedó cargando" />
            <button className="boton-primario" disabled={texto.trim().length < 3 || estado === 'enviando'} onClick={reportar}>
              {estado === 'enviando' ? 'Enviando…' : 'Reportar problema'}</button>
            {estado === 'hecho' && <p className="ok-texto">Gracias, quedó enviado. Lo revisamos.</p>}
            {estado === 'error' && <p className="error">No se pudo enviar. Revisa que Xandart siga abierto e inténtalo otra vez.</p>}
          </aside>
        </div>, document.body,
      )}
    </>
  );
}
