"""Añadir modelos Role y la clave foránea role_id a User

Revision ID: ad8154e1306e
Revises: 001
Create Date: 2025-11-10 08:15:51.266517

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ad8154e1306e'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Crear la tabla 'roles'
    op.create_table('roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # 2. Añadir la columna 'role_id' a 'user' con valor por defecto
    op.add_column('user', sa.Column('role_id', sa.Integer(), nullable=False, server_default=sa.text('1')))

    # 3. CORRECCIÓN: Definir el objeto de la tabla para op.bulk_insert
    roles_table = sa.Table(
        'roles',
        sa.MetaData(),
        sa.Column('id', sa.Integer),
        sa.Column('name', sa.String),
        sa.Column('description', sa.String)
    )

    # 4. Insertar el rol por defecto (ID 1) ANTES de activar la Foreign Key
    op.bulk_insert(
        roles_table, # <-- AQUÍ ESTÁ LA CORRECCIÓN
        [
            {'id': 1, 'name': 'guest', 'description': 'Usuario por defecto / no autenticado'}
        ]
    )

    # 5. Añadir la clave foránea a 'user'
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_user_role', 'roles', ['role_id'], ['id'])


def downgrade():
    # 1. Eliminar la clave foránea
    with op.batch_alter_table('user', schema=None) as batch_op:
        # Nota: Aquí la clave se llama 'fk_user_role' (definido arriba)
        batch_op.drop_constraint('fk_user_role', type_='foreignkey')
        # También eliminar la columna role_id si la añadiste
        batch_op.drop_column('role_id') 

    # 2. Eliminar la tabla roles
    op.drop_table('roles')