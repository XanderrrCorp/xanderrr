"""(Paso C) Quién puede usar cada dirección de Xandart. TODO CERRADO POR DEFECTO: una dirección sin regla aquí es solo
del dueño (owner). tests/test_permisos_rutas.py falla si aparece una dirección nueva sin regla decidida.

Niveles:
- «libre»:  sin sesión (la puerta de acceso.py decide qué pasa sin sesión; aquí solo se anota).
- «sesion»: cualquiera que entró (beta, admin y dueño).
- «admin»:  administración (admin y dueño).
- «owner»:  solo el dueño: sus módulos privados (Tracy, El Calvo, Calma, cola), sus plantillas y fórmulas, las
            claves y ajustes del PC, la biblioteca de sonidos, liberar espacio y las copias de seguridad.

(22-10) Las rutas de videos («sesion») todavía muestran la carpeta de videos de siempre: el Paso D las separa por
cuenta. Hasta entonces no se invita a nadie (y nadie de afuera llega: Xandart solo abre en este PC).
"""
from __future__ import annotations

import re

from .modelos import ROL_ADMIN, ROL_OWNER

LIBRE, SESION, ADMIN, OWNER = "libre", "sesion", "admin", "owner"
TODOS = "*"

# (métodos, plantilla de la ruta, nivel). Gana la PRIMERA que coincide: lo específico va antes que lo general.
REGLAS: list[tuple[str, str, str]] = [
    # --- la página y entrar
    ("GET", "/app", LIBRE), ("GET", "/app/{ruta:path}", LIBRE),     # menos tus pantallas privadas: ver PRIVADAS_APP
    ("GET", "/web/{nombre}", SESION),                                  # archivos de las páginas viejas
    ("GET", "/api/version", LIBRE), ("POST", "/api/apagar", OWNER),
    ("GET", "/api/v2/sesion", LIBRE), ("POST", "/api/v2/entrar", LIBRE), ("POST", "/api/v2/salir", LIBRE),
    ("POST", "/api/v2/crear-clave-dueno", LIBRE), ("POST", "/api/v2/cambiar-clave", SESION),
    ("GET", "/", OWNER),                      # Ajustes de siempre: claves, proveedores, Google
    ("GET", "/admin", ADMIN),

    # --- cuenta, créditos, canales y recursos (cada uno los suyos; lo privado del dueño ya lo filtra api.py)
    ("GET", "/api/v2/cuenta", SESION), ("GET", "/api/v2/precios", SESION), ("POST", "/api/v2/cotizar", SESION),
    ("GET", "/api/v2/creditos/historial", SESION), ("POST", "/api/v2/pedidos", SESION),
    ("GET,POST", "/api/v2/canales", SESION), ("PUT", "/api/v2/canales/{canal_id}/ajustes", SESION),
    ("GET", "/api/v2/recursos/{tipo}", SESION), ("POST", "/api/v2/recursos/{tipo}/{recurso_id}/duplicar", SESION),
    ("GET", "/api/v2/videos", SESION),
    ("GET", "/api/v2/avisos", SESION), ("POST", "/api/v2/avisos/leidos", SESION),
    ("POST", "/api/v2/reportes", SESION),
    ("GET", "/api/v2/estudio", OWNER),
    ("GET", "/api/v2/respaldo", OWNER), ("POST", "/api/v2/respaldo/visto", OWNER),
    ("GET", "/api/v2/estado-local", OWNER),
    # personajes: cada espacio los suyos (api_personajes revisa que sean de quien pide)
    ("GET,POST", "/api/v2/personajes", SESION), ("GET,PUT", "/api/v2/personajes/{personaje_id}", SESION),
    ("GET", "/api/v2/personajes/{personaje_id}/archivos/{carpeta}/{archivo}", SESION),
    ("POST", "/api/v2/personajes/{personaje_id}/{accion}", SESION),

    # --- administración
    ("GET,POST", "/api/v2/admin/copias", OWNER),
    ("GET,POST", "/api/v2/admin/usuarios", ADMIN),
    ("POST", "/api/v2/admin/usuarios/{usuario_id}/{accion}", ADMIN),
    ("GET", "/api/v2/admin/resumen", ADMIN), ("POST", "/api/v2/admin/creditos", ADMIN),
    ("POST", "/api/v2/admin/correo/prueba", ADMIN),
    ("PUT", "/api/v2/admin/{que}/{clave}", ADMIN),         # precios, planes, paquetes, ajustes, proveedores

    # --- hacer un video (el camino principal)
    ("POST", "/api/videos", SESION),
    ("GET", "/api/videos/{slug}", SESION),
    ("POST", "/api/videos/{slug}/guion", SESION), ("POST", "/api/videos/{slug}/imagenes", SESION),
    ("POST", "/api/videos/{slug}/prueba", SESION), ("POST", "/api/videos/{slug}/video", SESION),
    ("POST", "/api/videos/{slug}/ajustar-imagenes", SESION), ("POST", "/api/videos/{slug}/usar-las-que-hay", SESION),
    ("POST", "/api/videos/{slug}/short", SESION),
    ("PUT", "/api/videos/{slug}/escenas/{escena_id}", SESION),
    ("POST", "/api/videos/{slug}/escenas/{escena_id}/regenerar", SESION),
    ("POST", "/api/videos/{slug}/escenas/{escena_id}/voz", SESION),
    ("POST", "/api/videos/{slug}/escenas/{escena_id}/animar", SESION),   # imagen → video, con su costo a la vista
    ("POST", "/api/videos/{slug}/revisar", OWNER),                        # usa tu plan de Claude
    ("GET", "/api/videos/{slug}/editor", SESION),
    ("PUT", "/api/videos/{slug}/editor/escenas/{escena_id}/{que}", SESION),
    ("DELETE", "/api/videos/{slug}/editor/escenas/{escena_id}/{que}", SESION),
    ("PUT", "/api/videos/{slug}/editor/{que}", SESION),                   # música, efectos, recortes
    ("POST", "/api/videos/{slug}/editor/musica/subir", SESION),
    # miniaturas de hoy = tus plantillas (escala 2x3, texto + retrato); la genérica para beta llega en el Bloque 2
    ("GET,PUT", "/api/videos/{slug}/miniatura", OWNER),
    ("GET,POST,PUT", "/api/videos/{slug}/miniatura/{resto:path}", OWNER),
    ("GET", "/archivos/{slug}/{ruta:path}", SESION),

    # --- solo el dueño: importar, plantillas de canal, ajustes del PC, sonidos, espacio, módulos privados
    ("POST", "/api/importar", OWNER),
    (TODOS, "/api/canales/{resto:path}", OWNER), ("GET", "/canales/{resto:path}", OWNER),
    ("POST", "/api/miniaturas/canales", OWNER),
    ("GET", "/api/estado", OWNER), ("POST", "/api/claves", OWNER), ("POST", "/api/probar/{servicio}", OWNER),
    ("GET,POST", "/api/proveedor-imagenes", OWNER), ("GET,POST,DELETE", "/api/google-cuenta", OWNER),
    ("POST", "/api/imagenes-lotes", OWNER), ("POST", "/api/claude/sesion", OWNER),
    ("POST", "/api/abrir-carpeta", OWNER),
    (TODOS, "/api/biblioteca", OWNER), (TODOS, "/api/biblioteca/{resto:path}", OWNER),
    (TODOS, "/api/espacio", OWNER), (TODOS, "/api/espacio/{resto:path}", OWNER),
    (TODOS, "/api/tracy", OWNER), (TODOS, "/api/tracy/{resto:path}", OWNER),
    (TODOS, "/api/calma", OWNER), (TODOS, "/api/calma/{resto:path}", OWNER),
    (TODOS, "/api/explica", OWNER), (TODOS, "/api/explica/{resto:path}", OWNER),
    (TODOS, "/api/cola", OWNER), (TODOS, "/api/cola/{resto:path}", OWNER),
]


# Las pantallas de tus módulos privados van en archivos aparte de la página (React.lazy): solo te los entrega a ti
PRIVADAS_APP = re.compile(r"^/app/assets/(Tracy|TracyVideo|Calma|Explica|ExplicaNuevo|Cola)-[^/]+$")


def _patron(plantilla: str) -> re.Pattern:
    partes = re.split(r"(\{[^}]+\})", plantilla)
    rx = "".join(("(.+)" if p.endswith(":path}") else "([^/]+)") if p.startswith("{") else re.escape(p)
                 for p in partes)
    return re.compile(f"^{rx}$")


_COMPILADAS = [(TODOS if m == TODOS else frozenset(m.split(",")), _patron(p), n) for m, p, n in REGLAS]


def regla(metodo: str, ruta: str) -> str | None:
    """El nivel de la primera regla que coincide, o None si no hay (entonces vale «owner»)."""
    metodo = "GET" if metodo == "HEAD" else metodo
    if PRIVADAS_APP.match(ruta):
        return OWNER
    for metodos, rx, nivel in _COMPILADAS:
        if (metodos == TODOS or metodo in metodos) and rx.match(ruta):
            return nivel
    return None


def nivel(metodo: str, ruta: str) -> str:
    return regla(metodo, ruta) or OWNER


def permitido(rol: str, nivel_ruta: str) -> bool:
    if nivel_ruta in (LIBRE, SESION):
        return True
    if nivel_ruta == ADMIN:
        return rol in (ROL_OWNER, ROL_ADMIN)
    return rol == ROL_OWNER
