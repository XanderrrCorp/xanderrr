# Estudio · Buscanichos

Módulo de producción de video (ver la especificación del Estudio). Estado: **Fase 0**.

## Xandart en tu PC (Windows, un clic)

1. Descarga [`instalar/Instalar Xandart.bat`](https://raw.githubusercontent.com/XanderrrCorp/xanderrr/claude/new-session-uq98jd/instalar/Instalar%20Xandart.bat)
   (clic derecho → *Guardar como*) y dale doble clic. Si Windows avisa «protegió su PC»: *Más información → Ejecutar de todas formas*.
2. Instala Python, Xandart y Claude, crea el acceso directo **Xandart** en el escritorio y abre la página.
3. La primera vez, en **⚙ Ajustes**: pega la clave de Together y la de MiniMax, y dale *Iniciar sesión* en Claude.

Los videos salen en `Videos\Xandart`. Para actualizar: menú Inicio → *Actualizar Xandart* (no borra claves ni videos).
Sin instalador: `pip install -e .` y `xandart` (o `python -m estudio.app`) abre la página en http://127.0.0.1:8030.

## Instalación (desarrollo)

```bash
pip install -e ".[dev]"
cp .env.example .env   # claves de API solo aquí
python -m pytest
```

## Uso (Fase 0)

```bash
python -m estudio estilos
python -m estudio estimar --minutos 10 --estilo enciclopedia_mascota
python -m estudio importar-v1 ruta/escenas_v1.json --slug alacranes --canal animales-peligrosos
python -m estudio validar --slug alacranes
python -m estudio estimar --slug alacranes
python -m estudio costos --slug alacranes
```

## Estructura

| Ruta | Contenido |
|---|---|
| `config/costos.json` | TRM, presupuesto, precios por proveedor, modelo de Claude por módulo, consumo estimado |
| `estilos/<id>/estilo.json` | Catálogo de estilos: tipos de escena, plantillas, modos de montaje |
| `gramaticas/`, `perfiles/` | Gramática de edición (4.2) y perfiles de ritmo (3.4) |
| `estudio/esquemas.py` | Contratos: `escenas.json` v2, `edl.json`, perfiles, estilo, proyecto |
| `estudio/costos.py` | Libro de costos (`logs/costos.jsonl`) y freno duro al máximo |
| `estudio/estimador.py` | Estimación previa, degradación (2.4) y mejora (2.5) |
| `estudio/importar_v1.py` | Conversión de `escenas.json` v1 → v2 |
| `estudio/proyecto.py` | Carpeta de proyecto y estado reanudable por paso |
| `proyectos/` | Proyectos locales (fuera de git) |

Ningún tipo de escena, plantilla de prompt ni modo de montaje está escrito en el código: todo se lee del estilo.

## Prueba real de imágenes (Fase 1): 10 escenas de alacranes

En tu PC, con la clave en `.env` (`TOGETHER_API_KEY=...`, o `GEMINI_API_KEY=...` si cambias el proveedor en `config/proveedores.json`):

```bash
pip install -e ".[dev]"
python -m estudio importar-v1 RUTA/escenas.json --slug alacranes --canal animales-peligrosos
python -m estudio generar-imagenes --slug alacranes --primeras 10
```

Al terminar muestra el costo real de la corrida en pesos (con las imágenes de
referencia incluidas, tomado de lo que devuelve la API), el costo medio por imagen
y la proyección para todas las imágenes del video. Deja una hoja de contacto en
`proyectos/alacranes/render/hoja_imagenes.png` y cada llamada en
`proyectos/alacranes/logs/costos.jsonl`.

- Volver a correr el comando no vuelve a pagar lo que ya está hecho.
- Si se llega al máximo de 20.000 COP (o al tope de llamadas del video) se para
  y lo dice; `--permiso` es el permiso explícito para seguir.
- Para ensayar sin gastar: `--proveedor simulado`.
- El proveedor y el modelo se cambian en `config/proveedores.json`; las tarifas,
  en `config/costos.json`.

## De guion a video completo

```bash
python -m estudio generar-imagenes --slug X          # todas las escenas (reanudable, con freno)
python -m estudio generar-imagenes --slug X --niveles  # sujetos de la tira de niveles
python -m estudio armar-tira --slug X                # tira de niveles (sección 15)
python -m estudio generar-voz --slug X               # voz MiniMax + tiempos reales por escena
python -m estudio editar --slug X                    # Director de edición → edl.json + validador
python -m estudio render --slug X                    # MP4 1080p + SRT en proyectos/X/render/
python -m estudio render --slug X --desde 40 --hasta 60 --salida tramo.mp4   # tramo de prueba
```

`direccion.json` (opcional, en la carpeta del proyecto) guarda las decisiones puntuales del director:
la escena de revelación del villano, las zonas a pixelar antes de ella y los textos en pantalla.
