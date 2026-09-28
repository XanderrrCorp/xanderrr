import { useEffect, useState } from 'react';
import { Route, Routes } from 'react-router-dom';
import { api, type Cuenta } from './api';
import { Barra } from './componentes/Barra';
import { Lateral } from './componentes/Lateral';
import { Canales } from './paginas/Canales';
import { Formatos } from './paginas/Formatos';
import { Inicio } from './paginas/Inicio';
import { MisVideos } from './paginas/MisVideos';
import { Planes } from './paginas/Planes';
import { Pronto } from './paginas/Pronto';

export function App() {
  const [cuenta, setCuenta] = useState<Cuenta | null>(null);
  const [menu, setMenu] = useState(false);
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
        <main>
          <Routes>
            <Route path="/" element={<Inicio />} />
            <Route path="/videos" element={<MisVideos />} />
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
