"""Contratos de datos del Estudio (sección 3 y 12 de la especificación).

Todo lo que depende del estilo (tipos de escena, modos de montaje, plantillas)
se valida contra el `estilo.json` elegido, nunca contra listas fijas del código.
Lo que sí es fijo por especificación: intenciones (4.1) y catálogo de efectos (6).
"""
from __future__ import annotations

import random
import re
import unicodedata
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

INTENCIONES = (
    "gancho", "pregunta_al_espectador", "giro", "revelacion", "dato_impactante",
    "explicacion", "comparacion", "tension_creciente", "amenaza", "alivio", "humor",
    "consejo_practico", "advertencia", "llamado_accion", "transicion_de_seccion", "cierre",
)
Intencion = Literal[INTENCIONES]  # type: ignore[valid-type]

EFECTOS = (
    "zoom_lento", "alejamiento_lento", "paneo_lento", "zoom_golpe", "corte", "corte_seco",
    "fundido_corto", "destello", "destello_rojo", "pixelar", "revelar_pixelado",
    "entrada_rebote", "temblor_leve", "tinte_rojo", "oscurecer_fondo",
    "tira_deslizar_a_nivel", "lado_a_lado", "flecha", "circulo_rojo", "icono_advertencia",
    # cambio de encuadre a mitad de un plano largo (cuenta como cambio visual real, 4.3)
    "reencuadre",
    # ráfaga de acercamientos cortos al ritmo de un latido: solo en tension_creciente
    "rafaga",
    # signos de pregunta que aparecen con rebote cuando la voz le pregunta algo al espectador
    "signos_pregunta",
    # corte de ~2 s al presentador reaccionando (la voz sigue)
    "reaccion_presentador",
    # etiqueta con la palabra clave de la escena, que entra con un pop
    "etiqueta",
    # círculo con el detalle ampliado, unido con una línea al lugar exacto
    "lupa",
    # lo REAL (Pexels, verificado): foto en marco rojo con la mascota señalando, o video a pantalla completa
    "foto_real", "video_real",
    # entradas del objeto al cortar (sale de abajo o de un lado con rebote) y vaivén suave mientras está
    "entrada_abajo", "entrada_lado", "vaiven",
    # escala de peligro 0–10 a pantalla completa cuando se presenta un nivel (dibujada con código)
    "escala_peligro",
    # dato clave a un lado (ícono ✕/✓/⚠ y texto grande, «No muerde») con flecha curva desde el objeto
    "dato",
    # (03-10, como la competencia) pila de fotos que crece: cada foto nueva se desliza encima de la anterior
    "pila_fotos",
    # tarjeta de presentación de cada especie de la lista («1- Nombre» + la imagen en marco blanco)
    "presentacion_especie",
    # término técnico solo, grande, a pantalla completa sobre fondo oscuro («"cantaridina"»)
    "palabra_completa",
    # rótulos a mano (tiza) sobre la pizarra, con su flechita, y la palabra arriba con flecha curva
    "rotulos",
    # salto de tiempo en una mini historia del personaje («Unas horas después»)
    "rotulo_tiempo",
    # detrás del recorte, una foto REAL desenfocada del lugar del que habla la voz (en vez del papel)
    "fondo_lugar",
    # el personaje recortado en el mismo plano que el animal, señalándolo desde el otro lado
    "personaje_al_lado",
    # tarjeta de capítulo al empezar cada parte de la historia («CAPÍTULO 2 · El río que no se cruza»)
    "capitulo",
    # bordes oscurecidos de cine sobre las escenas a pantalla completa
    "vineta",
)
# "sfx" no es un efecto visual, pero se sugiere en la misma lista (ver 3.1).
EFECTOS_SUGERIBLES = EFECTOS + ("sfx",)


class Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- estilo.json

class TipoEscena(Modelo):
    id: str
    descripcion: str = ""
    plantilla_prompt: str
    quitar_fondo: bool
    modo_montaje: str


class FondoMontaje(Modelo):
    tipo: Literal["color", "textura", "cuadricula"]   # cuadricula: hoja blanca cuadriculada y un poco arrugada
    valor: str


class TextoTira(Modelo):
    formato: str = "Nivel {n}"
    tamano: int = Field(96, gt=8)
    color: str = "#FFFFFF"
    contorno_color: str = "#000000"
    contorno_grosor: int = Field(8, ge=0)
    fuentes: list[str] = []          # rutas candidatas, en orden (Windows, Linux, macOS)


class FondoTira(Modelo):
    tipo: Literal["niebla", "color", "transparente"] = "niebla"
    color_a: str = "#060D18"          # lo más oscuro
    color_b: str = "#1D3B5E"          # la niebla
    semilla: int = 7


class TiraNiveles(Modelo):
    """Diseño de la tira de niveles (sección 15). Todo en píxeles del lienzo."""
    tarjeta_ancho: int = Field(820, gt=0)
    tarjeta_alto: int = Field(560, gt=0)
    radio: int = Field(40, ge=0)
    borde_color: str = "#FFFFFF"
    borde_grosor: int = Field(8, ge=0)
    relleno_color: str = "#B9B3A8"   # piedra gris
    relleno_ruido: float = Field(0.06, ge=0, le=0.5)
    alto_lienzo: int = Field(1080, gt=0)
    separacion: int = Field(120, ge=0)
    y_tarjeta: int = Field(260, ge=0)
    sujeto_ancho: float = Field(0.8, gt=0, le=1)
    sombra_sujeto: bool = True
    drama_hacia_derecha: float = Field(0.35, ge=0, le=1)
    brillo_villano: str = "#FF2A2A"
    brillo_radio: int = Field(46, ge=0)
    pixel_bloque: int = Field(40, gt=1)
    texto: TextoTira = TextoTira()
    fondo: FondoTira = FondoTira()


class Subtitulos(Modelo):
    estilo: str
    posicion: str


class PoseCanal(Modelo):
    id: str
    descripcion: str = Field(description="Qué hace el personaje (en inglés, va al prompt)")
    uso: str = Field("", description="Cuándo se usa en el video")
    mira_a: Literal["derecha", "izquierda", "frente"] = "frente"


class Presentador(Modelo):
    nombre_canal: str
    logo: str = Field(description="Ruta del logo dentro de assets/ del estilo")
    persona: str = Field(description="Descripción fija de la persona inventada (en inglés)")
    escenario: str = Field(description="Descripción fija del lugar (en inglés)")
    poses: list[PoseCanal] = []
    # intención de la escena -> pose con la que reacciona; solo aparece en esas intenciones
    reacciones: dict[str, str] = {}
    duracion_reaccion_seg: float = Field(2.0, gt=0.5, le=4)
    separacion_minima_seg: float = Field(40, ge=5)
    maximo_por_video: int = Field(8, ge=0)
    maximo_por_pose: int = Field(2, ge=1)       # la misma reacción repetida se ve mecánica
    # reacción -> efecto de sonido que la acompaña (golpe de terror, nota de piano de miedo…)
    sonidos: dict[str, str] = {}
    # YouTube pide marcar «contenido alterado o sintético» cuando aparece una persona realista hecha con IA
    requiere_divulgacion_contenido_sintetico: bool = True


class Estilo(Modelo):
    id: str
    nombre: str
    descripcion: str
    miniatura: str | None = None
    con_personaje: bool | Literal["opcional"]
    bloque_estilo: str
    personaje_por_defecto: str | None = None
    tipos_de_escena: list[TipoEscena] = Field(min_length=1)
    mezcla_recomendada: dict[str, float]
    fondo_montaje: FondoMontaje
    modos_de_montaje_permitidos: list[str] = Field(min_length=1)
    gramatica_edicion: str
    perfil_edicion: str
    movimiento_maximo: float = Field(0.05, gt=0, le=0.05)
    subtitulos: Subtitulos
    musica_por_defecto: list[str] = []
    costo_relativo: float = Field(1.0, gt=0)
    # Para el estimador (sección 2): proporción de escenas que llevan imagen nueva.
    proporcion_imagenes_unicas: float = Field(0.6, gt=0, le=1)
    proporcion_minima_unicas: float = Field(0.4, gt=0, le=1)
    imagenes_fijas_por_video: int = Field(0, ge=0)
    # Plantillas de los assets reutilizables (personaje base, etc.) por tipo de asset.
    plantillas_assets: dict[str, str] = {}
    tira_niveles: TiraNiveles | None = None
    # Cómo dibuja el motor cada modo de montaje del estilo (sección 6).
    # «pizarra»: el dibujo de tiza va sobre una pizarra con marco de madera dibujada con código
    comportamiento_montaje: dict[str, Literal["recorte", "recuadro", "pantalla_completa", "pizarra"]] = {}
    # Poses del personaje del canal: se generan UNA vez y todos los videos las reutilizan
    # True: el villano va pixelado en pantalla hasta su revelación. Es solo visual: la voz nunca
    # dice que está pixelado (al dueño no le gustó oírlo en el guion)
    ocultar_villano: bool = True
    # Logo del canal fijo abajo a la derecha en todo el video (ruta dentro de la carpeta del estilo)
    marca_agua: str | None = None
    # «negro»: títulos de arriba en negro sin borde (con triángulo rojo en amenazas), como en la hoja
    # cuadriculada de la competencia; «contorno»: blancos con borde negro
    titulo: Literal["contorno", "negro"] = "contorno"
    # tipos de escena que solo muestran al animal: se pueden cambiar por una foto o video real de Pexels
    tipos_reemplazables_por_foto_real: list[str] = []
    poses_canal: list["PoseCanal"] = []
    # Presentador realista (persona INVENTADA) para reacciones cortas en giro, revelación y humor
    presentador: "Presentador | None" = None
    # miniaturas: cuánto se exagera cada animal según su peligro (villano, peligroso, neutral, inofensivo)
    miniatura_expresiones: dict[str, str] = {}

    @model_validator(mode="before")
    @classmethod
    def _sin_comentarios(cls, datos):
        # las claves que empiezan por "_" son notas para humanos dentro del JSON
        if isinstance(datos, dict):
            return {k: v for k, v in datos.items() if not str(k).startswith("_")}
        return datos

    @property
    def ids_tipos(self) -> set[str]:
        return {t.id for t in self.tipos_de_escena}

    def tipo(self, id_tipo: str) -> TipoEscena | None:
        return next((t for t in self.tipos_de_escena if t.id == id_tipo), None)

    @model_validator(mode="after")
    def _coherencia(self) -> "Estilo":
        ids = [t.id for t in self.tipos_de_escena]
        if len(ids) != len(set(ids)):
            raise ValueError("tipos_de_escena tiene ids repetidos")
        for t in self.tipos_de_escena:
            if t.modo_montaje not in self.modos_de_montaje_permitidos:
                raise ValueError(f"tipo '{t.id}' usa modo '{t.modo_montaje}' no permitido por el estilo")
            if "no text" not in t.plantilla_prompt.lower():
                raise ValueError(f"la plantilla de '{t.id}' debe pedir 'no text' (regla 11)")
        for k, plantilla in self.plantillas_assets.items():
            if "no text" not in plantilla.lower():
                raise ValueError(f"la plantilla del asset '{k}' debe pedir 'no text' (regla 11)")
        sin_modo = set(self.comportamiento_montaje) - set(self.modos_de_montaje_permitidos)
        if sin_modo:
            raise ValueError(f"comportamiento_montaje usa modos no permitidos: {sorted(sin_modo)}")
        desconocidos = set(self.mezcla_recomendada) - set(ids)
        if desconocidos:
            raise ValueError(f"mezcla_recomendada usa tipos inexistentes: {sorted(desconocidos)}")
        suma = sum(self.mezcla_recomendada.values())
        if abs(suma - 1.0) > 0.01:
            raise ValueError(f"mezcla_recomendada debe sumar 1 (suma {suma:.2f})")
        if self.proporcion_minima_unicas > self.proporcion_imagenes_unicas:
            raise ValueError("proporcion_minima_unicas no puede superar proporcion_imagenes_unicas")
        if self.con_personaje is True and not self.personaje_por_defecto:
            raise ValueError("un estilo con personaje necesita personaje_por_defecto")
        return self


# -------------------------------------------------------- perfil_edicion.json

class PerfilEdicion(Modelo):
    fuente: list[str] = []
    segundos_promedio_por_imagen: float = Field(gt=0)
    interrupcion_de_patron_cada_seg: float = Field(gt=0)
    efectos_por_minuto: float = Field(ge=0)
    sfx_por_minuto: float = Field(ge=0)
    cambios_de_musica: str
    texto_en_pantalla_por_minuto: float = Field(ge=0)
    densidad_primeros_30s: Literal["baja", "media", "alta"]
    notas: str = ""
    # 14.1 · sensación humana
    variacion_minima_duracion: float = Field(0.3, ge=0, description="Coeficiente de variación mínimo de la duración de escenas")
    respiros_max_por_minuto: float = Field(1, ge=0)
    uso_maximo_por_recurso: float = Field(0.35, gt=0, le=1, description="Fracción máxima de escenas con una misma transición, movimiento o efecto")
    recursos_exentos_de_uso_maximo: list[str] = Field(
        default=["corte"], description="Recursos neutros que no cuentan para uso_maximo_por_recurso")
    # Variación observada en el video de referencia (desviación estándar o coeficiente de
    # variación por métrica), no solo promedios. Ej.: {"cv_duracion_escenas": 0.42}
    variacion_referencia: dict[str, float] = {}
    # «clasica»: la edición de los peces del Amazonas (la favorita del dueño): mucho movimiento, sin música,
    # pops, whoosh y cámara. «calmada»: menos movimiento, escenas a pantalla completa y música suave.
    estilo_edicion: Literal["clasica", "calmada"] = "clasica"
    # «sin_vaiven»: la imagen no se mece sola en cada escena (zooms, entradas y ráfagas siguen igual)
    # «deslizar» (Peligro Tropical): nada se mece ni tiembla; casi todo entra deslizándose de lado con
    # swoosh y se acerca despacio; flechas curvas que se mueven y elementos que aparecen uno tras otro
    # «historia» (Paradoja Sapiens): como «deslizar», pero casi todo a pantalla completa con zoom tipo
    # documental (acercar, alejar, paneo), fundidos suaves, tarjetas de capítulo y viñeta de cine
    movimiento: Literal["normal", "sin_vaiven", "deslizar", "historia"] = "normal"


# ---------------------------------------------------------- perfil_canal.json

class Personaje(Modelo):
    bloqueo: str = Field(description="Descripción literal que se copia igual en cada prompt")
    imagen_referencia: str | None = None


class PerfilCanal(Modelo):
    id: str
    nombre: str
    idioma: str = "es"
    voz: dict[str, Any] = {}
    estilo: str
    personaje: Personaje | None = None
    paleta: list[str] = []
    tipografias: list[str] = []
    efectos_preferidos: list[str] = []
    efectos_prohibidos: list[str] = []
    duracion_objetivo_seg: tuple[float, float] = (480, 660)
    perfil_edicion: str | None = None
    musica_por_animo: dict[str, list[str]] = {}

    @field_validator("efectos_preferidos", "efectos_prohibidos")
    @classmethod
    def _efectos_validos(cls, v: list[str]) -> list[str]:
        malos = [e for e in v if e not in EFECTOS]
        if malos:
            raise ValueError(f"efectos fuera del catálogo: {malos}")
        return v


# ------------------------------------------------------- escenas.json (v2)

class Tiempo(Modelo):
    estimado_inicio: float | None = Field(None, ge=0)
    estimado_duracion: float | None = Field(None, gt=0)
    real_inicio: float | None = Field(None, ge=0)
    real_fin: float | None = Field(None, ge=0)
    alineacion_confiable: bool | None = None

    @model_validator(mode="after")
    def _orden(self) -> "Tiempo":
        if self.real_inicio is not None and self.real_fin is not None and self.real_fin <= self.real_inicio:
            raise ValueError("real_fin debe ser mayor que real_inicio")
        return self


class Visual(Modelo):
    # solo_edicion: no se genera imagen (animación de la tira, texto en pantalla...)
    accion: Literal["generar", "reusar", "componer", "solo_edicion"]
    tipo: str | None = None
    # Lo que muestra la escena. Va en {descripcion} de la plantilla del estilo.
    prompt: str | None = None
    # true = `prompt` ya es el prompt completo y se envía tal cual (no se pasa por
    # la plantilla). Solo para prompts importados que no encajan en el estilo.
    prompt_literal: bool = False
    archivo: str | None = None
    quitar_fondo: bool = False
    referencias: list[str] = []
    reusar_de: int | str | None = None

    @model_validator(mode="after")
    def _reuso(self) -> "Visual":
        if self.accion == "reusar" and self.reusar_de is None:
            raise ValueError("accion 'reusar' requiere reusar_de")
        if self.accion == "generar" and not self.prompt:
            raise ValueError("accion 'generar' requiere prompt")
        if self.accion == "generar" and not self.tipo:
            raise ValueError("accion 'generar' requiere tipo")
        return self


class EfectoSugerido(BaseModel):
    model_config = ConfigDict(extra="allow")  # parámetros propios de cada efecto
    efecto: str

    @field_validator("efecto")
    @classmethod
    def _en_catalogo(cls, v: str) -> str:
        if v not in EFECTOS_SUGERIBLES:
            raise ValueError(f"efecto '{v}' no está en el catálogo")
        return v


class Escena(Modelo):
    id: int
    seccion: str
    narracion: str = Field(min_length=1)
    intencion: Intencion
    intensidad: int = Field(ge=1, le=5)
    tiempo: Tiempo = Tiempo()
    visual: Visual
    efectos_sugeridos: list[EfectoSugerido] = []
    palabra_clave: str | None = Field(None, description="Palabra más importante de la frase (la marca el Director)")
    pausa_despues_seg: float = Field(0, ge=0, le=3)
    revision_humana: list[str] = Field(default=[], description="Motivos para revisión humana (p. ej. dato médico)")
    notas_edicion: str = ""

    @model_validator(mode="after")
    def _palabra_en_narracion(self) -> "Escena":
        if self.palabra_clave is not None:
            clave = _palabras(self.palabra_clave)
            narr = _palabras(self.narracion)
            n = len(clave)
            if not clave or not any(narr[i:i + n] == clave for i in range(len(narr) - n + 1)):
                raise ValueError(f"escena {self.id}: palabra_clave '{self.palabra_clave}' no aparece en la narración")
        return self


def _normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _palabras(texto: str) -> list[str]:
    return re.findall(r"\w+", _normalizar(texto))


class AssetDef(Modelo):
    id: str
    tipo: str
    nombre: str | None = None
    prompt: str | None = None
    prompt_literal: bool = False
    archivo: str
    quitar_fondo: bool = False


class Nivel(Modelo):
    numero: int = Field(ge=1)
    nombre: str
    asset: str
    villano: bool = False
    peligro: int | None = Field(None, ge=0, le=10)   # escala 0–10 en pantalla; si falta, sale de la posición


class EscenasV2(Modelo):
    version: Literal[2] = 2
    video: str
    canal: str
    estilo: str | None = None
    idioma: str = "es"
    relacion_aspecto: str = "16:9"
    assets: list[AssetDef] = []
    # Formato escala (sección 15): del más inofensivo al más peligroso.
    niveles: list[Nivel] = []
    escenas: list[Escena] = Field(min_length=1)

    @model_validator(mode="after")
    def _referencias(self) -> "EscenasV2":
        ids = [e.id for e in self.escenas]
        if len(ids) != len(set(ids)):
            raise ValueError("escenas con id repetido")
        ids_assets = {a.id for a in self.assets}
        conjunto = set(ids)
        for e in self.escenas:
            r = e.visual.reusar_de
            if r is not None and r not in conjunto and r not in ids_assets:
                raise ValueError(f"escena {e.id}: reusar_de={r!r} no existe")
            for ref in e.visual.referencias:
                if ref not in ids_assets:
                    raise ValueError(f"escena {e.id}: referencia '{ref}' no es un asset declarado")
        if self.niveles:
            if not 4 <= len(self.niveles) <= 8:
                raise ValueError(f"la tira de niveles debe tener entre 4 y 8 niveles (tiene {len(self.niveles)})")
            if [n.numero for n in self.niveles] != list(range(1, len(self.niveles) + 1)):
                raise ValueError("los niveles deben ir numerados 1, 2, 3... en orden")
            if sum(n.villano for n in self.niveles) != 1:
                raise ValueError("la tira de niveles necesita exactamente un villano")
            for n in self.niveles:
                if n.asset not in ids_assets:
                    raise ValueError(f"nivel {n.numero}: el asset '{n.asset}' no está declarado")
        return self

    def errores_contra_estilo(self, estilo: Estilo) -> list[str]:
        """Reglas 12.5: solo tipos de escena del estilo elegido."""
        errores = []
        for e in self.escenas:
            if e.visual.tipo is not None and e.visual.tipo not in estilo.ids_tipos:
                errores.append(f"escena {e.id}: tipo '{e.visual.tipo}' no existe en el estilo '{estilo.id}'")
        return errores


# ------------------------------------------------------------- edl.json

class Movimiento(Modelo):
    tipo: str
    de: float = 1.0
    a: float = 1.0
    # 14.4: nunca velocidad lineal
    curva: Literal["ease_in_out", "ease_in", "ease_out"] = "ease_in_out"
    # Coordenadas normalizadas (0 a 1) del sujeto importante; None = centro
    punto_foco: tuple[float, float] | None = None

    @field_validator("punto_foco")
    @classmethod
    def _normalizado(cls, v):
        if v is not None and not all(0 <= c <= 1 for c in v):
            raise ValueError("punto_foco debe estar en coordenadas normalizadas (0 a 1)")
        return v

    @field_validator("tipo")
    @classmethod
    def _catalogo(cls, v: str) -> str:
        if v not in EFECTOS:
            raise ValueError(f"movimiento '{v}' no está en el catálogo")
        return v


class Tramo(Modelo):
    inicio: float = Field(ge=0)
    fin: float = Field(gt=0)
    razon: str | None = None

    @model_validator(mode="after")
    def _orden(self):
        if self.fin <= self.inicio:
            raise ValueError(f"fin ({self.fin}) debe ser mayor que inicio ({self.inicio})")
        return self


class ClipFondo(Tramo):
    id: str
    tipo: Literal["color", "textura", "cuadricula"]   # cuadricula: hoja blanca cuadriculada y un poco arrugada
    archivo: str | None = None
    valor: str | None = None


class ClipEscena(Tramo):
    id: str
    escena: int
    archivo: str
    modo: str
    movimiento: Movimiento | None = None
    transicion_entrada: str = "corte"
    efectos: list[EfectoSugerido] = []
    reuso_intencional: bool = False
    respiro: bool = False  # 14.2: única excepción a la regla de 4,5 s, hasta 6 s


class Elemento(Tramo):
    id: str
    tipo: str
    valor: str
    posicion: str


class Texto(Tramo):
    id: str
    texto: str
    estilo: str
    posicion: str = "centro"


class Subtitulo(Tramo):
    texto: str
    escena: int | None = None      # de qué escena es (el editor corrige los de una escena)


class PistaVoz(Modelo):
    inicio: float = Field(0, ge=0)
    archivo: str


class ClipMusica(Tramo):
    id: str
    archivo: str                      # ruta dentro de la biblioteca (musica/<animo>/<archivo>)
    volumen: float = Field(0.18, ge=0, le=1)
    ducking: bool = True
    animo: str | None = None
    desde: float = Field(0, ge=0)     # segundo de la pista donde empieza
    # 14.5: la música cae de golpe 0,3 a 0,8 s antes de una revelación y el golpe cae en ese silencio
    caidas: list[tuple[float, float]] = []


class ClipSfx(Modelo):
    id: str
    inicio: float = Field(ge=0)
    archivo: str
    volumen: float = Field(0.7, ge=0, le=1)
    variante: str | None = None
    tono: float = Field(1.0, ge=0.95, le=1.05, description="Factor de ajuste de tono (±5 %)")
    razon: str | None = None
    # 14.7: una subida de tensión termina EXACTAMENTE en el corte o la revelación que anuncia;
    # el motor la coloca para que acabe aquí, sea cual sea el largo del archivo
    termina_en: float | None = None
    tipo: str | None = None
    # solo se usan los últimos (con termina_en) o los primeros segundos del archivo: una ruleta
    # larga se recorta para que sus clics finales caigan justo cuando la tira se detiene
    duracion_max: float | None = Field(None, gt=0)


class Pistas(Modelo):
    fondo: list[ClipFondo] = []
    escenas: list[ClipEscena] = []
    elementos: list[Elemento] = []
    textos: list[Texto] = []
    subtitulos: list[Subtitulo] = []
    voz: list[PistaVoz] = []
    musica: list[ClipMusica] = []
    sfx: list[ClipSfx] = []


class CambioHistorial(Modelo):
    version: int
    autor: str
    cambio: str
    razon: str


class EDL(Modelo):
    version: int = Field(ge=1)
    duracion_total: float = Field(gt=0)
    pistas: Pistas
    audio: dict = {}                     # {"igualar": bool}: igualar el volumen de cada efecto al mezclar
    historial: list[CambioHistorial] = []

    @model_validator(mode="after")
    def _ids_estables(self) -> "EDL":
        vistos: set[str] = set()
        for nombre in ("fondo", "escenas", "elementos", "textos", "musica", "sfx"):
            for item in getattr(self.pistas, nombre):
                if item.id in vistos:
                    raise ValueError(f"id repetido en la EDL: {item.id}")
                vistos.add(item.id)
        return self


# ---------------------------------------------------------- proyecto.json

PASOS = (
    "estratega", "guionista", "director_visual", "assets", "voz_muestra", "voz", "alineador",
    "director_edicion", "validador", "render_preview", "revisor", "editor", "export_final",
)
EstadoPaso = Literal["pendiente", "en_curso", "completo", "error"]


class Paso(Modelo):
    estado: EstadoPaso = "pendiente"
    salida: list[str] = []
    actualizado: str | None = None
    error: str | None = None


class Proyecto(Modelo):
    slug: str
    titulo: str
    canal: str
    estilo: str
    duracion_objetivo_seg: float = Field(gt=0)
    creado: str
    pasos: dict[str, Paso] = Field(default_factory=lambda: {p: Paso() for p in PASOS})
    # 14.4: aleatoriedad controlada, fija por proyecto para que el render sea repetible
    semilla: int = Field(default_factory=lambda: random.randrange(2**31))
    permiso_superar_maximo: bool = False
    notas: list[str] = []
    # se activa si el video usa al presentador realista hecho con IA: al subirlo hay que
    # marcar «contenido alterado o sintético» en YouTube
    requiere_divulgacion_contenido_sintetico: bool = False
    # la mascota sale con un hoodie del animal del tema solo en este video (una imagen extra)
    formula: str | None = None           # estructura del guion (None = escala de peligro, la de siempre)
    disfraz_mascota: bool = False
    disfraz_tema: str | None = None
    # «generated» = imágenes generadas (stickman, mascota…); «stock» = modo Tracy (clip base + stock)
    visual_mode: Literal["generated", "stock"] = "generated"

    @model_validator(mode="after")
    def _pasos_completos(self) -> "Proyecto":
        # Proyectos creados antes de agregar un paso nuevo lo reciben como pendiente.
        for paso in PASOS:
            self.pasos.setdefault(paso, Paso())
        return self
