"""Catálogo de piezas para que Claude arme las escenas de El Calvo Explica sin ver el código.

Cada pieza: qué es, qué «estado» acepta, dónde queda su ancla y un tamaño que se ve bien en 1920x1080.
Si una pieza nueva se dibuja (calma/piezas*.py), se agrega aquí con su descripción.
"""
from __future__ import annotations

from ..calma.personaje import CARAS, CARAS_NUEVAS, OJOS, OJOS_NUEVOS, POSES

POSES_TXT = ", ".join(p for p in POSES)
CARAS_TXT = ", ".join(CARAS + CARAS_NUEVAS)
OJOS_TXT = ", ".join(OJOS + OJOS_NUEVOS)

CATALOGO: dict[str, str] = {
    # personaje y personas
    "personaje": f"El Calvo (protagonista). Ancla en los PIES. Tamaño 1.1-1.3 → mide ~600-700 px de alto: ponlo con "
                 f"y≈990 (pies abajo). estado: pose ({POSES_TXT}); gesto ({CARAS_TXT}); ojos ({OJOS_TXT}). "
                 "Poses útiles: tablero (señala hacia arriba a la derecha), senalando_contento (señala a la derecha), "
                 "pensando, confundido (con signos ?), hombros, sorprendido, aliviado, idea (con bombillo), rechazo, "
                 "asustado (brazos arriba; también sirve para colgarse de una rama), corriendo, sentado, acostado (en "
                 "una cama, la pieza ya trae la cama).",
    "vecino": "Otra persona igual al Calvo pero gris y sin mochila. Mismo estado que personaje. Ancla en los pies.",
    "gente": "Tres personas grises (un grupo, «todo el mundo»). Ancla abajo al centro, tamaño 1.0, y≈900-980.",
    "fila_personas": "Fila de personas grises; estado {cuantas: 5|7|10, destacada: índice en rojo}. Para «una de cada N». "
                     "Ancla abajo; y≈650-700, tamaño 1.0-1.5.",
    "bebe": "Bebé recién nacido envuelto; estado {agarra: true} = su manita aprieta un dedo amarillo. Centro.",
    # texto y signos
    "texto": "Texto en mayúsculas sin caja. estado {texto, color: negro|rojo}. Negro = etiqueta; rojo = palabra clave. "
             "Tamaño 0.8-1.3. Máximo ~22 caracteres por texto. Centro en (x,y).",
    "titulo_tema": "Título grande con una palabra en rojo. estado {texto, rojo: 'PALABRA EN MAYÚSCULAS'}.",
    "rotulo": "Texto en una caja con borde. estado {texto, color: negro|rojo|verde|amarillo}. Para algo muy importante.",
    "x_roja": "X roja grande (mal, no, falso). Tamaño 0.5-1.0. Entra con movimiento dibujar.",
    "chulo": "Chulo verde (bien, sí, correcto). Tamaño 0.6-1.0. Entra con dibujar.",
    "flecha": "Flecha curva que apunta a la DERECHA (gírala con rotacion: 90 = abajo, 180 = izquierda, -90 = arriba). "
              "estado {color: rojo|negro, curva: 0-0.4}. Entra con dibujar.",
    "circulo_rojo": "Óvalo rojo a mano para resaltar algo. estado {ancho, alto} en px. Entra con dibujar.",
    "corchete": "Corchete rojo para resaltar. estado {alto}. Entra con dibujar.",
    "numero": "Número grande dentro de un círculo amarillo. estado {valor: '3'}.",
    "barra": "Barra que se llena. estado {etiqueta, color: rojo|verde|amarillo|gris, relleno: 0-1}; muévela con "
             "llenar_barra. Ancho ~620 px.",
    "grafica_barras": "Gráfica de barras grises sin números (algo que varía). estado {destacada: índice en rojo}.",
    "cronometro": "Cronómetro. Gira su aguja con {tipo: girar, velocidad: 540, parte: aguja}.",
    "calendario": "Hoja de calendario. estado {texto: 'HOY'}.",
    "documento": "Hoja con título, renglones y sello (guía, estudio). estado {titulo: 'ESTUDIO'} (máx. 7 letras).",
    "tablero": "Tablero blanco vacío con patas (≈750 px de ancho a tamaño 1.45). Encima se ponen títulos o textos.",
    "lineas_movimiento": "Rayitas alrededor de algo que se sacude. Centro. Entra con dibujar.",
    "ondas": "Ondas de sonido o señal hacia la derecha. estado {color: rojo|negro}. Entra con dibujar.",
    # cuerpo
    "muneca": "Mano amarilla en primer plano con la muñeca abajo. estado {dedos: abierta|pinza, tendon: true}. "
              "Grande: tamaño 0.8-1.0 ocupa casi todo el alto; centro y≈600.",
    "oreja": "Oreja de perfil. estado {bulto: true (piquito arriba), punta: true (oreja de animal)}.",
    "ojo": "Ojo de cerca con el pliegue rosado en la esquina de adentro (izquierda). estado {animal: true} = tercer "
           "párpado gris cruzando el ojo.",
    "boca": "Fila de muelas de abajo. estado {grande: true (mandíbula larga), torcida: true, resaltar: true}.",
    "columna": "Columna de perfil con el coxis abajo. estado {resaltar: true (coxis en rojo)}. Alta (~860 px a tamaño 1).",
    "embrion": "Embrión simple. estado {cola: true|false}.",
    "nariz": "Cabeza de perfil mirando a la derecha. estado {sensor: true (punto amarillo en la nariz), "
             "desconectado: true (cable roto hacia el cerebro)}.",
    "intestino": "Intestino (tubo rosado) con el apéndice abajo a la izquierda. estado {resaltar, bacterias}.",
    "piel": "Pedazo de piel con pelitos. estado {parados: true (piel de gallina)}.",
    "musculo": "Brazo doblado mostrando el músculo. estado {relajado: true}.",
    "pierna": "Pierna de lado con el pie a la derecha. Ancla en el pie (abajo).",
    "cerebro": "Cerebro rosado. estado {despierta: true (una parte amarilla)}.",
    "corazon": "Corazón rojo.",
    "torso": "Silueta neutra de un torso gris.",
    "vena": "Corte de piel con un vaso de sangre rojo.",
    "gotas": "Tres gotas rojas.",
    "muneca_brazo": "",
    # animales y cosas
    "gato": "Cabeza de gato gris. estado {giro_orejas: grados, erizado: true, oliendo: true (boca entreabierta)}.",
    "rama": "Rama de árbol con hojas (trepar, colgarse). Ancho ~900 px a tamaño 1.",
    "mesa": "Borde de una mesa vista de frente.",
    "casa": "Casa simple (hogar, refugio).",
    "cafe": "Taza de café humeante.",
    "zzz": "Zzz (sueño, cansancio).",
    "estres": "Nube gris con rayo (estrés, preocupación).",
    "nieve": "Copos de nieve (frío).",
    "escalon": "Escalera a la que le falta el último escalón.",
    "rayo": "Rayo amarillo (señal, energía). estado {color: rojo}.",
    "bacterias": "Grupito de bacterias verdes con carita.",
    "plano": "Plano cuadriculado con la silueta de una persona («el mismo plano»).",
    "cable": "Enchufe desconectado del tomacorriente.",
    "cordon": "Un tendón suelto como un cordón. Entra con dibujar.",
    "dedos": "Mano amarilla pinzando con dos dedos (apretar). La punta de los dedos queda en (x,y).",
    "brazo": "Brazo amarillo que entra desde la derecha; la mano queda en (x,y).",
    "pinzas": "Pinzas grises; la punta en (x,y).",
    "garrapata": "Garrapata vista de arriba. estado {variante: normal|llena|irritada|apretada}.",
}
CATALOGO.pop("muneca_brazo")

MOVIMIENTOS = (
    "aparecer (por defecto; rebote suave), deslizar {desde: [x,y]} (entra desde un punto) o {hasta: [x,y]} "
    "(se va), dibujar (para flechas, X, chulo, óvalos, corchetes, cordón, ondas), crecer {hasta: 1.1}, "
    "girar {grados} o {velocidad, parte}, llenar_barra {desde, hasta}, cambiar_pose {estado: {...}} (cambia pose, "
    "gesto, ojos o cualquier estado al decir la palabra), temblor {fuerza: 6-16}, desaparecer. "
    "Cada movimiento puede llevar «palabra» (empieza cuando la voz la dice), «retraso» y «duracion»."
)


def texto_catalogo() -> str:
    return "\n".join(f"- {k}: {v}" for k, v in CATALOGO.items())
