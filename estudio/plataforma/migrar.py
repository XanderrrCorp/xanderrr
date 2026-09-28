"""Convierte una instalación de Xandart de un solo usuario en datos de la cuenta del dueño.

Lo que antes estaba en carpetas del código (estilos/, canales/, perfiles/, config de voz) y
los videos de proyectos/ pasan a ser recursos privados del espacio del dueño, registrados en
la base, igual que los crearía cualquier cliente. Se puede correr las veces que haga falta:
lo ya migrado no se duplica ni se pisa.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import RAIZ, leer_config, leer_json, ruta_proyectos
from . import almacen, contexto, db, precios
from .cuentas import cuenta_local
from .modelos import (Ajuste, Canal, Estilo, FormulaGuion, PerfilEdicion, Personaje, PlantillaMiniatura,
                      Video, Voz)


def _upsert(s: Session, modelo, espacio_id: str | None, clave: str, **campos):
    r = s.scalar(select(modelo).where(modelo.espacio_id.is_(None) if espacio_id is None
                                      else modelo.espacio_id == espacio_id, modelo.clave == clave))
    if r is None:
        r = modelo(espacio_id=espacio_id, clave=clave, **campos)
        s.add(r)
    else:
        for k, v in campos.items():
            if k not in ("origen",):
                setattr(r, k, v)
    s.flush()
    return r


def sembrar_catalogo(s: Session) -> dict[str, int]:
    """Registra en la base el catálogo público que viene con Xandart (carpeta catalogo/)."""
    base = contexto.carpeta_catalogo()
    cuenta = {"formulas": 0, "plantillas": 0, "perfiles": 0, "estilos": 0}
    for f in sorted((base / "formulas").glob("*/formula.json")):
        d = leer_json(f)
        _upsert(s, FormulaGuion, None, f.parent.name, nombre=d["nombre"], descripcion=d.get("descripcion", ""),
                datos=d, origen={"catalogo": True})
        cuenta["formulas"] += 1
    for f in sorted((base / "plantillas_miniatura").glob("*/plantilla.json")):
        d = leer_json(f)
        _upsert(s, PlantillaMiniatura, None, f.parent.name, nombre=d.get("nombre", f.parent.name), datos=d,
                origen={"catalogo": True})
        cuenta["plantillas"] += 1
    for f in sorted((base / "perfiles").glob("*/perfil.json")):
        d = leer_json(f)
        _upsert(s, PerfilEdicion, None, f.parent.name, nombre=f.parent.name.replace("_", " ").capitalize(),
                descripcion=d.get("notas", ""), datos=d, origen={"catalogo": True})
        cuenta["perfiles"] += 1
    for f in sorted((base / "estilos").glob("*/estilo.json")):
        d = leer_json(f)
        _upsert(s, Estilo, None, f.parent.name, nombre=d.get("nombre", f.parent.name),
                descripcion=d.get("descripcion", ""), datos=d, origen={"catalogo": True})
        cuenta["estilos"] += 1
    return cuenta


def _copiar(origen: Path, destino: Path) -> None:
    """Copia la carpeta si el destino no existe todavía (nunca pisa lo del espacio)."""
    if origen.exists() and not destino.exists():
        shutil.copytree(origen, destino)


def migrar_instalacion(raiz: Path = RAIZ, proyectos: Path | None = None) -> dict:
    db.preparar()
    proyectos = proyectos or ruta_proyectos()
    resumen: dict = {"estilos": [], "personajes": [], "plantillas": [], "perfiles": [], "canales": [], "videos": 0}
    with db.sesion() as s:
        precios.sembrar(s)
        resumen["catalogo"] = sembrar_catalogo(s)
        _, espacio = cuenta_local(s)
        E = espacio.id
        raiz_e = almacen.raiz_espacio(E)

        # estilos (con sus assets: mascota, poses, presentador, logo)
        estilos: dict[str, Estilo] = {}
        for f in sorted((raiz / "estilos").glob("*/estilo.json")):
            clave = f.parent.name
            _copiar(f.parent, raiz_e / "estilos" / clave)
            d = leer_json(raiz_e / "estilos" / clave / "estilo.json")
            estilos[clave] = _upsert(s, Estilo, E, clave, nombre=d.get("nombre", clave),
                                     descripcion=d.get("descripcion", ""), datos=d, origen={"migrado_de": str(f.parent)})
            resumen["estilos"].append(clave)

            # personajes que vivían dentro del estilo
            if d.get("personaje_por_defecto"):
                _upsert(s, Personaje, E, f"{clave}_mascota", nombre="Mascota del canal", estilo_id=estilos[clave].id,
                        descripcion=d["personaje_por_defecto"],
                        datos={"tipo": "mascota", "descripcion": d["personaje_por_defecto"], "estilo": clave,
                               "imagen_base": "assets/mascota_base.png", "poses": "assets/poses"})
                resumen["personajes"].append(f"{clave}_mascota")
            pr = d.get("presentador")
            if pr:
                _upsert(s, Personaje, E, f"{clave}_presentador", nombre="Presentador", estilo_id=estilos[clave].id,
                        descripcion=pr.get("persona", ""),
                        datos={"tipo": "presentador", "estilo": clave, "persona": pr.get("persona", ""),
                               "escenario": pr.get("escenario", ""), "poses": "assets/presentador",
                               "clips": "assets/presentador/clips", "reacciones": pr.get("reacciones", {})})
                resumen["personajes"].append(f"{clave}_presentador")

        # perfiles de edición propios (los públicos ya están en el catálogo)
        perfiles: dict[str, PerfilEdicion] = {}
        for f in sorted((raiz / "perfiles").glob("*.json")):
            destino = raiz_e / "perfiles" / f.stem / "perfil.json"
            if not destino.exists():
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(f, destino)
            d = leer_json(destino)
            perfiles[f.stem] = _upsert(s, PerfilEdicion, E, f.stem, nombre=f.stem.replace("_", " ").capitalize(),
                                       descripcion=d.get("notas", ""), datos=d)
            resumen["perfiles"].append(f.stem)

        # plantillas de miniatura por canal (con sus referencias de estilo)
        plantillas: dict[str, PlantillaMiniatura] = {}
        for f in sorted((raiz / "canales").glob("*/miniatura/plantilla.json")):
            canal = f.parent.parent.name
            _copiar(f.parent, raiz_e / "plantillas_miniatura" / canal)
            d = leer_json(raiz_e / "plantillas_miniatura" / canal / "plantilla.json")
            plantillas[canal] = _upsert(s, PlantillaMiniatura, E, canal, nombre=d.get("nombre", canal), datos=d)
            resumen["plantillas"].append(canal)

        # la voz que se usaba para todo
        v = leer_config("proveedores.json").get("voz") or {}
        voz = None
        if v.get("voz_id"):
            voz = _upsert(s, Voz, E, "voz_principal", nombre="Voz principal",
                          descripcion=f"{v.get('proveedor', '')} · {v.get('idioma', '')} · velocidad {v.get('velocidad', 1)}",
                          datos={k: v[k] for k in ("proveedor", "modelo", "voz_id", "idioma", "velocidad") if k in v})

        # canales: los que tienen plantilla y los que usan los videos
        claves_canal = set(plantillas)
        for p in sorted(proyectos.glob("*/proyecto.json")):
            claves_canal.add(leer_json(p).get("canal", ""))
        claves_canal.discard("")
        formula = s.scalar(select(FormulaGuion).where(FormulaGuion.espacio_id.is_(None),
                                                      FormulaGuion.clave == "escala_peligro"))
        canales: dict[str, Canal] = {}
        for clave in sorted(claves_canal):
            usados = [leer_json(p) for p in proyectos.glob("*/proyecto.json") if leer_json(p).get("canal") == clave]
            clave_estilo = usados[-1]["estilo"] if usados else next(iter(estilos), None)
            est = estilos.get(clave_estilo)
            datos_est = est.datos if est else {}
            nombre = (datos_est.get("presentador") or {}).get("nombre_canal") or clave.replace("-", " ").title()
            presentador = s.scalar(select(Personaje).where(Personaje.espacio_id == E,
                                                           Personaje.clave == f"{clave_estilo}_presentador"))
            perfil_clave = Path(datos_est.get("perfil_edicion", "")).stem
            c = s.scalar(select(Canal).where(Canal.espacio_id == E, Canal.clave == clave))
            if c is None:
                c = Canal(espacio_id=E, clave=clave, nombre=nombre)
                s.add(c)
            c.estilo_id = est.id if est else None
            c.personaje_id = presentador.id if presentador else None
            c.voz_id = voz.id if voz else None
            c.formula_id = formula.id if formula else None
            c.plantilla_miniatura_id = plantillas[clave].id if clave in plantillas else None
            c.perfil_edicion_id = perfiles[perfil_clave].id if perfil_clave in perfiles else None
            c.ajustes = {**(c.ajustes or {}), "minutos": 9, "idioma_voz": v.get("idioma", "Spanish")}
            s.flush()
            canales[clave] = c
            resumen["canales"].append(nombre)

        # videos: se registran donde están (no se mueven: siguen funcionando igual)
        for p in sorted(proyectos.glob("*/proyecto.json")):
            d = leer_json(p)
            carpeta = p.parent
            formato = "16:9"
            if (carpeta / "escenas.json").exists():
                formato = leer_json(carpeta / "escenas.json").get("relacion_aspecto", "16:9")
            vid = s.scalar(select(Video).where(Video.espacio_id == E, Video.slug == d["slug"]))
            if vid is None:
                vid = Video(espacio_id=E, slug=d["slug"], titulo=d["titulo"], carpeta=str(carpeta))
                s.add(vid)
            vid.canal_id = canales[d["canal"]].id if d.get("canal") in canales else None
            vid.formato = formato
            vid.estado = "listo" if (carpeta / "render" / "final.mp4").exists() else "en_proceso"
            vid.minutos = round(d.get("duracion_objetivo_seg", 0) / 60, 1) or None
            resumen["videos"] += 1

        marca = s.get(Ajuste, "migracion_local")
        valor = {"fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"), "espacio": E,
                 "resumen": {k: v for k, v in resumen.items() if k != "catalogo"}}
        if marca is None:
            s.add(Ajuste(clave="migracion_local", valor=valor))
        else:
            marca.valor = valor
        resumen["espacio"] = E
    return resumen


def espacio_local() -> str:
    """El espacio del dueño (para fijarlo como espacio actual en modo local)."""
    db.preparar()
    with db.sesion() as s:
        _, e = cuenta_local(s)
        return e.id
