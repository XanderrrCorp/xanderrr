"""usos de clip (modo Tracy): historial anti-repetición

Solo agrega una tabla nueva; no toca las que ya existen.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-30 19:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('usos_clip',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('espacio_id', sa.String(length=32), nullable=False),
    sa.Column('canal', sa.String(length=80), nullable=False),
    sa.Column('slug', sa.String(length=80), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('clip', sa.String(length=200), nullable=False),
    sa.Column('inicio', sa.Float(), nullable=True),
    sa.Column('fin', sa.Float(), nullable=True),
    sa.Column('creado', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['espacio_id'], ['espacios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('usos_clip', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_usos_clip_espacio_id'), ['espacio_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_usos_clip_canal'), ['canal'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('usos_clip', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_usos_clip_canal'))
        batch_op.drop_index(batch_op.f('ix_usos_clip_espacio_id'))
    op.drop_table('usos_clip')
