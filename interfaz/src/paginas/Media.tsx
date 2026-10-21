import { useEffect, useState } from 'react';
import { api, paginaVieja } from '../api';
import { Esqueleto, ErrorAmable, Vacio } from '../componentes/Estados';

interface Audio { huella: string; clase: string; tipo: string; nombre_original: string; licencia: string; fuente: string }

// Media: la biblioteca de música y efectos de sonido, cada archivo con su licencia registrada.
export function Media() {
  const [archivos, setArchivos] = useState<Audio[] | null>(null);
  const [error, setError] = useState('');
  const [clase, setClase] = useState<'musica' | 'sfx'>('musica');
  const cargar = () => api<{ archivos: Audio[] }>('/api/biblioteca').then((r) => setArchivos(r.archivos)).catch((e) => { setError(e.message); setArchivos([]); });
  useEffect(() => { cargar(); }, []);
  const lista = (archivos ?? []).filter((a) => a.clase === clase);
  return (
    <div className="pagina">
      <div className="seccion-cab" style={{ marginTop: 0 }}><h1>Media</h1>
        <a className="boton-borde pequeno" href={`${paginaVieja()}#sonidos`}>Subir audio con su licencia</a></div>
      <p className="tenue">Música y efectos que tus videos pueden usar. Solo entra audio con licencia que se pueda comprobar.</p>
      <div className="alternar" role="group" aria-label="Tipo" style={{ display: 'inline-flex', margin: '6px 0 16px' }}>
        <button className={clase === 'musica' ? 'sel' : ''} onClick={() => setClase('musica')}>Música</button>
        <button className={clase === 'sfx' ? 'sel' : ''} onClick={() => setClase('sfx')}>Efectos</button>
      </div>
      {error && <ErrorAmable texto={error} reintentar={cargar} />}
      {archivos === null ? <Esqueleto filas={5} /> : lista.length === 0 ? (
        <Vacio icono="sonidos" titulo={clase === 'musica' ? 'Aún no hay música' : 'Aún no hay efectos'}
          texto="Súbelos con su licencia. Mientras tanto, los videos usan los efectos que Xandart genera por código." />
      ) : (
        <div className="lista-media">
          {lista.map((a) => (
            <div key={a.huella} className="fila-media">
              <div><b>{a.nombre_original}</b><span className="tenue pequeno">{a.tipo} · {a.licencia}</span></div>
              <audio controls preload="none" src={`/api/biblioteca/${a.huella}/escuchar`} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
