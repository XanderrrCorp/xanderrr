import { useEffect, useState } from 'react';
import { Route, Routes } from 'react-router-dom';
import { api, type Cuenta, type EstadoLocal } from './api';
import { Barra } from './componentes/Barra';
import { Lateral } from './componentes/Lateral';
import { Canales } from './paginas/Canales';
import { Editor } from './paginas/Editor';
import { Formatos } from './paginas/Formatos';
import { Inicio } from './paginas/Inicio';
import { Miniatura } from './paginas/Miniatura';
import { MisVideos } from './paginas/MisVideos';
import { Planes } from './paginas/Planes';
import { Pronto } from './paginas/Pronto';
import { Revision } from './paginas/Revision';
import { Tracy, TracyVideo } from './paginas/Tracy';
import { Calma } from './paginas/Calma';
import { Explica } from './paginas/Explica';
import { Cola } from './paginas/Cola';
import { Espacio } from './paginas/Espacio';
import { Personajes } from './paginas/Personajes';
import { PersonajeDetalle } from './paginas/PersonajeDetalle';
import { Producir } from './paginas/Producir';
import { Estilos } from './paginas/Estilos';
import { Miniaturas } from './paginas/Miniaturas';
import { Media } from './paginas/Media';
import { CanalNuevo } from './paginas/CanalNuevo';

export function App() {
  const [cuenta, setCuenta] = useState<Cuenta | null>(null);
  const [prep, setPrep] = useState<EstadoLocal | null>(null);
  useEffect(() => {
    // la primera vez la plataforma hace la copia de seguridad y registra tus videos: se avisa hasta que termine
    let espera: number | undefined;
    const mirar = () => api<EstadoLocal>('/api/v2/estado-local').then((e) => {
      setPrep(e);
      if (e.activo && !['listo', 'error'].includes(e.fase)) espera = window.setTimeout(mirar, 3000);
    }).catch(() => {});
    mirar();
    return () => window.clearTimeout(espera);
  }, []);
  useEffect(() => { api('/api/cola').catch(() => {}); }, []);   // la cola sigue donde iba al abrir Xandart
  useEffect(() => {
    const traer = () => api<Cuenta>('/api/v2/cuenta').then(setCuenta).catch(() => {});
    traer();
    const cada = window.setInterval(traer, 30000);      // el saldo cambia cuando termina un paso
    return () => window.clearInterval(cada);
  }, []);

  return (
    <div className="marco">
      <Lateral cuenta={cuenta} />
      <div className="contenido">
        <Barra cuenta={cuenta} />
        {prep && prep.activo && prep.fase !== 'listo' && (
          <div className={`aviso-prep ${prep.fase === 'error' ? 'malo' : ''}`} role="status">
            {prep.fase === 'error'
              ? <>No se preparó la plataforma: {prep.error}. Tus videos siguen intactos.</>
              : <>{prep.detalle || 'Preparando…'} La copia queda en <b>{prep.carpeta_copias}</b>. Mientras tanto todo sigue funcionando.</>}
          </div>
        )}
        <main>
          <Routes>
            <Route path="/" element={<Inicio />} />
            <Route path="/videos" element={<MisVideos />} />
            <Route path="/videos/:slug/editor" element={<Editor />} />
            <Route path="/videos/:slug/miniatura" element={<Miniatura />} />
            <Route path="/videos/:slug" element={<Revision />} />
            <Route path="/tracy" element={<Tracy />} />
            <Route path="/calma" element={<Calma />} />
            <Route path="/explica" element={<Explica />} />
            <Route path="/cola" element={<Cola />} />
            <Route path="/espacio" element={<Espacio />} />
            <Route path="/tracy/:slug" element={<TracyVideo />} />
            <Route path="/canales" element={<Canales />} />
            <Route path="/canales/nuevo" element={<CanalNuevo />} />
            <Route path="/producir" element={<Producir />} />
            <Route path="/producir/video" element={<Producir personalizado />} />
            <Route path="/producir/:slug" element={<Producir />} />
            <Route path="/personajes" element={<Personajes />} />
            <Route path="/personajes/nuevo" element={<Personajes nuevo />} />
            <Route path="/personajes/:id" element={<PersonajeDetalle />} />
            <Route path="/estilos" element={<Estilos />} />
            <Route path="/estilos/nuevo" element={<Estilos nuevo />} />
            <Route path="/miniaturas" element={<Miniaturas />} />
            <Route path="/media" element={<Media />} />
            <Route path="/formatos" element={<Formatos />} />
            <Route path="/planes" element={<Planes />} />
            <Route path="/pronto/:que" element={<Pronto />} />
            <Route path="*" element={<Pronto />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
