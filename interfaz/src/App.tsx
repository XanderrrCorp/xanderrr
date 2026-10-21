import { lazy, Suspense, useEffect, useState } from 'react';
import { Navigate, Route, Routes, useNavigate, useSearchParams } from 'react-router-dom';
import { api, type Cuenta, type EstadoLocal, type Sesion } from './api';
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
import { Espacio } from './paginas/Espacio';
import { Personajes } from './paginas/Personajes';
import { PersonajeDetalle } from './paginas/PersonajeDetalle';
import { Producir } from './paginas/Producir';
import { Estilos } from './paginas/Estilos';
import { Miniaturas } from './paginas/Miniaturas';
import { Media } from './paginas/Media';
import { CanalNuevo } from './paginas/CanalNuevo';
import { Creditos } from './paginas/Creditos';
import { AvisoRespaldo } from './componentes/Respaldo';
import { Esqueleto } from './componentes/Estados';
import { Entrar, Preparando } from './paginas/Entrar';
import { Cuentas, MiCuenta } from './paginas/MiCuenta';

// tus módulos privados van en archivos aparte: solo se descargan cuando tú los abres (nada de su texto va en la página
// que recibe cualquier usuario); en el Paso C el servidor además solo se los entrega al dueño
const Tracy = lazy(() => import('./paginas/Tracy').then((m) => ({ default: m.Tracy })));
const TracyVideo = lazy(() => import('./paginas/Tracy').then((m) => ({ default: m.TracyVideo })));
const Calma = lazy(() => import('./paginas/Calma').then((m) => ({ default: m.Calma })));
const Explica = lazy(() => import('./paginas/Explica').then((m) => ({ default: m.Explica })));
const Cola = lazy(() => import('./paginas/Cola').then((m) => ({ default: m.Cola })));

// (Paso B) Primero se mira si hay sesión: sin sesión solo se ve la pantalla de entrar (nada de datos).
export function App() {
  const [sesion, setSesion] = useState<Sesion | null>(null);
  const [params] = useSearchParams();
  const ir = useNavigate();
  useEffect(() => {
    let espera: number | undefined;
    const mirar = () => api<Sesion>('/api/v2/sesion').then((s) => {
      setSesion(s);
      if (s.preparando) espera = window.setTimeout(mirar, 3000);
    }).catch(() => { espera = window.setTimeout(mirar, 3000); });
    mirar();
    const sinSesion = () => setSesion({ conectado: false });
    window.addEventListener('xandart:sin-sesion', sinSesion);
    return () => { window.clearTimeout(espera); window.removeEventListener('xandart:sin-sesion', sinSesion); };
  }, []);

  if (!sesion) return null;
  if (sesion.preparando) return <Preparando />;
  if (!sesion.conectado || sesion.cambiar_clave) {
    return <Entrar sesion={sesion} listo={(s) => {
      if (s.cambiar_clave) { setSesion(s); return; }
      // vuelve a donde iba: una página vieja (/, /admin) se abre fuera de esta aplicación
      const volver = params.get('volver') ?? '';
      if (volver.startsWith('/') && !volver.startsWith('//') && !volver.startsWith('/app')) { window.location.href = volver; return; }
      setSesion(s);
      const dentro = volver.startsWith('/app') ? volver.slice(4) || '/' : '/';
      ir(dentro, { replace: true });
    }} />;
  }
  return <Marco />;
}

function Marco() {
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
        <AvisoRespaldo />
        {prep && prep.activo && prep.fase !== 'listo' && (
          <div className={`aviso-prep ${prep.fase === 'error' ? 'malo' : ''}`} role="status">
            {prep.fase === 'error'
              ? <>No se preparó la plataforma: {prep.error}. Tus videos siguen intactos.</>
              : <>{prep.detalle || 'Preparando…'} La copia queda en <b>{prep.carpeta_copias}</b>. Mientras tanto todo sigue funcionando.</>}
          </div>
        )}
        <main>
          <Suspense fallback={<Esqueleto filas={5} />}>
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
            <Route path="/creditos" element={<Creditos />} />
            <Route path="/formatos" element={<Formatos />} />
            <Route path="/planes" element={<Planes />} />
            <Route path="/entrar" element={<Navigate to="/" replace />} />
            <Route path="/cuenta" element={<MiCuenta cuenta={cuenta} />} />
            <Route path="/cuentas" element={<Cuentas />} />
            <Route path="/pronto/:que" element={<Pronto />} />
            <Route path="*" element={<Pronto />} />
          </Routes>
          </Suspense>
        </main>
      </div>
    </div>
  );
}
