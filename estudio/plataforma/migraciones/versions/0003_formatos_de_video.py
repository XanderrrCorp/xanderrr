"""formatos de video

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-28 04:13:11.779633
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('formatos',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('espacio_id', sa.String(length=32), nullable=True),
    sa.Column('clave', sa.String(length=80), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('datos', sa.JSON(), nullable=False),
    sa.Column('origen', sa.JSON(), nullable=False),
    sa.Column('archivado', sa.Boolean(), nullable=False),
    sa.Column('creado', sa.DateTime(timezone=True), nullable=False),
    sa.Column('actualizado', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['espacio_id'], ['espacios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('espacio_id', 'clave')
    )
    with op.batch_alter_table('formatos', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_formatos_espacio_id'), ['espacio_id'], unique=False)

    with op.batch_alter_table('canales', schema=None) as batch_op:
        batch_op.add_column(sa.Column('formato_id', sa.String(length=32), nullable=True))
        batch_op.create_foreign_key('fk_canales_formato_id', 'formatos', ['formato_id'], ['id'])

    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('formato_id', sa.String(length=32), nullable=True))
        batch_op.create_foreign_key('fk_videos_formato_id', 'formatos', ['formato_id'], ['id'])



def downgrade() -> None:
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.drop_constraint('fk_videos_formato_id', type_='foreignkey')
        batch_op.drop_column('formato_id')

    with op.batch_alter_table('canales', schema=None) as batch_op:
        batch_op.drop_constraint('fk_canales_formato_id', type_='foreignkey')
        batch_op.drop_column('formato_id')

    with op.batch_alter_table('formatos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_formatos_espacio_id'))

    op.drop_table('formatos')
