"""Add is_active to ClinicalInstructor

Revision ID: a1b2c3d4e5f6
Revises: 9224674ced4b
Create Date: 2026-02-27

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '9224674ced4b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('clinical_instructor', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')))


def downgrade():
    with op.batch_alter_table('clinical_instructor', schema=None) as batch_op:
        batch_op.drop_column('is_active')
