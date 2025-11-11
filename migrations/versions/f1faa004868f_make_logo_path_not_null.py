from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'f1faa004868f'
down_revision = 'dbfb383e3cc2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands manual adjustment: Make community.logo_path NOT NULL ###
    with op.batch_alter_table('community', schema=None) as batch_op:
        batch_op.alter_column('logo_path',
                   existing_type=mysql.VARCHAR(length=255),
                   nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands manual adjustment: Make community.logo_path nullable again ###
    with op.batch_alter_table('community', schema=None) as batch_op:
        batch_op.alter_column('logo_path',
                   existing_type=mysql.VARCHAR(length=255),
                   nullable=True)
    # ### end Alembic commands ###