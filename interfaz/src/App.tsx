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

export function App() {
  const [cuenta, setCuenta] = useState<Cuenta | null>(null);
  const [menu, setMenu] = useState(false);
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
  useEffect(() => {
    const traer = () => api<Cuenta>('/api/v2/cuenta').then(setCuenta).catch(() => {});
    traer();
    const cada = window.setInterval(traer, 30000);      // el saldo cambia cuando termina un paso
    return () => window.clearInterval(cada);
  }, []);

  return (
    <div className="marco">
      <div className="resplandor" aria-hidden="true" />
      <Lateral admin={!!cuenta?.usuario.admin} abierto={menu} cerrar={() => setMenu(false)} />
      <div className="contenido">
        <Barra cuenta={cuenta} menu={() => setMenu(true)} />
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
            <Route path="/tracy/:slug" element={<TracyVideo />} />
            <Route path="/canales" element={<Canales />} />
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
