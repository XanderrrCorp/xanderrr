# Estudio · Buscanichos

Módulo de producción de video (ver la especificación del Estudio). Estado: **Fase 0**.

## Instalación

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
