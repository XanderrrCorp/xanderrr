// Llamadas a Xandart. Un error trae el mensaje que manda el servidor (ya en español).
export async function api<T = unknown>(ruta: string, opciones: { metodo?: string; cuerpo?: unknown } = {}): Promise<T> {
  const r = await fetch(ruta, {
    method: opciones.metodo ?? (opciones.cuerpo !== undefined ? 'POST' : 'GET'),
    headers: { 'Content-Type': 'application/json' },
    body: opciones.cuerpo !== undefined ? JSON.stringify(opciones.cuerpo) : undefined,
  });
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error((datos as { detail?: string }).detail || `Error ${r.status}`);
  return datos as T;
}

export const miles = (n: number) => Math.round(n).toLocaleString('es-CO');

export interface Cuenta {
  gasto_mes_usd: number;
  usuario: { email: string; nombre: string; rol: string; a_costo: boolean; admin: boolean };
  espacio: { id: string; nombre: string };
  saldo: { creditos: number; usd: number; minutos: number; bajo: boolean };
}

export interface Ref { id: string; clave: string; nombre: string }
export interface Canal { id: string; clave: string; nombre: string; formato: Ref | null; videos: number }
export interface Formato {
  id: string; clave: string; nombre: string; descripcion: string; publico: boolean;
  datos: { duraciones_min?: number[]; duracion_min?: number; idea_ejemplo?: string; relacion_aspecto?: string };
}

export interface Trabajo { paso: string; progreso: number; mensaje: string; activo: boolean; error: string | null }
export interface VideoLista {
  slug: string; titulo: string; minutos: number; canal: string; estado: string;
  pasos: Record<string, string>; portada: string | null; video: string | null; trabajo: Trabajo | null;
}
export interface Escena { id: number; seccion: string; narracion: string; accion: string; imagen: string | null }
export interface VideoDetalle {
  slug: string; titulo: string; minutos: number; pasos: Record<string, string>; costo: string;
  escenas: Escena[]; video: string | null; trabajo: (Trabajo & { segundos: number }) | null;
}

export interface Cotizacion {
  creditos: number; usd: number; precio_cliente: { creditos: number; usd: number };
  a_costo: boolean; alcanza: boolean; saldo: number;
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
