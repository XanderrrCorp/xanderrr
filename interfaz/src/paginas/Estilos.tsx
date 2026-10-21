import { useEffect, useState } from 'react';
import { api } from '../api';
import { Esqueleto, ErrorAmable, Vacio } from '../componentes/Estados';
import { Icono } from '../componentes/Icono';

interface FilaEstilo { id: string; clave: string; nombre: string; descripcion: string; publico: boolean }

// Estilos visuales: los tuyos (privados) y los del catálogo de Xandart. Para cambiar uno del catálogo, se duplica.
export function Estilos({ nuevo = false }: { nuevo?: boolean }) {
  const [filas, setFilas] = useState<FilaEstilo[] | null>(null);
  const [error, setError] = useState('');
  const [hecho, setHecho] = useState('');
  const cargar = () => api<FilaEstilo[]>('/api/v2/recursos/estilos').then(setFilas).catch((e) => { setError(e.message); setFilas([]); });
  useEffect(() => { cargar(); }, []);

  async function duplicar(f: FilaEstilo) {
    setError(''); setHecho('');
    try {
      const r = await api<{ nombre: string }>(`/api/v2/recursos/estilos/${f.id}/duplicar`, { cuerpo: {} });
      setHecho(`Listo: «${r.nombre}» quedó en tus estilos.`); cargar();
    } catch (e) { setError((e as Error).message); }
  }

  const tuyos = (filas ?? []).filter((f) => !f.publico);
  const catalogo = (filas ?? []).filter((f) => f.publico);
  return (
    <div className="pagina">
      <div className="seccion-cab" style={{ marginTop: 0 }}><h1>Estilos</h1></div>
      <p className="tenue">El estilo decide cómo se ven las imágenes de tus videos. Cada canal usa uno.</p>
      {nuevo && (
        <div className="aviso-canal">
          <Icono nombre="estilo" />
          <div><b>Crear un estilo desde cero llega pronto</b>
            <span className="tenue pequeno">Mientras tanto, duplica uno del catálogo: la copia es tuya y la usas en tu canal.</span></div>
        </div>
      )}
      {error && <ErrorAmable texto={error} reintentar={cargar} />}
      {hecho && <p className="ok-texto">{hecho}</p>}
      {filas === null ? <Esqueleto tarjetas={3} /> : (
        <>
          <h2 className="sub">Tus estilos</h2>
          {tuyos.length === 0 ? <Vacio icono="estilos" titulo="Aún no tienes estilos propios" texto="Duplica uno del catálogo para empezar." />
            : <div className="rejilla-formatos">{tuyos.map((f) => <Tarjeta key={f.id} f={f} />)}</div>}
          {catalogo.length > 0 && <>
            <h2 className="sub">Catálogo de Xandart</h2>
            <div className="rejilla-formatos">{catalogo.map((f) => <Tarjeta key={f.id} f={f} duplicar={() => duplicar(f)} />)}</div>
          </>}
        </>
      )}
    </div>
  );
}

function Tarjeta({ f, duplicar }: { f: FilaEstilo; duplicar?: () => void }) {
  return (
    <article className="tarjeta-formato">
      <b>{f.nombre}</b>
      <p className="tenue pequeno">{f.descripcion || 'Sin descripción'}</p>
      <div className="fila-botones">
        <span className="etiqueta">{f.publico ? 'Catálogo' : 'Privado'}</span>
        <span className="crece" />
        {duplicar && <button className="boton-borde pequeno" onClick={duplicar}>Duplicar</button>}
      </div>
    </article>
  );
}
