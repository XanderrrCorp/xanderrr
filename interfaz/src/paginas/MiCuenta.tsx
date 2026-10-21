import { useEffect, useState, type FormEvent } from 'react';
import { Copy, LogOut } from 'lucide-react';
import { api, type Cuenta, type CuentaBeta } from '../api';
import { Esqueleto, Girando, Vacio } from '../componentes/Estados';

// (Paso B) Mi cuenta: cambiar la contraseña y salir. Cuentas beta (solo administración): crearlas con contraseña
// temporal, pausarlas y darles una contraseña nueva si la olvidan. No hay registro abierto.

export async function salir() {
  await api('/api/v2/salir', { cuerpo: {} }).catch(() => {});
  window.location.href = '/app/entrar';
}

export function MiCuenta({ cuenta }: { cuenta: Cuenta | null }) {
  const [actual, setActual] = useState('');
  const [nueva, setNueva] = useState('');
  const [otra, setOtra] = useState('');
  const [estado, setEstado] = useState<{ ok?: string; error?: string; enviando?: boolean }>({});

  async function cambiar(e: FormEvent) {
    e.preventDefault();
    if (nueva !== otra) { setEstado({ error: 'Las dos contraseñas nuevas no coinciden.' }); return; }
    setEstado({ enviando: true });
    try {
      await api('/api/v2/cambiar-clave', { cuerpo: { actual, nueva } });
      setActual(''); setNueva(''); setOtra('');
      setEstado({ ok: 'Listo: tu contraseña quedó cambiada. Las demás sesiones abiertas se cerraron.' });
    } catch (ex) {
      setEstado({ error: (ex as Error).message });
    }
  }

  return (
    <div className="pagina angosta">
      <h1>Mi cuenta</h1>
      {cuenta && <p className="tenue">Entraste como <b>{cuenta.usuario.email}</b>.</p>}
      <form className="tarjeta-formato" onSubmit={cambiar} style={{ marginTop: 18 }}>
        <h3>Cambiar mi contraseña</h3>
        <label className="campo">Contraseña actual
          <input type="password" value={actual} onChange={(e) => setActual(e.target.value)} autoComplete="current-password" required />
        </label>
        <label className="campo">Contraseña nueva (mínimo 8 caracteres)
          <input type="password" value={nueva} onChange={(e) => setNueva(e.target.value)} autoComplete="new-password" required />
        </label>
        <label className="campo">Escríbela otra vez
          <input type="password" value={otra} onChange={(e) => setOtra(e.target.value)} autoComplete="new-password" required />
        </label>
        {estado.error && <p className="error" role="alert">{estado.error}</p>}
        {estado.ok && <p className="ok-texto" role="status">{estado.ok}</p>}
        <button className="boton-primario" style={{ marginTop: 14 }} disabled={estado.enviando}>
          {estado.enviando ? <Girando texto="Guardando…" /> : 'Guardar contraseña'}</button>
      </form>
      <button className="boton-borde" style={{ marginTop: 18 }} onClick={salir}><LogOut size={16} />Cerrar sesión</button>
    </div>
  );
}

function fecha(iso: string | null) {
  return iso ? new Date(iso).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' }) : '—';
}

export function Cuentas() {
  const [lista, setLista] = useState<CuentaBeta[] | null>(null);
  const [email, setEmail] = useState('');
  const [nombre, setNombre] = useState('');
  const [error, setError] = useState('');
  const [nueva, setNueva] = useState<CuentaBeta | null>(null);       // para mostrar UNA vez la contraseña temporal
  const [copiado, setCopiado] = useState(false);
  const traer = () => api<CuentaBeta[]>('/api/v2/admin/usuarios').then(setLista).catch((e) => setError(e.message));
  useEffect(() => { traer(); }, []);

  async function crear(e: FormEvent) {
    e.preventDefault();
    setError('');
    try {
      const c = await api<CuentaBeta>('/api/v2/admin/usuarios', { cuerpo: { email, nombre } });
      setNueva(c); setCopiado(false); setEmail(''); setNombre('');
      traer();
    } catch (ex) { setError((ex as Error).message); }
  }

  async function bloqueo(c: CuentaBeta) {
    if (!c.bloqueado && !confirm(`¿Pausar la cuenta de ${c.email}? No podrá entrar hasta que la actives otra vez.`)) return;
    try { await api(`/api/v2/admin/usuarios/${c.id}/bloqueo`, { cuerpo: { bloqueado: !c.bloqueado } }); traer(); }
    catch (ex) { setError((ex as Error).message); }
  }

  async function temporal(c: CuentaBeta) {
    if (!confirm(`¿Darle una contraseña nueva a ${c.email}? La que tenía deja de servir.`)) return;
    try { setNueva(await api<CuentaBeta>(`/api/v2/admin/usuarios/${c.id}/clave-temporal`, { cuerpo: {} })); setCopiado(false); traer(); }
    catch (ex) { setError((ex as Error).message); }
  }

  const texto = nueva ? `Tu cuenta de Xandart:\nCorreo: ${nueva.email}\nContraseña temporal: ${nueva.clave_temporal_texto}\n` +
    'Al entrar te pedirá que pongas tu propia contraseña.' : '';

  return (
    <div className="pagina angosta">
      <h1>Cuentas beta</h1>
      <p className="tenue">Solo tú creas las cuentas. Cada persona recibe una contraseña temporal y al entrar pone la suya.</p>
      <form className="tarjeta-formato" onSubmit={crear} style={{ marginTop: 18 }}>
        <h3>Crear una cuenta</h3>
        <label className="campo">Correo<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
        <label className="campo">Nombre (opcional)<input value={nombre} onChange={(e) => setNombre(e.target.value)} /></label>
        <button className="boton-primario" style={{ marginTop: 14 }}>Crear cuenta</button>
      </form>
      {nueva && (
        <div className="aviso-canal" role="status" style={{ marginTop: 16 }}>
          <div>
            <b>Mándale esto a {nueva.nombre || nueva.email}</b>
            <span className="tenue pequeno">Solo se muestra ahora. Si se pierde, dale otra contraseña temporal.</span>
            <pre className="clave-temporal">{texto}</pre>
          </div>
          <button className="boton-borde pequeno" onClick={() => navigator.clipboard.writeText(texto).then(() => setCopiado(true))}>
            <Copy size={14} />{copiado ? 'Copiado' : 'Copiar'}</button>
        </div>
      )}
      {error && <p className="error" role="alert">{error}</p>}
      <h2 style={{ marginTop: 26 }}>Cuentas</h2>
      {!lista ? <Esqueleto filas={3} /> : lista.length <= 1 ? (
        <Vacio icono="personajes" titulo="Todavía no hay cuentas beta" texto="Crea la primera arriba." />
      ) : (
        <div className="lista-cuentas">
          {lista.map((c) => (
            <div key={c.id} className="fila-cuenta">
              <div className="crece">
                <b>{c.nombre || c.email}</b>
                <span className="tenue pequeno">{c.email} · {c.rol === 'owner' ? 'Owner (tú)' : c.rol === 'admin' ? 'Admin' : 'Beta'}
                  {' · '}última vez: {fecha(c.ultima_actividad)}
                  {c.clave_temporal ? ' · aún no pone su contraseña' : ''}{c.bloqueado ? ' · PAUSADA' : ''}</span>
              </div>
              {c.rol !== 'owner' && <>
                <button className="boton-borde pequeno" onClick={() => temporal(c)}>Contraseña nueva</button>
                <button className="boton-borde pequeno" onClick={() => bloqueo(c)}>{c.bloqueado ? 'Activar' : 'Pausar'}</button>
              </>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
