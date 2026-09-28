import { useEffect, useState } from 'react';
import { api, miles, type Precios } from '../api';
import { Icono } from '../componentes/Icono';

// Solo visual por ahora: no hay pasarela de pago, los botones no cobran nada.
const EXTRAS: Record<string, string[]> = {
  lite: ['Guion, imágenes, voz y edición', 'Miniaturas escala 2×3', 'Shorts desde tus videos', '1 canal'],
  starter: ['Todo lo de Lite', 'Personajes y estilos propios', 'Fotos y clips reales de Pexels', '3 canales'],
  creator: ['Todo lo de Starter', '1080p', 'Canales sin límite', 'Recargas con descuento'],
};

export function Planes() {
  const [p, setP] = useState<Precios | null>(null);
  const [porSemana, setPorSemana] = useState(2);
  const [largo, setLargo] = useState(9);
  const [aviso, setAviso] = useState(false);
  useEffect(() => { api<Precios>('/api/v2/precios').then(setP).catch(() => {}); }, []);

  const necesita = Math.round(porSemana * largo * 4.33);
  const planes = p?.planes ?? [];
  const recomendado = planes.find((x) => x.minutos_mes >= necesita) ?? planes[planes.length - 1];
  const faltan = recomendado ? Math.max(0, necesita - recomendado.minutos_mes) : 0;

  return (
    <div className="pagina">
      <h1 className="titular">Paga por <span className="acento">minutos de video</span></h1>
      <p className="bajada">Dinos cuánto publicas y te decimos qué plan te sirve.</p>

      <section className="calculadora">
        <div>
          <label>Videos por semana: <b>{porSemana}</b></label>
          <input type="range" min={1} max={7} value={porSemana} onChange={(e) => setPorSemana(+e.target.value)} />
        </div>
        <div>
          <label>Minutos por video: <b>{largo}</b></label>
          <input type="range" min={4} max={20} value={largo} onChange={(e) => setLargo(+e.target.value)} />
        </div>
        <div className="calc-res">
          <big>≈ {necesita} min al mes</big>
          <span className="tenue">
            {recomendado ? <>te sirve <b className="dorado">{recomendado.nombre}</b>{faltan ? ` + recargas (${faltan} min más)` : ''}</> : ''}
          </span>
        </div>
      </section>

      <div className="rejilla-planes">
        {planes.map((x) => {
          const videos = Math.floor(x.minutos_mes / largo);
          const rec = x.clave === recomendado?.clave;
          return (
            <article key={x.clave} className={`plan ${rec ? 'rec' : ''}`}>
              <div className="plan-cab">
                {rec && <span className="sello">Recomendado para ti</span>}
                <h3>{x.nombre}</h3>
                <div className="precio">${miles(x.precio_usd_mes)}<small> /mes</small></div>
                <div className="plan-cred"><i className="moneda" />{miles(x.creditos_mes)} créditos <small>≈ {x.minutos_mes} min</small></div>
              </div>
              <div className="plan-cuerpo">
                <div className="cuadritos">{Array.from({ length: Math.min(videos, 14) }, (_, i) => <i key={i} />)}</div>
                <span className="tenue pequeno">≈ {videos} videos de {largo} min al mes</span>
                <ul>{(EXTRAS[x.clave] ?? []).map((t) => <li key={t}><Icono nombre="ok" tam={14} />{t}</li>)}</ul>
                <button className={rec ? 'boton-dorado ancho' : 'boton-borde ancho'} onClick={() => setAviso(true)}>Elegir {x.nombre}</button>
              </div>
            </article>
          );
        })}
      </div>
      {aviso && <p className="aviso-pago">Los pagos llegan pronto: todavía no se cobra nada.</p>}

      {p && p.paquetes.length > 0 && (
        <>
          <div className="seccion-cab"><h2>Recargas sueltas</h2></div>
          <div className="rejilla-paquetes">
            {p.paquetes.map((k) => (
              <article key={k.clave} className="paquete">
                <b>${miles(k.precio_usd)}</b><span><i className="moneda" /> {miles(k.creditos)} créditos</span>
                <small className="tenue">≈ {k.minutos} min de video · no vencen</small>
              </article>
            ))}
          </div>
        </>
      )}
      <div className="garantias">
        <span><Icono nombre="ok" tam={14} /> Lo que no usas del plan se guarda 2 meses</span>
        <span><Icono nombre="ok" tam={14} /> Ves el costo antes de cada paso</span>
        <span><Icono nombre="ok" tam={14} /> Si algo falla por nuestra parte, te devolvemos los créditos</span>
      </div>
    </div>
  );
}
