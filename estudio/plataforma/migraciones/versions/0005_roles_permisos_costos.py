"""roles (owner/admin/beta), permisos por usuario, visibilidad, lista negra y costo real por llamada

Solo agrega columnas y tablas y traduce los roles de antes (ceo → owner, cliente → beta). No borra nada.
Todo lo que ya existe con dueño queda PRIVADO; lo del catálogo (sin espacio), público.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-21 10:00:00
"""
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

CON_VISIBILIDAD = ('estilos', 'personajes', 'plantillas_miniatura', 'formulas_guion', 'voces', 'perfiles_edicion',
                   'formatos', 'canales')
LISTA_NEGRA_INICIAL = (('canal', '@codigodelexito22', 'Canal del dueño (Código del Éxito)'),)


def upgrade() -> None:
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.add_column(sa.Column('bloqueado', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('clave_hash', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('ultima_actividad', sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE usuarios SET rol = 'owner' WHERE rol = 'ceo'")
    op.execute("UPDATE usuarios SET rol = 'beta' WHERE rol = 'cliente'")

    for tabla in CON_VISIBILIDAD:
        with op.batch_alter_table(tabla, schema=None) as batch_op:
            batch_op.add_column(sa.Column('visibilidad', sa.String(length=12), nullable=False,
                                          server_default='privado'))
        if tabla != 'canales':                    # los canales siempre tienen espacio: quedan privados
            op.execute(f"UPDATE {tabla} SET visibilidad = 'publico' WHERE espacio_id IS NULL")

    op.create_table('permisos_usuario',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('usuario_id', sa.String(length=32), nullable=False),
    sa.Column('permiso', sa.String(length=40), nullable=False),
    sa.Column('activo', sa.Boolean(), nullable=False),
    sa.Column('creado', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('usuario_id', 'permiso')
    )
    with op.batch_alter_table('permisos_usuario', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_permisos_usuario_usuario_id'), ['usuario_id'], unique=False)

    lista = op.create_table('lista_negra',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('tipo', sa.String(length=10), nullable=False),
    sa.Column('valor', sa.String(length=200), nullable=False),
    sa.Column('nota', sa.Text(), nullable=False),
    sa.Column('creado', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tipo', 'valor')
    )
    op.bulk_insert(lista, [{'id': uuid.uuid4().hex, 'tipo': t, 'valor': v, 'nota': n,
                            'creado': datetime.now(timezone.utc)} for t, v, n in LISTA_NEGRA_INICIAL])

    op.create_table('costos_llamada',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('usuario_id', sa.String(length=32), nullable=True),
    sa.Column('espacio_id', sa.String(length=32), nullable=True),
    sa.Column('video_id', sa.String(length=32), nullable=True),
    sa.Column('trabajo', sa.String(length=120), nullable=False),
    sa.Column('proveedor', sa.String(length=30), nullable=False),
    sa.Column('modelo', sa.String(length=80), nullable=False),
    sa.Column('accion', sa.String(length=60), nullable=False),
    sa.Column('unidades', sa.JSON(), nullable=False),
    sa.Column('costo_usd', sa.Float(), nullable=False),
    sa.Column('creado', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['espacio_id'], ['espacios.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('costos_llamada', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_costos_llamada_usuario_id'), ['usuario_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_costos_llamada_espacio_id'), ['espacio_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_costos_llamada_creado'), ['creado'], unique=False)


def downgrade() -> None:
    op.drop_table('costos_llamada')
    op.drop_table('lista_negra')
    op.drop_table('permisos_usuario')
    for tabla in CON_VISIBILIDAD:
        with op.batch_alter_table(tabla, schema=None) as batch_op:
            batch_op.drop_column('visibilidad')
    op.execute("UPDATE usuarios SET rol = 'cliente' WHERE rol = 'beta'")
    op.execute("UPDATE usuarios SET rol = 'ceo' WHERE rol = 'owner'")
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_column('ultima_actividad')
        batch_op.drop_column('clave_hash')
        batch_op.drop_column('bloqueado')
