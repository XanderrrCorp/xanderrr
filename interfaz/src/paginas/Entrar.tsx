import { useState, type FormEvent } from 'react';
import { Eye, EyeOff, LockKeyhole } from 'lucide-react';
import { api, type Sesion } from '../api';
import { Girando } from '../componentes/Estados';

// (Paso B) Pantalla de entrar. Tres casos: la primera vez del dueño (crea su contraseña), entrar con correo y
// contraseña, y cambiar la contraseña temporal que el dueño le dio a un beta.

function Clave({ etiqueta, valor, cambiar, auto, enfocar }: {
  etiqueta: string; valor: string; cambiar: (v: string) => void; auto: string; enfocar?: boolean;
}) {
  const [ver, setVer] = useState(false);
  return (
    <label className="campo">
      {etiqueta}
      <span className="clave-con-ojo">
        <input type={ver ? 'text' : 'password'} value={valor} onChange={(e) => cambiar(e.target.value)}
          autoComplete={auto} autoFocus={enfocar} required />
        <button type="button" className="boton-icono" onClick={() => setVer(!ver)}
          aria-label={ver ? 'Ocultar contraseña' : 'Mostrar contraseña'}>
          {ver ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </span>
    </label>
  );
}

export function Entrar({ sesion, listo }: { sesion: Sesion; listo: (s: Sesion) => void }) {
  const primeraVez = !sesion.conectado && !!sesion.crear_clave_dueno;
  const cambiar = sesion.conectado && !!sesion.cambiar_clave;
  const [email, setEmail] = useState(primeraVez && sesion.correo_dueno && !sesion.correo_dueno.endsWith('.local')
    ? sesion.correo_dueno : '');
  const [clave, setClave] = useState('');
  const [otra, setOtra] = useState('');
  const [actual, setActual] = useState('');
  const [recordar, setRecordar] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setError('');
    if ((primeraVez || cambiar) && clave !== otra) { setError('Las dos contraseñas no coinciden.'); return; }
    if ((primeraVez || cambiar) && clave.length < 8) { setError('La contraseña debe tener al menos 8 caracteres.'); return; }
    setEnviando(true);
    try {
      const r = primeraVez
        ? await api<Sesion>('/api/v2/crear-clave-dueno', { cuerpo: { email, clave, recordar } })
        : cambiar
          ? await api<Sesion>('/api/v2/cambiar-clave', { cuerpo: { actual, nueva: clave } })
          : await api<Sesion>('/api/v2/entrar', { cuerpo: { email, clave, recordar } });
      // entró con la temporal: esta misma pantalla pasa a «pon tu contraseña» con la temporal ya puesta
      if (r.cambiar_clave && !cambiar) { setActual(clave); setClave(''); setOtra(''); }
      listo(r);
    } catch (ex) {
      setError((ex as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  const titulo = primeraVez ? 'Crea tu contraseña' : cambiar ? 'Pon tu propia contraseña' : 'Entra a Xandart';
  const texto = primeraVez
    ? 'Es la primera vez que abres esta versión. Desde ahora Xandart pide tu correo y una contraseña para entrar. Tus canales y videos quedan igual.'
    : cambiar
      ? 'Entraste con una contraseña temporal. Elige una tuya para seguir; la temporal deja de servir.'
      : 'Escribe tu correo y tu contraseña.';

  return (
    <div className="entrar">
      <form className="entrar-caja" onSubmit={enviar}>
        <div className="marca"><i>X</i>Xandart</div>
        <span className="entrar-icono" aria-hidden="true"><LockKeyhole size={22} /></span>
        <h1>{titulo}</h1>
        <p className="tenue">{texto}</p>
        {!cambiar && (
          <label className="campo">
            Correo
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email"
              autoFocus required />
          </label>
        )}
        {cambiar && <Clave etiqueta="Contraseña temporal (la que te dieron)" valor={actual} cambiar={setActual}
          auto="current-password" enfocar />}
        <Clave etiqueta={primeraVez || cambiar ? 'Contraseña nueva (mínimo 8 caracteres)' : 'Contraseña'} valor={clave}
          cambiar={setClave} auto={primeraVez || cambiar ? 'new-password' : 'current-password'} />
        {(primeraVez || cambiar) && <Clave etiqueta="Escríbela otra vez" valor={otra} cambiar={setOtra} auto="new-password" />}
        {!cambiar && (
          <label className="entrar-recordar">
            <input type="checkbox" checked={recordar} onChange={(e) => setRecordar(e.target.checked)} />
            Recordarme en este equipo (30 días)
          </label>
        )}
        {error && <p className="error" role="alert">{error}</p>}
        <button className="boton-primario" disabled={enviando}>
          {enviando ? <Girando texto="Un momento…" /> : primeraVez ? 'Guardar y entrar' : cambiar ? 'Guardar y seguir' : 'Entrar'}
        </button>
        {primeraVez && (
          <p className="tenue pequeno">Si algún día la olvidas: menú Inicio de Windows → Xandart → «Restablecer mi
            contraseña de Xandart Nueva». No hace falta correo.</p>
        )}
        {!primeraVez && !cambiar && (
          <p className="tenue pequeno">¿Olvidaste tu contraseña? Si eres el dueño, usa «Restablecer mi contraseña» en el
            menú Inicio de Windows (carpeta Xandart). Si te dieron una cuenta beta, pídele una contraseña nueva a quien te
            invitó.</p>
        )}
      </form>
    </div>
  );
}

export function Preparando() {
  return (
    <div className="entrar">
      <div className="entrar-caja">
        <div className="marca"><i>X</i>Xandart</div>
        <h1>Actualizando Xandart</h1>
        <p className="tenue">Estoy guardando una copia de seguridad y poniendo al día tus datos. Tarda unos minutos; esta
          página sigue sola cuando termine.</p>
        <Girando texto="Trabajando…" />
      </div>
    </div>
  );
}
