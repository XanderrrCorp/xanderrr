// Llamadas a Xandart. Un error trae el mensaje que manda el servidor (ya en español).
export async function api<T = unknown>(ruta: string, opciones: { metodo?: string; cuerpo?: unknown } = {}): Promise<T> {
  let r: Response;
  try {
    r = await fetch(ruta, {
      method: opciones.metodo ?? (opciones.cuerpo !== undefined ? 'POST' : 'GET'),
      headers: { 'Content-Type': 'application/json' },
      body: opciones.cuerpo !== undefined ? JSON.stringify(opciones.cuerpo) : undefined,
    });
  } catch {
    ultimoError.texto = `${ruta}: sin conexión`;
    throw new Error('No hay conexión con Xandart. Revisa que su ventana negra siga abierta y vuelve a intentarlo.');
  }
  const datos = await r.json().catch(() => ({}));
  // (Paso B) la sesión venció o la cerraron desde otro lado: la página vuelve a la pantalla de entrar
  if (r.status === 401 && !ruta.startsWith('/api/v2/entrar')) window.dispatchEvent(new Event('xandart:sin-sesion'));
  if (!r.ok) {
    const m = humano(r.status, (datos as { detail?: unknown }).detail);
    ultimoError.texto = `${ruta} → ${r.status}: ${m}`;      // va solo en «Reportar problema»
    throw new Error(m);
  }
  return datos as T;
}

/** (Paso C) Quién está conectado: la página esconde lo que su cuenta no puede usar (el servidor igual lo cierra). */
export const conectado = { rol: '' };
export const esDueno = () => conectado.rol === 'owner';
export const esAdmin = () => conectado.rol === 'owner' || conectado.rol === 'admin';

/** El último error que vio la persona (para adjuntarlo al reportar un problema). */
export const ultimoError = { texto: '' };

/** Errores en palabras normales: el servidor ya los manda en español; lo técnico se traduce aquí. */
export function humano(estado: number, detalle?: unknown): string {
  const texto = typeof detalle === 'string' ? detalle : '';
  if (/HTTP 429|RESOURCE_EXHAUSTED|demasiadas/i.test(texto) || estado === 429)
    return 'El servicio está muy ocupado en este momento. Espera un par de minutos y vuelve a intentarlo; no se te cobró.';
  if (texto && !/Traceback|Exception|Error\(|errno|\{\s*"/.test(texto)) return texto;
  if (estado === 404) return 'No encontramos eso. Puede que se haya movido o borrado.';
  if (estado === 403) return 'Esto no está disponible en tu cuenta.';
  if (estado === 402) return 'No tienes créditos suficientes para esto.';
  if (estado >= 500) return 'Algo falló de nuestro lado. Vuelve a intentarlo; si se repite, avísanos.';
  return 'No se pudo completar. Revisa los datos y vuelve a intentarlo.';
}

export const miles = (n: number) => Math.round(n).toLocaleString('es-CO');

export interface UsuarioSesion { id: string; email: string; nombre: string; rol: string; admin: boolean }
export interface Sesion {
  conectado: boolean; usuario?: UsuarioSesion; cambiar_clave?: boolean; preparando?: boolean;
  crear_clave_dueno?: boolean; correo_dueno?: string | null;
}
export interface CuentaBeta extends UsuarioSesion {
  bloqueado: boolean; clave_temporal: boolean; creado: string | null; ultima_actividad: string | null;
  clave_temporal_texto?: string;
}

export interface Cuenta {
  gasto_mes_usd: number;
  usuario: { email: string; nombre: string; rol: string; a_costo: boolean; admin: boolean };
  espacio: { id: string; nombre: string };
  saldo: { creditos: number; usd: number; minutos: number; bajo: boolean };
}

export interface Ref { id: string; clave: string; nombre: string }
export interface Canal {
  id: string; clave: string; nombre: string; formato: Ref | null; videos: number;
  estilo?: Ref | null; ajustes?: Record<string, unknown>;
}
export interface Formato {
  id: string; clave: string; nombre: string; descripcion: string; publico: boolean; estudio?: boolean;
  datos: { duraciones_min?: number[]; duracion_min?: number; idea_ejemplo?: string; relacion_aspecto?: string; formula?: string; estilo?: string };
}

export interface Trabajo { paso: string; progreso: number; mensaje: string; activo: boolean; error: string | null }
export interface VideoLista {
  slug: string; titulo: string; minutos: number; canal: string; estado: string;
  pasos: Record<string, string>; portada: string | null; video: string | null; trabajo: Trabajo | null;
}
export interface Escena {
  id: number; seccion: string; narracion: string; accion: string; imagen: string | null;
  puede_regenerar?: boolean; medico?: boolean;
}
export interface Estimacion {
  total: number; faltan: number; texto: string; prueba: number; prueba_texto: string; maximo_texto: string;
  gastado_texto?: string; total_texto?: string; pasa_maximo: boolean;
}
export interface Prueba {
  escenas: number; generadas: number; ya_estaban: number; llamadas: number; proveedor: string; modelo: string;
  costo_corrida: string; costo_medio_imagen: string | null; hoja: string | null;
  proyeccion: { imagenes: number; texto: string; base: string } | null;
}
export interface VideoDetalle {
  slug: string; titulo: string; minutos: number; pasos: Record<string, string>; costo: string;
  escenas: Escena[]; video: string | null; trabajo: (Trabajo & { segundos: number }) | null;
  estimacion_imagenes?: Estimacion; prueba: Prueba | null; puede_short?: boolean; vertical: boolean;
  divulgacion: boolean; guion: string | null; modo?: string;
  revision_video?: { resumen: string; problemas: { cuadro: number; minuto: string; que: string; gravedad: string }[] };
  llamados?: { comentario_fijado: string | null; avisos: string[]; lista: { tipo: string; seccion: string; texto: string }[] };
  creditos_fotos?: string | null;
  uso_claude?: { pedidos: number; pasos: { paso: string; pedidos: number; porcentaje: number; modelos: string[]; minutos: number }[] } | null;
}

export interface Cotizacion {
  creditos: number; usd: number; precio_cliente: { creditos: number; usd: number };
  a_costo: boolean; alcanza: boolean; saldo: number; costo_real_usd?: number;
}

export interface Precios {
  valor_credito_usd: number;
  planes: { clave: string; nombre: string; precio_usd_mes: number; minutos_mes: number; creditos_mes: number;
            tope_acumulado_meses: number }[];
  paquetes: { clave: string; nombre: string; precio_usd: number; creditos: number; minutos: number }[];
}

export const archivo = (slug: string, ruta: string) => `/archivos/${slug}/${ruta}`;
// Mientras la página nueva no tenga todas las pantallas, la revisión de un video se hace en la de siempre.
export const paginaVieja = (slug?: string) => (slug ? `/#${slug}` : '/');

export interface EstadoLocal { activo: boolean; fase: string; detalle: string; error: string | null; carpeta_copias: string }

// ------------------------------------------------------------ editor
export interface EscenaLinea {
  id: number; inicio: number; fin: number; imagen: string; animacion: string | null; video_real: string | null;
  narracion: string; seccion: string; puede_regenerar: boolean; modo: string; corte_movido: boolean;
}
export interface SubLinea { inicio: number; fin: number; texto: string; escena: number | null; editado: boolean }
export interface LineaDeTiempo {
  slug: string; titulo: string; duracion: number; escenas: EscenaLinea[];
  voz: { escena: number; inicio: number; fin: number }[];
  musica: { inicio: number; fin: number; nombre: string; animo: string | null }[];
  sfx: { inicio: number; tipo: string; dur: number }[];
  subtitulos: SubLinea[]; video: string | null; video_version: number;
  ediciones: { version: number; actualizado: string | null; pendientes: boolean };
  trabajo: (Trabajo & { segundos: number }) | null;
}
export const reloj = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, '0')}`;

export interface Aviso { id: string; tipo: 'listo' | 'error'; titulo: string; texto: string; enlace: string | null; fecha: number; leido: boolean }
export interface Respaldo { estado: 'ok' | 'error' | 'ninguna' | 'movida' | 'copiando' | 'actualizando'; segundos?: number; carpeta?: string; fecha?: string; total_bytes?: number;
  partes?: Record<string, number>; error?: string; visto?: boolean; migracion?: string }
export interface MovimientoCredito { fecha: string; tipo: string; creditos: number; bolsa: string; accion: string | null;
  cantidad: number | null; nota: string; video: string | null; que: string; costo_real_usd?: number }
export interface ModuloEstudio { clave: string; nombre: string; ir: string; menu: string }
/** Tus módulos privados (solo la cuenta del dueño; a cualquier otro el servidor responde 403). */
let _estudio: Promise<ModuloEstudio[]> | null = null;
export const modulosEstudio = () => (_estudio ??= api<{ modulos: ModuloEstudio[] }>('/api/v2/estudio')
  .then((r) => r.modulos).catch(() => []));
