"""Add color to Field model

Revision ID: da568523af3d
Revises: 37da31ccff46
Create Date: 2024-07-12 15:02:03.799840

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'da568523af3d'
down_revision = '37da31ccff46'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('field', schema=None) as batch_op:
        batch_op.add_column(sa.Column('color', sa.String(length=7), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('field', schema=None) as batch_op:
        batch_op.drop_column('color')

    # ### end Alembic commands ###
