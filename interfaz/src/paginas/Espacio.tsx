import { useEffect, useState } from 'react';
import { api } from '../api';

// Liberar espacio: cuánto ocupa Xandart y un botón que borra solo lo que Xandart puede volver a hacer
// (pedazos de render de videos terminados y clips de Pexels que ningún video pendiente usa).

interface Parte { nombre: string; carpeta: string; texto: string }
interface Inventario {
  partes: Parte[]; se_puede_liberar: number; se_puede_liberar_texto: string; archivos: number; hay_trabajo: boolean;
  liberado_texto?: string; copias_viejas: number; copias_viejas_texto: string;
  videos_viejos: number; videos_viejos_texto: string; videos_viejos_lista: string[];
}

export function Espacio() {
  const [inv, setInv] = useState<Inventario | null>(null);
  const [error, setError] = useState('');
  const [borrando, setBorrando] = useState(false);
  const [hecho, setHecho] = useState('');
  useEffect(() => { api<Inventario>('/api/espacio').then(setInv).catch((e) => setError((e as Error).message)); }, []);

  const conPermiso = async (ruta: string, pregunta: string) => {
    if (!confirm(pregunta)) return;
    setError(''); setBorrando(true);
    try {
      const r = await api<Inventario>(ruta, { cuerpo: {} });
      setInv(r); setHecho(`Listo: se liberaron ${r.liberado_texto}.`);
    } catch (e) { setError((e as Error).message); } finally { setBorrando(false); }
  };

  const liberar = async () => {
    if (!inv || !confirm(`Se borrarán ${inv.archivos} archivos temporales y se liberan ${inv.se_puede_liberar_texto}. ¿Seguir?`)) return;
    setError(''); setBorrando(true);
    try {
      const r = await api<Inventario>('/api/espacio/liberar', { cuerpo: {} });
      setInv(r); setHecho(`Listo: se liberaron ${r.liberado_texto}.`);
    } catch (e) { setError((e as Error).message); } finally { setBorrando(false); }
  };

  return (
    <div className="pagina tracy">
      <h1>Liberar espacio</h1>
      <p className="tenue">Borra solo lo que Xandart puede volver a hacer solo: los pedazos que quedan al armar los
        videos ya terminados y los clips de Pexels que ningún video pendiente usa. Nunca toca tus videos, imágenes,
        voces, música ni proyectos.</p>
      {!inv ? <p>{error || 'Midiendo…'}</p> : (
        <>
          <section className="rev-tarjeta">
            <h2>Cuánto ocupa Xandart</h2>
            <ul>
              {inv.partes.map((p) => (
                <li key={p.nombre}><b>{p.texto}</b> · {p.nombre}
                  <div className="tenue pequeno tr-ruta" title={p.carpeta}>{p.carpeta}</div></li>
              ))}
            </ul>
            <p className="tenue pequeno">Las copias de seguridad y los videos terminados no se borran desde aquí: si ya
              no los necesitas, bórralos tú y vacía la Papelera.</p>
          </section>
          <section className="rev-tarjeta">
            <h2>Se puede liberar: {inv.se_puede_liberar_texto}</h2>
            {inv.hay_trabajo && <p className="error pequeno">Hay un video haciéndose: espera a que termine.</p>}
            <button className="boton" disabled={borrando || inv.hay_trabajo || inv.archivos === 0} onClick={liberar}>
              {borrando ? 'Borrando…' : inv.archivos === 0 ? 'No hay nada que liberar' : `Liberar ${inv.se_puede_liberar_texto}`}
            </button>
            <p className="tenue pequeno">Es seguro: borra pedazos que sobran y deja una sola vez los videos que estaban
              guardados dos veces. Desde ahora, la cola lo hace sola al terminar cada video.</p>
          </section>
          <section className="rev-tarjeta">
            <h2>Copias de seguridad viejas: {inv.copias_viejas_texto}</h2>
            <p className="pequeno">Cada copia guarda TODOS tus proyectos. Se deja la más reciente y se borran las
              otras {inv.copias_viejas}.</p>
            <button className="boton-borde" disabled={borrando || inv.hay_trabajo || inv.copias_viejas === 0}
              onClick={() => conPermiso('/api/espacio/copias-viejas',
                `Se borran ${inv.copias_viejas} copias de seguridad viejas (${inv.copias_viejas_texto}). La más reciente se queda. ¿Seguir?`)}>
              {inv.copias_viejas === 0 ? 'No hay copias viejas' : `Borrar copias viejas (${inv.copias_viejas_texto})`}</button>
          </section>
          <section className="rev-tarjeta">
            <h2>Videos ya subidos (más de 30 días): {inv.videos_viejos_texto}</h2>
            <p className="pequeno">De los videos terminados hace más de un mes se borran las imágenes, voces y clips.
              El video final sigue en «Videos › Xandart» y el guion queda. <b>Esos videos ya no se podrán volver a
              hacer ni editar.</b></p>
            {inv.videos_viejos > 0 && <details><summary className="pequeno">Ver los {inv.videos_viejos} videos</summary>
              <ul className="pequeno">{inv.videos_viejos_lista.map((n) => <li key={n}>{n}</li>)}</ul></details>}
            <button className="boton-borde" disabled={borrando || inv.hay_trabajo || inv.videos_viejos === 0}
              onClick={() => conPermiso('/api/espacio/videos-viejos',
                `Se borran los archivos de trabajo de ${inv.videos_viejos} videos ya terminados (${inv.videos_viejos_texto}). Sus videos finales se quedan en Videos › Xandart, pero ya no se podrán rehacer. ¿Seguir?`)}>
              {inv.videos_viejos === 0 ? 'No hay videos viejos' : `Liberar ${inv.videos_viejos_texto}`}</button>
          </section>
          {hecho && <p>{hecho}</p>}
          {error && <p className="error">{error}</p>}
        </>
      )}
    </div>
  );
}
