import { useEffect, useState } from 'react';
import { api, type Formato } from '../api';

const EN_CAMINO = [
  { nombre: 'Hombre de palo', texto: 'Muñecos de palitos con caras expresivas sobre fondos pintados con detalle.' },
  { nombre: 'Top X', texto: 'Cuenta regresiva con escenas ilustradas y un número grande por puesto.' },
  { nombre: 'Narración de historias', texto: 'Ilustración de novela gráfica, personajes con expresión, relato continuo.' },
  { nombre: 'Personaje garabato', texto: 'Un personaje simple y fijo dentro de escenarios detallados y coloridos.' },
  { nombre: 'Videos para dormir', texto: 'Paisajes pintados y calmados, cortes lentos, voz suave; videos largos.' },
];

export function Formatos() {
  const [formatos, setFormatos] = useState<Formato[]>([]);
  useEffect(() => { api<Formato[]>('/api/v2/recursos/formatos').then(setFormatos).catch(() => {}); }, []);
  return (
    <div className="pagina">
      <div className="seccion-cab"><h1>Formatos</h1></div>
      <p className="tenue">Un formato junta guion, estilo y edición. Usa uno del catálogo o, pronto, crea el tuyo.</p>
      <div className="rejilla-formatos">
        {formatos.map((f) => (
          <article key={f.id} className="tarjeta-formato">
            <b>{f.nombre}</b><p className="tenue">{f.descripcion}</p>
            <span className="pequeno">{(f.datos.duraciones_min ?? []).join(' · ')} min · {f.publico ? 'Catálogo' : 'Tuyo'}</span>
          </article>
        ))}
        {EN_CAMINO.map((f) => (
          <article key={f.nombre} className="tarjeta-formato pronto">
            <b>{f.nombre} <em>pronto</em></b><p className="tenue">{f.texto}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
