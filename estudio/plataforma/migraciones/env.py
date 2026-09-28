"""Entorno de Alembic: toma la URL de la configuración y las tablas de modelos.py."""
from alembic import context
from sqlalchemy import engine_from_config, pool

from estudio.plataforma import modelos  # noqa: F401 — registra las tablas
from estudio.plataforma.db import Base

config = context.config
objetivo = Base.metadata


def correr() -> None:
    motor = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.",
                               poolclass=pool.NullPool)
    with motor.connect() as con:
        # render_as_batch: SQLite no sabe alterar columnas; Alembic recrea la tabla por nosotros
        context.configure(connection=con, target_metadata=objetivo, render_as_batch=True,
                          compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


correr()
